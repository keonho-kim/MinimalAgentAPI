import json
from pathlib import Path
from typing import Any

from fastapi.encoders import jsonable_encoder

from minial_agent.constants.tool_mapper import get_tool_label, get_tool_message

WRITE_FILE_PARENT_RUNNING_MESSAGE = "AGENT가 필요한 폴더를 만들고 파일 작성을 시작합니다."
WRITE_FILE_PARENT_COMPLETED_MESSAGE = "AGENT가 필요한 폴더를 만들고 파일 작성을 완료했습니다."

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


class StreamEventNormalizer:
    def __init__(self, workspace_root: str | Path | None = None) -> None:
        self._streamed_model_runs: set[str] = set()
        self._workspace_root = Path(workspace_root).resolve() if workspace_root else None
        self._activity_contexts: dict[str, dict[str, Any]] = {}

    def normalize(self, raw: Any) -> list[dict[str, Any]]:
        raw = _jsonable_mapping(raw)
        if not isinstance(raw, dict):
            return []

        event_name = raw.get("event") or raw.get("name")

        if event_name in {"on_chat_model_stream", "on_llm_stream"}:
            return self._normalize_model_stream(raw)

        if event_name in {"on_chat_model_end", "on_llm_end"}:
            return self._normalize_model_end(raw)

        if event_name == "on_tool_start":
            return [
                self._create_activity(
                    raw,
                    "tool",
                    "running",
                    raw.get("data", {}).get("input"),
                )
            ]

        if event_name == "on_tool_end":
            return [
                self._create_activity(
                    raw,
                    "tool",
                    "completed",
                    None,
                    raw.get("data", {}).get("output"),
                )
            ]

        if event_name == "on_tool_error":
            return [
                self._create_activity(
                    raw,
                    "tool",
                    "error",
                    None,
                    raw.get("data", {}).get("error"),
                )
            ]

        if event_name == "on_retriever_start":
            return [
                self._create_activity(
                    raw,
                    "retriever",
                    "running",
                    raw.get("data", {}).get("input"),
                )
            ]

        if event_name == "on_retriever_end":
            return [
                self._create_activity(
                    raw,
                    "retriever",
                    "completed",
                    raw.get("data", {}).get("input"),
                    raw.get("data", {}).get("output"),
                )
            ]

        if event_name in {"custom", "on_custom_event"}:
            return [self._create_activity(raw, "custom", "running", raw.get("data"))]

        if event_name in {"on_chain_start", "on_chain_end"}:
            activity = self._normalize_visible_chain(raw, event_name)
            return [activity] if activity else []

        return []

    def _normalize_model_stream(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        data = _object_or_empty(raw.get("data"))
        chunk = data.get("chunk") or data.get("output") or data.get("message") or data
        tool_calls = _extract_tool_calls(chunk)
        reasoning = _extract_reasoning(chunk)
        text = _extract_text(chunk)
        events: list[dict[str, Any]] = []
        run_id = raw.get("run_id")

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
            name = tool_call.get("name") or "tool"
            input_value = tool_call.get("args")
            status = "pending"
            events.append(
                {
                    "kind": "activity",
                    "type": "tool",
                    "id": tool_call.get("id")
                    or f"{run_id}:{tool_call.get('index', index)}",
                    "parentIds": raw.get("parent_ids") or [],
                    "name": name,
                    "label": get_tool_label(name),
                    "message": get_tool_message(name, status),
                    "status": status,
                    "input": input_value,
                    "summary": _summarize_activity(name, input_value),
                }
            )

        return events

    def _normalize_model_end(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        run_id = raw.get("run_id")
        if isinstance(run_id, str) and run_id in self._streamed_model_runs:
            return []

        data = _object_or_empty(raw.get("data"))
        output = data.get("output") or data.get("chunk") or data.get("message")
        reasoning = _extract_reasoning(output)
        text = _extract_text(output)
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

    def _create_activity(
        self,
        raw: dict[str, Any],
        activity_type: str,
        status: str,
        input_value: Any = None,
        output: Any = None,
    ) -> dict[str, Any]:
        name = raw.get("name") or activity_type
        activity_id = raw.get("run_id") or f"{activity_type}:{name}"
        summary = _summarize_activity(name, input_value, output)
        folder_context = self._get_write_file_parent_context(name, input_value)

        if not folder_context and isinstance(activity_id, str):
            folder_context = self._activity_contexts.get(activity_id)

        if folder_context:
            summary.update(folder_context["summary"])
            if status == "running" and isinstance(activity_id, str):
                self._activity_contexts[activity_id] = folder_context

        message = get_tool_message(name, status)
        if folder_context and status == "running":
            message = WRITE_FILE_PARENT_RUNNING_MESSAGE
        elif folder_context and status == "completed":
            if folder_context["real_parent_path"].exists() and not _output_looks_error(output):
                summary["parentDirectoryCreated"] = True
                message = WRITE_FILE_PARENT_COMPLETED_MESSAGE
        elif folder_context and status == "error":
            summary["parentDirectoryCreated"] = False

        if isinstance(activity_id, str) and status in {"completed", "error"}:
            self._activity_contexts.pop(activity_id, None)

        return {
            "kind": "activity",
            "type": activity_type,
            "id": activity_id,
            "parentIds": raw.get("parent_ids") or [],
            "name": name,
            "label": get_tool_label(name),
            "message": message,
            "status": status,
            "input": input_value,
            "output": output,
            "summary": summary,
        }

    def _normalize_visible_chain(
        self,
        raw: dict[str, Any],
        event_name: str,
    ) -> dict[str, Any] | None:
        name = raw.get("name") or ""
        looks_like_subagent = name == "task" or "subagent" in name.lower()

        if not looks_like_subagent:
            return None

        data = _object_or_empty(raw.get("data"))
        return self._create_activity(
            raw,
            "chain",
            "running" if event_name.endswith("_start") else "completed",
            data.get("input"),
            data.get("output"),
        )

    def _get_write_file_parent_context(
        self,
        name: str,
        input_value: Any,
    ) -> dict[str, Any] | None:
        if name != "write_file" or self._workspace_root is None:
            return None

        source = _object_or_empty(input_value)
        virtual_path = source.get("file_path") or source.get("path")
        if not isinstance(virtual_path, str) or not virtual_path.strip():
            return None

        resolved_path = _resolve_workspace_virtual_path(
            self._workspace_root,
            virtual_path,
        )
        if resolved_path is None:
            return None

        parent_path = resolved_path.parent
        if parent_path == self._workspace_root or parent_path.exists():
            return None

        virtual_parent_path = _virtual_parent_path(virtual_path)
        return {
            "real_parent_path": parent_path,
            "summary": {
                "createsParentDirectory": True,
                "parentPath": virtual_parent_path,
                "description": f"필요한 폴더: {virtual_parent_path}",
            },
        }


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


def _extract_text(value: Any) -> str:
    if isinstance(value, str):
        return value

    if isinstance(value, list):
        return "".join(_extract_text(item) for item in value)

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
        return "".join(_extract_text(item) for item in value["content"])

    if "kwargs" in value:
        return _extract_text(value["kwargs"])

    return ""


def _extract_reasoning(value: Any) -> str:
    if isinstance(value, str):
        return ""

    if isinstance(value, list):
        return "".join(_extract_reasoning(item) for item in value)

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
            extracted = _extract_reasoning(nested)
            if extracted:
                parts.append(extracted)

    content = value.get("content")
    if isinstance(content, list):
        extracted = _extract_reasoning(content)
        if extracted:
            parts.append(extracted)

    return "".join(parts)


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


def _extract_tool_calls(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, dict):
        return []

    calls: list[dict[str, Any]] = []
    content = value.get("content") if isinstance(value.get("content"), list) else []

    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") in {"tool_call", "tool_call_chunk"}:
            calls.append(
                {
                    "id": block.get("id"),
                    "name": block.get("name"),
                    "args": _parse_maybe_json(block.get("args")),
                    "index": block.get("index"),
                }
            )

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
                    "args": _parse_maybe_json(call.get("args")),
                    "index": call.get("index"),
                }
            )

    return _deduplicate_tool_calls(calls)


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


def _summarize_activity(name: str, input_value: Any, output: Any = None) -> dict[str, Any]:
    source = _object_or_empty(input_value)
    result = _object_or_empty(output)

    return {
        "path": source.get("file_path")
        or source.get("path")
        or result.get("file_path")
        or result.get("path"),
        "command": source.get("command"),
        "query": source.get("query") or source.get("pattern"),
        "description": source.get("description"),
        "result": _preview_value(output),
    }


def _resolve_workspace_virtual_path(
    workspace_root: Path,
    virtual_path: str,
) -> Path | None:
    relative_path = virtual_path.strip().lstrip("/")
    if not relative_path:
        return None

    resolved_path = (workspace_root / relative_path).resolve()
    try:
        resolved_path.relative_to(workspace_root)
    except ValueError:
        return None

    return resolved_path


def _virtual_parent_path(virtual_path: str) -> str:
    normalized = "/" + virtual_path.strip().lstrip("/")
    parent = str(Path(normalized).parent)
    return "/" if parent == "." else parent


def _output_looks_error(output: Any) -> bool:
    output = _jsonable_mapping(output)

    if isinstance(output, str):
        return "error" in output.lower()

    if isinstance(output, dict):
        error = output.get("error")
        return bool(error)

    return False


def _object_or_empty(value: Any) -> dict[str, Any]:
    value = _jsonable_mapping(value)
    return value if isinstance(value, dict) else {}


def _jsonable_mapping(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _jsonable_mapping(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_jsonable_mapping(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonable_mapping(item) for item in value]

    try:
        return jsonable_encoder(value)
    except Exception:
        return value


def _preview_value(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, str):
        return _truncate(value)

    if isinstance(value, dict):
        useful = (
            value.get("message")
            or value.get("error")
            or value.get("result")
            or value.get("output")
            or value.get("content")
            or value.get("file_path")
            or value.get("path")
        )
        return _truncate(str(useful)) if useful else _truncate(json.dumps(value, ensure_ascii=False))

    return _truncate(str(value))


def _truncate(value: str, max_length: int = 700) -> str:
    if len(value) <= max_length:
        return value

    return f"{value[:max_length]}..."


def _parse_maybe_json(value: Any) -> Any:
    if not isinstance(value, str):
        return value

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value
