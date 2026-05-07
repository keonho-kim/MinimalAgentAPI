import json
from typing import Any

from langchain_core.messages import BaseMessage

from minial_agent.api.agent.events.text import message_content_blocks


def extract_tool_calls(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, BaseMessage):
        return _deduplicate_tool_calls(
            _extract_message_tool_calls(value)
            + _extract_content_block_tool_calls(message_content_blocks(value))
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


def parse_maybe_json(value: Any) -> Any:
    if not isinstance(value, str):
        return value

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


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
