from pathlib import PurePosixPath
from typing import Any, Callable

from langchain.agents.middleware import AgentMiddleware
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.types import Command

OFFICE_BINARY_EXTENSIONS = {
    ".docx",
    ".hwpx",
    ".pdf",
    ".ppt",
    ".pptx",
    ".xlsx",
}


class OfficeBinaryReadGuardMiddleware(AgentMiddleware):
    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        blocked = _blocked_read_file_message(request)
        if blocked:
            return blocked
        return handler(request)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        blocked = _blocked_read_file_message(request)
        if blocked:
            return blocked
        return await handler(request)


def _blocked_read_file_message(request: ToolCallRequest) -> ToolMessage | None:
    if request.tool_call.get("name") != "read_file":
        return None

    args = request.tool_call.get("args")
    if not isinstance(args, dict):
        return None

    file_path = args.get("file_path")
    if not isinstance(file_path, str):
        return None

    extension = PurePosixPath(file_path).suffix.lower()
    if extension not in OFFICE_BINARY_EXTENSIONS:
        return None

    return ToolMessage(
        content=(
            "Error: office binary files must not be read with read_file. "
            f"Use the matching read_*_file tool for '{file_path}' instead."
        ),
        name="read_file",
        tool_call_id=request.tool_call.get("id"),
        status="error",
    )
