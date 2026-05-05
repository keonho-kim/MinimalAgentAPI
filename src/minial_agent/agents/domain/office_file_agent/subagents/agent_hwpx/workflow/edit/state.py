from pathlib import Path
from typing import Any, TypedDict


class HwpxEditState(TypedDict, total=False):
    file_ref: str
    instruction: str
    artifact: Any
    edit_spec: dict[str, Any]
    edited_path: Path
    changed_items: list[dict[str, Any]]
    result_payload: dict[str, Any]
    result: str
