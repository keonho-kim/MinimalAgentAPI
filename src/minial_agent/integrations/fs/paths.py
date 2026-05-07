from pathlib import Path

from minial_agent.integrations.fs.errors import WorkspaceFsError
from minial_agent.integrations.upload.visibility import (
    WorkspaceVisibilityError,
    normalize_public_workspace_path,
    public_virtual_to_physical,
)


def resolve_public_path(
    files_root: Path,
    path: str,
    *,
    allow_root: bool = False,
) -> Path:
    try:
        if allow_root and normalize_public_workspace_path(path, allow_root=True) == "/":
            return files_root.resolve()
        return public_virtual_to_physical(files_root, path)
    except WorkspaceVisibilityError as exc:
        raise WorkspaceFsError(400, str(exc)) from exc


def resolve_existing_path(files_root: Path, path: str) -> Path:
    target = resolve_public_path(files_root, path)
    if not target.exists():
        raise WorkspaceFsError(404, "Workspace path not found.")
    return target


def resolve_file(files_root: Path, path: str) -> Path:
    target = resolve_existing_path(files_root, path)
    if not target.is_file():
        raise WorkspaceFsError(400, "Workspace path is not a file.")
    return target


def validate_output_part(value: str, *, label: str) -> None:
    if not value or Path(value).name != value or value in {".", ".."}:
        raise WorkspaceFsError(400, f"Invalid output {label}.")


def validate_visible_name(value: str) -> None:
    if (
        not value
        or Path(value).name != value
        or value in {".", ".."}
        or value.startswith(".")
    ):
        raise WorkspaceFsError(400, "Invalid workspace name.")
