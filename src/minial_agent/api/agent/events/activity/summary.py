from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langgraph.types import Command

from minial_agent.constants.agent_mapper import is_agent_name

from minial_agent.api.agent.events.serialization import (
    jsonable_mapping,
    object_or_empty,
)


def summarize_activity(
    name: str, input_value: Any, output: Any = None
) -> dict[str, Any]:
    source = _summarize_input(input_value)
    result = _summarize_output(output)
    skill_lines = _skill_metadata_lines(output)
    summary = public_summary(
        {
            "path": source.get("path") or result.get("path"),
            "fileId": source.get("fileId") or result.get("fileId"),
            "filename": source.get("filename") or result.get("filename"),
            "query": source.get("query"),
            "description": source.get("description") or result.get("description"),
            "result": None if skill_lines else result.get("result"),
            "pageCount": result.get("pageCount"),
            "relevantPages": result.get("relevantPages"),
            "editedFile": result.get("editedFile"),
            "status": result.get("status"),
            "toolCalls": result.get("toolCalls"),
            "agentName": source.get("agentName") or result.get("agentName"),
            "next": result.get("next"),
        }
    )

    if skill_lines:
        summary["skills"] = skill_lines

    return summary


def event_metadata_summary(raw: dict[str, Any]) -> dict[str, Any]:
    metadata = object_or_empty(raw.get("metadata"))
    node = metadata.get("langgraph_node")
    model = metadata.get("ls_model_name") or metadata.get("model_name")
    return {
        "description": "모델 응답을 생성하는 단계입니다.",
        "node": node,
        "model": model,
    }


def output_looks_error(output: Any) -> bool:
    output = jsonable_mapping(output)

    if isinstance(output, str):
        return "error" in output.lower()

    if isinstance(output, dict):
        error = output.get("error")
        return bool(error)

    return False


def public_summary(value: dict[str, Any]) -> dict[str, Any]:
    return {
        key: item
        for key, item in value.items()
        if item is not None and item != "" and item != [] and item != {}
    }


def string_value(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _summarize_input(value: Any) -> dict[str, Any]:
    if value is None:
        return {}

    if isinstance(value, Command):
        return _summarize_command(value)

    if isinstance(value, BaseMessage):
        return _summarize_message(value)

    if isinstance(value, dict):
        return _summarize_mapping(value)

    return {}


def _summarize_output(value: Any) -> dict[str, Any]:
    if value is None:
        return {}

    if isinstance(value, Command):
        return _summarize_command(value)

    if isinstance(value, ToolMessage):
        artifact_summary = _summarize_mapping(value.artifact or {})
        content = _safe_text_result(value.content)
        if content and not artifact_summary:
            artifact_summary.setdefault("result", content)
        return artifact_summary

    if isinstance(value, AIMessage):
        summary = _summarize_message(value)
        summary.pop("result", None)
        return summary

    if isinstance(value, BaseMessage):
        return _summarize_message(value)

    if isinstance(value, dict):
        return _summarize_mapping(value)

    if isinstance(value, str):
        result = _safe_text_result(value)
        return {"result": result} if result else {}

    return {}


def _summarize_command(value: Command) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    update = getattr(value, "update", None)
    if isinstance(update, dict):
        summary.update(_summarize_mapping(update))

    goto = getattr(value, "goto", None)
    if isinstance(goto, str):
        summary["next"] = goto
    elif isinstance(goto, (list, tuple)):
        next_nodes = [item for item in goto if isinstance(item, str)]
        if next_nodes:
            summary["next"] = ", ".join(next_nodes[:3])

    return public_summary(summary)


def _summarize_message(value: BaseMessage) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    tool_calls = getattr(value, "tool_calls", None) or []
    if tool_calls:
        names = [
            str(call.get("name"))
            for call in tool_calls
            if isinstance(call, dict) and call.get("name")
        ]
        if names:
            summary["toolCalls"] = names[:5]

    if isinstance(value, ToolMessage):
        artifact_summary = _summarize_mapping(value.artifact or {})
        content = _safe_text_result(value.content)
        if content and not artifact_summary:
            artifact_summary.setdefault("result", content)
        return artifact_summary

    if not isinstance(value, AIMessage):
        content = _message_text(value)
        if content:
            summary["result"] = content

    return public_summary(summary)


def _summarize_mapping(value: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    path = string_value(
        value.get("file_path")
        or value.get("path")
        or value.get("visible_path")
        or value.get("download_url")
    )
    if path:
        summary["path"] = path

    file_id = string_value(value.get("file_id") or value.get("source_file_id"))
    if file_id:
        summary["fileId"] = file_id

    filename = string_value(
        value.get("filename")
        or value.get("visible_name")
        or value.get("source_filename")
    )
    if filename:
        summary["filename"] = filename

    query = string_value(value.get("query") or value.get("pattern"))
    if query:
        summary["query"] = query

    description = string_value(value.get("description"))
    if description:
        summary["description"] = description

    agent_name = string_value(value.get("name") or value.get("agent_name"))
    if agent_name and is_agent_name(agent_name):
        summary["agentName"] = agent_name

    status = string_value(value.get("status"))
    if status:
        summary["status"] = status

    page_count = _int_value(value.get("page_count") or value.get("pageCount"))
    if page_count is not None:
        summary["pageCount"] = page_count

    relevant_pages = _page_numbers(value.get("relevant_pages"))
    if relevant_pages:
        summary["relevantPages"] = relevant_pages

    edited_file = value.get("edited_file")
    if isinstance(edited_file, dict):
        edited_summary = _summarize_mapping(edited_file)
        if edited_summary:
            summary["editedFile"] = edited_summary

    useful = (
        value.get("message")
        or value.get("error")
        or value.get("result")
        or value.get("content")
    )
    result = _safe_text_result(useful)
    if result:
        summary["result"] = result

    return public_summary(summary)


def _message_text(value: BaseMessage) -> str | None:
    content = value.content
    if isinstance(content, str):
        return _safe_text_result(content)
    return None


def _safe_text_result(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    if _looks_like_raw_runtime_value(text):
        return None

    return _truncate(text, max_length=240)


def _looks_like_raw_runtime_value(value: str) -> bool:
    stripped = value.lstrip()
    if stripped.startswith(("{", "[")):
        return True
    return any(
        marker in value
        for marker in (
            "Command(",
            "ToolMessage(",
            "AIMessage(",
            "tool_call_id=",
            "additional_kwargs=",
            "response_metadata=",
        )
    )


def _int_value(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _page_numbers(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []

    pages = []
    for item in value[:20]:
        if isinstance(item, int):
            pages.append(item)
            continue
        if isinstance(item, dict):
            page = _int_value(item.get("page_number") or item.get("page"))
            if page is not None:
                pages.append(page)
    return pages


def _skill_metadata_lines(value: Any) -> list[str]:
    value = jsonable_mapping(value)
    if not isinstance(value, dict):
        return []

    metadata = value.get("skills_metadata")
    if not isinstance(metadata, list):
        return []

    lines = []
    for item in metadata:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        description = item.get("description")
        if isinstance(name, str) and name.strip():
            if isinstance(description, str) and description.strip():
                lines.append(f"{name.strip()}: {description.strip()}")
            else:
                lines.append(name.strip())

    return lines


def _truncate(value: str, max_length: int = 700) -> str:
    if len(value) <= max_length:
        return value

    return f"{value[:max_length]}..."
