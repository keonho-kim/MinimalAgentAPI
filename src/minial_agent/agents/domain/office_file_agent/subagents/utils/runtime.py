from typing import Any

from langgraph.prebuilt.tool_node import ToolRuntime

from minial_agent.common.llm import llm_client
from minial_agent.integrations.upload import ensure_upload_workspace, get_workspace_root
from minial_agent.integrations.upload.models import UploadWorkspace


def workspace_from_tool_runtime(runtime: ToolRuntime) -> UploadWorkspace:
    configurable = runtime.config.get("configurable", {})
    user_id = configurable.get("user_id")
    uuid = configurable.get("uuid")

    thread_id = configurable.get("thread_id")
    if (not user_id or not uuid) and isinstance(thread_id, str) and ":" in thread_id:
        user_id, uuid = thread_id.split(":", 1)

    if not user_id or not uuid:
        raise RuntimeError("Tool runtime is missing user workspace identity.")

    return ensure_upload_workspace(get_workspace_root(str(user_id), str(uuid)))


def sanitize_tool_error(error: Exception) -> str:
    message = str(error)
    for token in (".converted", ".registry", ".jobs", ".cache", ".outputs"):
        message = message.replace(token, "[internal]")
    return message


def compact_artifact_summary(artifact: dict[str, Any]) -> str:
    parts = [
        f"file_id={artifact.get('file_id', '')}",
        f"filename={artifact.get('filename', '')}",
        f"file_type={artifact.get('file_type', '')}",
        f"pages={artifact.get('page_count', 0)}",
    ]
    if "sheet_count" in artifact:
        parts.append(f"sheets={artifact.get('sheet_count', 0)}")
    return ", ".join(parts)


def invoke_text_llm(prompt: str, *, disable_streaming: bool | str = False) -> str:
    response = llm_client(disable_streaming=disable_streaming).invoke(prompt)
    return response_content(response)


def response_content(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, list):
        return " ".join(str(item) for item in content)
    return str(content)
