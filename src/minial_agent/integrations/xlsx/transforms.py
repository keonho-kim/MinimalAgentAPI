import ast
import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import pandas as pd

from minial_agent.integrations.xlsx.dataframes import load_dataframe
from minial_agent.integrations.xlsx.errors import XlsxTransformError


FORBIDDEN_NAMES = {
    "__import__",
    "compile",
    "eval",
    "exec",
    "globals",
    "input",
    "locals",
    "open",
    "subprocess",
}
FORBIDDEN_ATTRIBUTES = {"__class__", "__dict__", "__globals__", "__mro__", "__subclasses__"}
ALLOWED_BUILTINS = {
    "abs",
    "all",
    "any",
    "bool",
    "dict",
    "enumerate",
    "float",
    "int",
    "len",
    "list",
    "max",
    "min",
    "pow",
    "range",
    "round",
    "set",
    "sorted",
    "str",
    "sum",
    "tuple",
    "zip",
}


def transform_dataframe(
    *,
    input_path: Path,
    output_path: Path,
    code: str,
    timeout_seconds: int = 8,
) -> pd.DataFrame:
    _validate_transform_code(code)
    with tempfile.TemporaryDirectory(prefix="minial_xlsx_transform_") as temp_dir:
        task_path = Path(temp_dir) / "task.py"
        result_path = Path(temp_dir) / "result.json"
        task_path.write_text(_runner_source(), encoding="utf-8")
        process = subprocess.run(
            [
                sys.executable,
                str(task_path),
                str(input_path),
                str(output_path),
                str(result_path),
            ],
            input=code,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        if process.returncode != 0:
            message = process.stderr.strip() or process.stdout.strip() or "Transform failed."
            raise XlsxTransformError(message)
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if result.get("status") != "ok":
            raise XlsxTransformError(str(result.get("error", "Transform failed.")))
    return load_dataframe(output_path)


def _validate_transform_code(code: str) -> None:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise XlsxTransformError(f"Invalid transform code: {exc}") from exc
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    if len(functions) != 1 or functions[0].name != "transform":
        raise XlsxTransformError("Transform code must define exactly one function named transform(df).")
    if len(functions[0].args.args) != 1 or functions[0].args.args[0].arg != "df":
        raise XlsxTransformError("transform must accept exactly one argument named df.")
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise XlsxTransformError("Imports are not allowed in XLSX dataframe transforms.")
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            raise XlsxTransformError(f"Forbidden name in transform code: {node.id}")
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("__") or node.attr in FORBIDDEN_ATTRIBUTES:
                raise XlsxTransformError(f"Forbidden attribute in transform code: {node.attr}")


def _runner_source() -> str:
    builtins_literal = repr(sorted(ALLOWED_BUILTINS))
    return textwrap.dedent(
        f"""
        import json
        import sys
        from io import StringIO

        import numpy as np
        import pandas as pd

        ALLOWED_BUILTINS = {builtins_literal}

        def load_df(path):
            return pd.read_json(StringIO(open(path, encoding="utf-8").read()), orient="split")

        def save_df(path, dataframe):
            open(path, "w", encoding="utf-8").write(
                dataframe.to_json(orient="split", date_format="iso", force_ascii=False)
            )

        input_path, output_path, result_path = sys.argv[1:4]
        code = sys.stdin.read()
        try:
            namespace = {{
                "__builtins__": {{name: getattr(__builtins__, name) for name in ALLOWED_BUILTINS}},
                "pd": pd,
                "np": np,
            }}
            exec(code, namespace)
            df = load_df(input_path)
            result = namespace["transform"](df.copy())
            if not isinstance(result, pd.DataFrame):
                raise TypeError("transform(df) must return a pandas DataFrame.")
            save_df(output_path, result)
            open(result_path, "w", encoding="utf-8").write(json.dumps({{"status": "ok"}}))
        except Exception as exc:
            open(result_path, "w", encoding="utf-8").write(
                json.dumps({{"status": "error", "error": str(exc)}})
            )
            raise
        """
    )
