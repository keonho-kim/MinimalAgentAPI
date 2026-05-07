from pathlib import Path
from typing import Any

from minial_agent.api.agent.events.activity import ActivityEventBuilder
from minial_agent.api.agent.events.serialization import object_or_empty
from minial_agent.api.agent.events.text import extract_reasoning, extract_text
from minial_agent.api.agent.events.tool_calls import extract_tool_calls


class StreamEventNormalizer:
    def __init__(self, workspace_root: str | Path | None = None) -> None:
        self._streamed_model_runs: set[str] = set()
        self._intermediate_model_text: dict[str, str] = {}
        self._emitted_tool_intents: set[tuple[Any, ...]] = set()
        self._activity_builder = ActivityEventBuilder(workspace_root=workspace_root)

    def normalize(self, raw: Any) -> list[dict[str, Any]]:
        if not isinstance(raw, dict):
            return []

        event_name = raw.get("event") or raw.get("name")

        if event_name in {"on_chat_model_start", "on_llm_start"}:
            if not _is_root_model_output(raw):
                return []
            return [self._activity_builder.create_model(raw, "running")]

        if event_name in {"on_chat_model_stream", "on_llm_stream"}:
            return self._normalize_model_stream(raw)

        if event_name in {"on_chat_model_end", "on_llm_end"}:
            events = self._normalize_model_end(raw)
            if _is_root_model_output(raw):
                return [
                    self._activity_builder.create_model(raw, "completed"),
                    *events,
                ]
            return events

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

        if event_name == "on_custom_event":
            return [self._activity_builder.create_custom(raw)]

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
        text = extract_text(chunk)
        events: list[dict[str, Any]] = []
        is_root_output = _is_root_model_output(raw)

        if not is_root_output:
            if isinstance(run_id, str) and text:
                self._intermediate_model_text[run_id] = (
                    self._intermediate_model_text.get(run_id, "") + text
                )
            self._append_tool_intents(events, raw, run_id, tool_calls)
            return events

        if reasoning or text:
            if isinstance(run_id, str):
                self._streamed_model_runs.add(run_id)

        if reasoning:
            _append_text_event(
                events,
                "think_delta",
                run_id,
                raw.get("event"),
                raw.get("name"),
                raw.get("parent_ids") or [],
                reasoning,
            )

        if text:
            _append_text_event(
                events,
                "assistant_delta",
                run_id,
                raw.get("event"),
                raw.get("name"),
                raw.get("parent_ids") or [],
                text,
            )

        self._append_tool_intents(events, raw, run_id, tool_calls)

        return events

    def _append_tool_intents(
        self,
        events: list[dict[str, Any]],
        raw: dict[str, Any],
        run_id: Any,
        tool_calls: list[dict[str, Any]],
    ) -> None:
        for index, tool_call in enumerate(tool_calls):
            if not _is_complete_tool_intent(tool_call):
                continue
            intent_key = _tool_intent_key(run_id, tool_call, index)
            if intent_key in self._emitted_tool_intents:
                continue
            self._emitted_tool_intents.add(intent_key)
            events.append(
                self._activity_builder.create_tool_intent(
                    raw,
                    run_id,
                    tool_call,
                    index,
                )
            )

    def _normalize_model_end(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        run_id = raw.get("run_id")
        data = object_or_empty(raw.get("data"))
        output = data.get("output") or data.get("chunk") or data.get("message")

        if not _is_root_model_output(raw):
            if isinstance(run_id, str):
                self._intermediate_model_text.pop(run_id, None)
            return []

        if isinstance(run_id, str) and run_id in self._streamed_model_runs:
            return []

        reasoning = extract_reasoning(output)
        text = extract_text(output)
        events: list[dict[str, Any]] = []

        if reasoning:
            _append_text_event(
                events,
                "think_delta",
                raw.get("run_id"),
                raw.get("event"),
                raw.get("name"),
                raw.get("parent_ids") or [],
                reasoning,
            )

        if text:
            _append_text_event(
                events,
                "assistant_delta",
                raw.get("run_id"),
                raw.get("event"),
                raw.get("name"),
                raw.get("parent_ids") or [],
                text,
            )

        return events


def _is_root_model_output(raw: dict[str, Any]) -> bool:
    metadata = object_or_empty(raw.get("metadata"))
    checkpoint_ns = metadata.get("langgraph_checkpoint_ns") or metadata.get(
        "checkpoint_ns"
    )
    if metadata.get("langgraph_node") == "model" and isinstance(checkpoint_ns, str):
        return checkpoint_ns.startswith("model:") and "|" not in checkpoint_ns

    parent_ids = raw.get("parent_ids") or []
    return not isinstance(parent_ids, list) or len(parent_ids) <= 1


def _is_complete_tool_intent(tool_call: dict[str, Any]) -> bool:
    name = tool_call.get("name")
    return isinstance(name, str) and bool(name.strip())


def _tool_intent_key(
    run_id: Any,
    tool_call: dict[str, Any],
    index: int,
) -> tuple[Any, ...]:
    call_id = tool_call.get("id")
    if call_id:
        return ("id", call_id)
    return ("run", run_id, tool_call.get("name"), tool_call.get("index", index))


def _append_text_event(
    events: list[dict[str, Any]],
    kind: str,
    run_id: Any,
    source_event: Any,
    name: Any,
    parent_ids: list[Any],
    text: str,
) -> None:
    if not text:
        return

    events.append(
        {
            "kind": kind,
            "id": run_id,
            "sourceEvent": source_event,
            "name": name,
            "runId": run_id,
            "parentIds": parent_ids,
            "text": text,
        }
    )
