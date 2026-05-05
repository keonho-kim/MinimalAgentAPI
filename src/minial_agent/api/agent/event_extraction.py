import json
from typing import Any

from fastapi.encoders import jsonable_encoder
from langchain_core.messages import BaseMessage

REASONING_BLOCK_TYPES = {
    "reasoning",
    "reasoning_content",
    "thinking",
    "thought",
    "reasoning_delta",
    "thinking_delta",
}

REASONING_FIELDS = (
    "reasoning_content",
    "reasoning",
    "thinking",
    "thought",
    "reasoning_delta",
    "thinking_delta",
)


def extract_text(value: Any) -> str:
    if isinstance(value, str):
        return value

    if isinstance(value, BaseMessage):
        return value.text

    if isinstance(value, list):
        return "".join(extract_text(item) for item in value)

    if not isinstance(value, dict):
        return ""

    if _is_reasoning_block(value):
        return ""

    if value.get("type") == "text" and isinstance(value.get("text"), str):
        return value["text"]

    if isinstance(value.get("text"), str):
        return value["text"]

    if isinstance(value.get("content"), str):
        return value["content"]

    if isinstance(value.get("content"), list):
        return "".join(extract_text(item) for item in value["content"])

    if "kwargs" in value:
        return extract_text(value["kwargs"])

    return ""


def extract_reasoning(value: Any) -> str:
    if isinstance(value, str):
        return ""

    if isinstance(value, BaseMessage):
        return "".join(
            _extract_reasoning_block_text(block)
            for block in _message_content_blocks(value)
            if isinstance(block, dict) and _is_reasoning_block(block)
        )

    if isinstance(value, list):
        return "".join(extract_reasoning(item) for item in value)

    if not isinstance(value, dict):
        return ""

    if _is_reasoning_block(value):
        return _extract_reasoning_block_text(value)

    parts = []
    for field in REASONING_FIELDS:
        extracted = _extract_reasoning_value(value.get(field))
        if extracted:
            parts.append(extracted)

    for nested_field in ("kwargs", "additional_kwargs", "response_metadata"):
        nested = value.get(nested_field)
        if isinstance(nested, dict):
            extracted = extract_reasoning(nested)
            if extracted:
                parts.append(extracted)

    content = value.get("content")
    if isinstance(content, list):
        extracted = extract_reasoning(content)
        if extracted:
            parts.append(extracted)

    return "".join(parts)


def extract_tool_calls(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, BaseMessage):
        return _deduplicate_tool_calls(
            _extract_message_tool_calls(value)
            + _extract_content_block_tool_calls(_message_content_blocks(value))
        )

    if not isinstance(value, dict):
        return []

    calls: list[dict[str, Any]] = []
    content = value.get("content") if isinstance(value.get("content"), list) else []
    calls.extend(_extract_content_block_tool_calls(content))

    for call in value.get("tool_calls") or []:
        if isinstance(call, dict):
            calls.append(
                {
                    "id": call.get("id"),
                    "name": call.get("name"),
                    "args": call.get("args"),
                }
            )

    for call in value.get("tool_call_chunks") or []:
        if isinstance(call, dict):
            calls.append(
                {
                    "id": call.get("id"),
                    "name": call.get("name"),
                    "args": parse_maybe_json(call.get("args")),
                    "index": call.get("index"),
                }
            )

    return _deduplicate_tool_calls(calls)


def object_or_empty(value: Any) -> dict[str, Any]:
    value = jsonable_mapping(value)
    return value if isinstance(value, dict) else {}


def jsonable_mapping(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: jsonable_mapping(item) for key, item in value.items()}
    if isinstance(value, list):
        return [jsonable_mapping(item) for item in value]
    if isinstance(value, tuple):
        return [jsonable_mapping(item) for item in value]

    try:
        return jsonable_encoder(value)
    except Exception:
        return value


def parse_maybe_json(value: Any) -> Any:
    if not isinstance(value, str):
        return value

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _extract_reasoning_value(value: Any) -> str:
    if isinstance(value, str):
        return value

    if isinstance(value, list):
        return "".join(_extract_reasoning_value(item) for item in value)

    if isinstance(value, dict):
        for field in ("text", "content", "summary", "reasoning", "thinking"):
            extracted = _extract_reasoning_value(value.get(field))
            if extracted:
                return extracted

    return ""


def _extract_reasoning_block_text(value: dict[str, Any]) -> str:
    for field in ("text", "content", "thinking", "reasoning", "summary"):
        extracted = _extract_reasoning_value(value.get(field))
        if extracted:
            return extracted

    return ""


def _is_reasoning_block(value: dict[str, Any]) -> bool:
    block_type = value.get("type")
    return isinstance(block_type, str) and block_type in REASONING_BLOCK_TYPES


def _message_content_blocks(value: BaseMessage) -> list[Any]:
    blocks = getattr(value, "content_blocks", None)
    if isinstance(blocks, list):
        return blocks

    content = value.content
    return content if isinstance(content, list) else []


def _extract_message_tool_calls(value: BaseMessage) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    for call in getattr(value, "tool_calls", None) or []:
        if isinstance(call, dict):
            calls.append(
                {
                    "id": call.get("id"),
                    "name": call.get("name"),
                    "args": call.get("args"),
                }
            )

    for call in getattr(value, "tool_call_chunks", None) or []:
        if isinstance(call, dict):
            calls.append(
                {
                    "id": call.get("id"),
                    "name": call.get("name"),
                    "args": parse_maybe_json(call.get("args")),
                    "index": call.get("index"),
                }
            )

    return calls


def _extract_content_block_tool_calls(blocks: list[Any]) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if block.get("type") not in {"tool_call", "tool_call_chunk"}:
            continue
        calls.append(
            {
                "id": block.get("id"),
                "name": block.get("name"),
                "args": parse_maybe_json(block.get("args")),
                "index": block.get("index"),
            }
        )
    return calls


def _deduplicate_tool_calls(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduplicated: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()

    for call in calls:
        if call.get("id"):
            key = ("id", call.get("id"))
        else:
            key = (
                "content",
                call.get("name"),
                call.get("index"),
                json.dumps(
                    call.get("args"),
                    sort_keys=True,
                    ensure_ascii=False,
                    default=str,
                ),
            )
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(call)

    return deduplicated
