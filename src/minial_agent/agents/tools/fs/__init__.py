from langchain_core.tools import tool
from langgraph.prebuilt.tool_node import ToolRuntime

from minial_agent.agents.utils.runtime import (
    sanitize_tool_error,
    workspace_identity_from_tool_runtime,
)
from minial_agent.integrations.fs import workspace_fs_service


@tool
def rename_file(file_path: str, name: str, runtime: ToolRuntime) -> str:
    """Rename a workspace file or folder without changing its parent directory."""
    try:
        user_id, uuid = workspace_identity_from_tool_runtime(runtime)
        result = workspace_fs_service.rename_path(
            user_id=user_id,
            uuid=uuid,
            path=file_path,
            name=name,
        )
        return f"Renamed to {result.path}"
    except Exception as exc:
        return sanitize_tool_error(exc)


@tool
def move_file(file_path: str, destination_path: str, runtime: ToolRuntime) -> str:
    """Move a workspace file or folder to a new full workspace path."""
    try:
        user_id, uuid = workspace_identity_from_tool_runtime(runtime)
        result = workspace_fs_service.move_path(
            user_id=user_id,
            uuid=uuid,
            path=file_path,
            destination_path=destination_path,
        )
        return f"Moved to {result.path}"
    except Exception as exc:
        return sanitize_tool_error(exc)


@tool
def delete_file(file_path: str, runtime: ToolRuntime) -> str:
    """Delete a workspace file or folder and its generated artifacts."""
    try:
        user_id, uuid = workspace_identity_from_tool_runtime(runtime)
        result = workspace_fs_service.delete_file(
            user_id=user_id,
            uuid=uuid,
            path=file_path,
        )
        return f"Deleted {result.path}"
    except Exception as exc:
        return sanitize_tool_error(exc)


FS_TOOLS = [rename_file, move_file, delete_file]

__all__ = ["FS_TOOLS", "delete_file", "move_file", "rename_file"]
