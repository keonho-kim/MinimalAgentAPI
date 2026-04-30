from pathlib import Path
from typing import Any

from .event_activity import ActivityEventBuilder
from .event_extraction import (
    extract_reasoning,
    extract_text,
    extract_tool_calls,
    jsonable_mapping,
    object_or_empty,
)
from .event_filtering import InternalProtocolFilter


class StreamEventNormalizer:
    def __init__(self, workspace_root: str | Path | None = None) -> None:
        self._streamed_model_runs: set[str] = set()
        self._activity_builder = ActivityEventBuilder(workspace_root=workspace_root)
        self._protocol_filter = InternalProtocolFilter()

    def normalize(self, raw: Any) -> list[dict[str, Any]]:
        raw = jsonable_mapping(raw)
        if not isinstance(raw, dict):
            return []

        event_name = raw.get("event") or raw.get("name")

        if event_name in {"on_chat_model_stream", "on_llm_stream"}:
            return self._normalize_model_stream(raw)

        if event_name in {"on_chat_model_end", "on_llm_end"}:
            return self._normalize_model_end(raw)

        if event_name == "on_tool_start":
            return [
                self._activity_builder.create(
                    raw,
                    "tool",
                    "running",
                    raw.get("data", {}).get("input"),
                )
            ]

        if event_name == "on_tool_end":
            return [
                self._activity_builder.create(
                    raw,
                    "tool",
                    "completed",
                    None,
                    raw.get("data", {}).get("output"),
                )
            ]

        if event_name == "on_tool_error":
            return [
                self._activity_builder.create(
                    raw,
                    "tool",
                    "error",
                    None,
                    raw.get("data", {}).get("error"),
                )
            ]

        if event_name == "on_retriever_start":
            return [
                self._activity_builder.create(
                    raw,
                    "retriever",
                    "running",
                    raw.get("data", {}).get("input"),
                )
            ]

        if event_name == "on_retriever_end":
            return [
                self._activity_builder.create(
                    raw,
                    "retriever",
                    "completed",
                    raw.get("data", {}).get("input"),
                    raw.get("data", {}).get("output"),
                )
            ]

        if event_name in {"custom", "on_custom_event"}:
            return [
                self._activity_builder.create(raw, "custom", "running", raw.get("data"))
            ]

        if event_name in {"on_chain_start", "on_chain_end"}:
            activity = self._activity_builder.normalize_visible_chain(raw, event_name)
            return [activity] if activity else []

        return []

    def _normalize_model_stream(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        data = object_or_empty(raw.get("data"))
        chunk = data.get("chunk") or data.get("output") or data.get("message") or data
        run_id = raw.get("run_id")
        tool_calls = extract_tool_calls(chunk)
        reasoning = extract_reasoning(chunk)
        text = self._protocol_filter.filter_text(run_id, extract_text(chunk))
        events: list[dict[str, Any]] = []

        if reasoning or text:
            if isinstance(run_id, str):
                self._streamed_model_runs.add(run_id)

        if reasoning:
            _append_text_event(
                events,
                "think_delta",
                run_id,
                raw.get("parent_ids") or [],
                reasoning,
            )

        if text:
            _append_text_event(
                events,
                "assistant_delta",
                run_id,
                raw.get("parent_ids") or [],
                text,
            )

        for index, tool_call in enumerate(tool_calls):
            events.append(
                self._activity_builder.create_tool_intent(
                    raw,
                    run_id,
                    tool_call,
                    index,
                )
            )

        return events

    def _normalize_model_end(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        run_id = raw.get("run_id")
        if isinstance(run_id, str) and run_id in self._streamed_model_runs:
            return []

        data = object_or_empty(raw.get("data"))
        output = data.get("output") or data.get("chunk") or data.get("message")
        reasoning = extract_reasoning(output)
        text = self._protocol_filter.filter_text(run_id, extract_text(output))
        events: list[dict[str, Any]] = []

        if reasoning:
            _append_text_event(
                events,
                "think_delta",
                raw.get("run_id"),
                raw.get("parent_ids") or [],
                reasoning,
            )

        if text:
            _append_text_event(
                events,
                "assistant_delta",
                raw.get("run_id"),
                raw.get("parent_ids") or [],
                text,
            )

        return events


def _append_text_event(
    events: list[dict[str, Any]],
    kind: str,
    run_id: Any,
    parent_ids: list[Any],
    text: str,
) -> None:
    if not text:
        return

    events.append(
        {
            "kind": kind,
            "id": run_id,
            "parentIds": parent_ids,
            "text": text,
        }
    )
