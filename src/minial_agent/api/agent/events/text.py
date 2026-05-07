from typing import Any

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
            for block in message_content_blocks(value)
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


def message_content_blocks(value: BaseMessage) -> list[Any]:
    blocks = getattr(value, "content_blocks", None)
    if isinstance(blocks, list):
        return blocks

    content = value.content
    return content if isinstance(content, list) else []


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
