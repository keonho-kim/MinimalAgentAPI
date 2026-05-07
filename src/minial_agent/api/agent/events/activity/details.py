from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langgraph.types import Command

from minial_agent.constants.agent_mapper import is_agent_name

from minial_agent.api.agent.events.serialization import (
    jsonable_mapping,
    object_or_empty,
)


def activity_details(
    name: str, input_value: Any, output: Any = None
) -> dict[str, Any]:
    source = _details_from_input(input_value)
    result = _details_from_output(output)
    skill_lines = _skill_metadata_lines(output)
    details = public_details(
        {
            "path": source.get("path") or result.get("path"),
            "fileId": source.get("fileId") or result.get("fileId"),
            "filename": source.get("filename") or result.get("filename"),
            "query": source.get("query"),
            "description": source.get("description") or result.get("description"),
            "result": None if skill_lines else result.get("result"),
            "pageCount": result.get("pageCount"),
            "evidence": result.get("evidence"),
            "scannedPages": result.get("scannedPages"),
            "evidencePageCount": result.get("evidencePageCount"),
            "isSufficient": result.get("isSufficient"),
            "editedFile": result.get("editedFile"),
            "status": result.get("status"),
            "toolCalls": result.get("toolCalls"),
            "agentName": source.get("agentName") or result.get("agentName"),
            "next": result.get("next"),
        }
    )

    if skill_lines:
        details["skills"] = skill_lines

    return details


def event_metadata_details(raw: dict[str, Any]) -> dict[str, Any]:
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


def public_details(value: dict[str, Any]) -> dict[str, Any]:
    return {
        key: item
        for key, item in value.items()
        if item is not None and item != "" and item != [] and item != {}
    }


def string_value(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _details_from_input(value: Any) -> dict[str, Any]:
    if value is None:
        return {}

    if isinstance(value, Command):
        return _details_from_command(value)

    if isinstance(value, BaseMessage):
        return _details_from_message(value)

    if isinstance(value, dict):
        return _details_from_mapping(value)

    return {}


def _details_from_output(value: Any) -> dict[str, Any]:
    if value is None:
        return {}

    if isinstance(value, Command):
        return _details_from_command(value)

    if isinstance(value, ToolMessage):
        artifact_details = _details_from_mapping(value.artifact or {})
        content = _safe_text_result(value.content)
        if content and not artifact_details:
            artifact_details.setdefault("result", content)
        return artifact_details

    if isinstance(value, AIMessage):
        details = _details_from_message(value)
        details.pop("result", None)
        return details

    if isinstance(value, BaseMessage):
        return _details_from_message(value)

    if isinstance(value, dict):
        return _details_from_mapping(value)

    if isinstance(value, str):
        result = _safe_text_result(value)
        return {"result": result} if result else {}

    return {}


def _details_from_command(value: Command) -> dict[str, Any]:
    details: dict[str, Any] = {}
    update = getattr(value, "update", None)
    if isinstance(update, dict):
        details.update(_details_from_mapping(update))

    goto = getattr(value, "goto", None)
    if isinstance(goto, str):
        details["next"] = goto
    elif isinstance(goto, (list, tuple)):
        next_nodes = [item for item in goto if isinstance(item, str)]
        if next_nodes:
            details["next"] = ", ".join(next_nodes[:3])

    return public_details(details)


def _details_from_message(value: BaseMessage) -> dict[str, Any]:
    details: dict[str, Any] = {}
    tool_calls = getattr(value, "tool_calls", None) or []
    if tool_calls:
        names = [
            str(call.get("name"))
            for call in tool_calls
            if isinstance(call, dict) and call.get("name")
        ]
        if names:
            details["toolCalls"] = names[:5]

    if isinstance(value, ToolMessage):
        artifact_details = _details_from_mapping(value.artifact or {})
        content = _safe_text_result(value.content)
        if content and not artifact_details:
            artifact_details.setdefault("result", content)
        return artifact_details

    if not isinstance(value, AIMessage):
        content = _message_text(value)
        if content:
            details["result"] = content

    return public_details(details)


def _details_from_mapping(value: dict[str, Any]) -> dict[str, Any]:
    details: dict[str, Any] = {}
    path = string_value(
        value.get("file_path")
        or value.get("path")
        or value.get("visible_path")
        or value.get("download_url")
    )
    if path:
        details["path"] = path

    file_id = string_value(value.get("file_id") or value.get("source_file_id"))
    if file_id:
        details["fileId"] = file_id

    filename = string_value(
        value.get("filename")
        or value.get("visible_name")
        or value.get("source_filename")
    )
    if filename:
        details["filename"] = filename

    query = string_value(value.get("query") or value.get("pattern"))
    if query:
        details["query"] = query

    description = string_value(value.get("description"))
    if description:
        details["description"] = description

    agent_name = string_value(value.get("name") or value.get("agent_name"))
    if agent_name and is_agent_name(agent_name):
        details["agentName"] = agent_name

    status = string_value(value.get("status"))
    if status:
        details["status"] = status

    page_count = _int_value(value.get("page_count") or value.get("pageCount"))
    if page_count is not None:
        details["pageCount"] = page_count

    evidence = value.get("evidence")
    if isinstance(evidence, dict):
        clean_evidence = {
            str(page): str(answer)
            for page, answer in evidence.items()
            if str(page).strip() and str(answer).strip()
        }
        if clean_evidence:
            details["evidence"] = clean_evidence

    scanned_pages = _int_value(value.get("scanned_pages") or value.get("scannedPages"))
    if scanned_pages is not None:
        details["scannedPages"] = scanned_pages

    evidence_page_count = _int_value(
        value.get("evidence_page_count") or value.get("evidencePageCount")
    )
    if evidence_page_count is not None:
        details["evidencePageCount"] = evidence_page_count

    is_sufficient = value.get("is_sufficient")
    if isinstance(value.get("isSufficient"), bool):
        is_sufficient = value["isSufficient"]
    if isinstance(is_sufficient, bool):
        details["isSufficient"] = is_sufficient

    edited_file = value.get("edited_file")
    if isinstance(edited_file, dict):
        edited_details = _details_from_mapping(edited_file)
        if edited_details:
            details["editedFile"] = edited_details

    useful = (
        value.get("message")
        or value.get("error")
        or value.get("result")
        or value.get("content")
    )
    result = _safe_text_result(useful)
    if result:
        details["result"] = result

    return public_details(details)


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
