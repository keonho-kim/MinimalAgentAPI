import os
import shlex
import subprocess
import uuid
from pathlib import Path

from deepagents.backends.filesystem import FilesystemBackend
from deepagents.backends.protocol import (
    BackendProtocol,
    ExecuteResponse,
    SandboxBackendProtocol,
)


DEFAULT_EXECUTION_TIMEOUT_SECONDS = 300
MAX_EXECUTION_OUTPUT_BYTES = 100_000
ALLOWED_COMMANDS = frozenset({"python", "python3", "node", "bun", "uv"})
PYTHON_COMMANDS = frozenset({"python", "python3"})
JS_COMMANDS = frozenset({"node", "bun"})
COMMAND_ALLOWLIST_ERROR = (
    "Error: only python/python3 via uv, node, and bun commands are allowed "
    "for data analysis execution."
)


class DataExecutionBackend(FilesystemBackend, SandboxBackendProtocol):
    def __init__(self, root_dir: str | Path) -> None:
        super().__init__(
            root_dir=root_dir,
            virtual_mode=True,
            max_file_size_mb=1024,
        )
        self._id = f"data-execution-{uuid.uuid4()}"
        self._root_dir = Path(root_dir).resolve()
        self._project_root = self._find_project_root()

    @classmethod
    def from_backend(cls, backend: BackendProtocol) -> "DataExecutionBackend":
        root_dir = getattr(backend, "cwd", None)
        if root_dir is None:
            raise ValueError("Data analyst subagent requires a filesystem backend.")
        return cls(Path(root_dir))

    @property
    def id(self) -> str:
        return self._id

    def execute(self, command: str, *, timeout: int | None = None) -> ExecuteResponse:
        try:
            args, stdin = self._parse_command(command)
        except ValueError as exc:
            return ExecuteResponse(output=f"Error: invalid command: {exc}", exit_code=2)

        if not args:
            return ExecuteResponse(output="Error: command is required.", exit_code=2)

        executable = Path(args[0]).name
        if executable not in ALLOWED_COMMANDS:
            return ExecuteResponse(output=COMMAND_ALLOWLIST_ERROR, exit_code=126)

        try:
            prepared_args = self._prepare_args(executable, args)
        except PermissionError:
            return ExecuteResponse(output=COMMAND_ALLOWLIST_ERROR, exit_code=126)
        try:
            completed = subprocess.run(
                prepared_args,
                cwd=self._root_dir,
                env=self._execution_env(),
                text=True,
                input=stdin,
                capture_output=True,
                timeout=timeout or DEFAULT_EXECUTION_TIMEOUT_SECONDS,
                check=False,
            )
        except FileNotFoundError as exc:
            return ExecuteResponse(output=f"Error: command not found: {exc}", exit_code=127)
        except subprocess.TimeoutExpired as exc:
            output = self._join_output(exc.stdout, exc.stderr)
            return ExecuteResponse(
                output=f"{output}\nError: command timed out.",
                exit_code=124,
                truncated=False,
            )

        output = self._join_output(completed.stdout, completed.stderr)
        output, truncated = self._truncate_output(output)
        return ExecuteResponse(
            output=output,
            exit_code=completed.returncode,
            truncated=truncated,
        )

    def _prepare_args(self, executable: str, args: list[str]) -> list[str]:
        if executable in PYTHON_COMMANDS:
            return self._prepare_uv_python_args(args[1:])
        if executable == "uv":
            return self._prepare_explicit_uv_args(args)
        return [args[0], *(self._map_virtual_path_arg(arg) for arg in args[1:])]

    def _prepare_uv_python_args(self, args: list[str]) -> list[str]:
        return [
            "uv",
            "run",
            "--project",
            str(self._project_root),
            "python",
            *(self._map_virtual_path_arg(arg) for arg in args),
        ]

    def _prepare_explicit_uv_args(self, args: list[str]) -> list[str]:
        if len(args) < 3:
            raise PermissionError
        if args[1] != "run" or Path(args[2]).name not in PYTHON_COMMANDS:
            raise PermissionError
        return self._prepare_uv_python_args(args[3:])

    def _parse_command(self, command: str) -> tuple[list[str], str | None]:
        if not command.strip():
            return [], None

        lines = command.splitlines()
        first_line = lines[0]
        try:
            args = shlex.split(first_line)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

        heredoc = self._extract_heredoc(args, lines[1:])
        if heredoc is not None:
            return heredoc
        if len(lines) > 1:
            raise ValueError("multi-line commands require a supported heredoc.")
        return args, None

    def _extract_heredoc(
        self,
        args: list[str],
        body_lines: list[str],
    ) -> tuple[list[str], str] | None:
        delimiter = None
        delimiter_index = None
        remove_count = 1
        for index, arg in enumerate(args):
            if arg == "<<":
                if index + 1 >= len(args):
                    raise ValueError("heredoc delimiter is required.")
                delimiter = args[index + 1]
                delimiter_index = index
                remove_count = 2
                break
            if arg.startswith("<<"):
                delimiter = arg[2:]
                delimiter_index = index
                break

        if delimiter_index is None:
            return None
        if not delimiter:
            raise ValueError("heredoc delimiter is required.")

        end_index = None
        for index, line in enumerate(body_lines):
            if line.strip() == delimiter:
                end_index = index
                break
        if end_index is None:
            raise ValueError(f"heredoc delimiter '{delimiter}' was not found.")
        if any(line.strip() for line in body_lines[end_index + 1 :]):
            raise ValueError("commands after heredoc are not supported.")

        cleaned_args = [
            *args[:delimiter_index],
            *args[delimiter_index + remove_count :],
        ]
        return cleaned_args, "\n".join(body_lines[:end_index])

    def _map_virtual_path_arg(self, arg: str) -> str:
        if not arg.startswith("/"):
            return arg
        path = Path(arg)
        if ".." in path.parts:
            return arg
        return str(self._root_dir / arg.lstrip("/"))

    def _execution_env(self) -> dict[str, str]:
        return {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONIOENCODING": "utf-8",
            "PYTHONNOUSERSITE": "1",
            "MPLBACKEND": "Agg",
        }

    def _join_output(self, *parts: object) -> str:
        return "\n".join(
            text for part in parts if (text := self._output_part_to_text(part))
        )

    def _output_part_to_text(self, value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="ignore")
        return str(value)

    def _truncate_output(self, output: str) -> tuple[str, bool]:
        encoded = output.encode("utf-8")
        if len(encoded) <= MAX_EXECUTION_OUTPUT_BYTES:
            return output, False
        truncated = encoded[:MAX_EXECUTION_OUTPUT_BYTES].decode("utf-8", errors="ignore")
        return truncated, True

    def _find_project_root(self) -> Path:
        for parent in Path(__file__).resolve().parents:
            if (parent / "pyproject.toml").is_file():
                return parent
        raise RuntimeError("Data execution backend could not locate pyproject.toml.")
