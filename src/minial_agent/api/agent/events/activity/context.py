from pathlib import Path
from typing import Any

from minial_agent.api.agent.events.activity.constants import (
    SKILL_READ_COMPLETED_MESSAGE,
    SKILL_READ_ERROR_MESSAGE,
    SKILL_READ_PENDING_MESSAGE,
    SKILL_READ_RUNNING_MESSAGE,
)
from minial_agent.api.agent.events.serialization import object_or_empty


def get_skill_read_context(
    name: str,
    input_value: Any,
) -> dict[str, Any] | None:
    if name != "read_file":
        return None

    source = object_or_empty(input_value)
    path = source.get("file_path") or source.get("path")
    if not isinstance(path, str):
        return None

    skill_name = _skill_name_from_path(path)
    if skill_name is None:
        return None

    return {
        "context_type": "skill_read",
        "skill_name": skill_name,
        "summary": {
            "skillName": skill_name,
            "path": f"/.agents/skills/{skill_name}/SKILL.md",
            "description": f"사용한 스킬: {skill_name}",
        },
    }


def skill_read_message(skill_name: str, status: str) -> str:
    if status == "pending":
        return SKILL_READ_PENDING_MESSAGE
    if status == "running":
        return SKILL_READ_RUNNING_MESSAGE.format(skill_name=skill_name)
    if status == "completed":
        return SKILL_READ_COMPLETED_MESSAGE.format(skill_name=skill_name)
    if status == "error":
        return SKILL_READ_ERROR_MESSAGE.format(skill_name=skill_name)
    return f"AGENT가 {skill_name} 스킬을 확인합니다."


def get_write_file_parent_context(
    workspace_root: Path | None,
    name: str,
    input_value: Any,
) -> dict[str, Any] | None:
    if name != "write_file" or workspace_root is None:
        return None

    source = object_or_empty(input_value)
    virtual_path = source.get("file_path") or source.get("path")
    if not isinstance(virtual_path, str) or not virtual_path.strip():
        return None

    resolved_path = _resolve_workspace_virtual_path(workspace_root, virtual_path)
    if resolved_path is None:
        return None

    parent_path = resolved_path.parent
    if parent_path == workspace_root or parent_path.exists():
        return None

    virtual_parent_path = _virtual_parent_path(virtual_path)
    return {
        "context_type": "write_file_parent",
        "real_parent_path": parent_path,
        "summary": {
            "createsParentDirectory": True,
            "parentPath": virtual_parent_path,
            "description": f"필요한 폴더: {virtual_parent_path}",
        },
    }


def _skill_name_from_path(path: str) -> str | None:
    normalized = path.strip().replace("\\", "/")
    prefixes = (
        "/.agents/skills/",
        ".agents/skills/",
    )
    for prefix in prefixes:
        if not normalized.startswith(prefix):
            continue
        relative = normalized.removeprefix(prefix)
        parts = [part for part in relative.split("/") if part]
        if len(parts) == 2 and parts[1] == "SKILL.md" and parts[0]:
            return parts[0]
    return None


def _resolve_workspace_virtual_path(
    workspace_root: Path,
    virtual_path: str,
) -> Path | None:
    relative_path = virtual_path.strip().lstrip("/")
    if not relative_path:
        return None

    resolved_path = (workspace_root / relative_path).resolve()
    try:
        resolved_path.relative_to(workspace_root)
    except ValueError:
        return None

    return resolved_path


def _virtual_parent_path(virtual_path: str) -> str:
    normalized = "/" + virtual_path.strip().lstrip("/")
    parent = str(Path(normalized).parent)
    return "/" if parent == "." else parent
