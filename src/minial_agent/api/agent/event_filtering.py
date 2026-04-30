import json
from typing import Any


class InternalProtocolFilter:
    def __init__(self) -> None:
        self._selector_text_buffers: dict[str, str] = {}

    def filter_text(self, run_id: Any, text: str) -> str:
        if not text:
            return ""

        text = _remove_internal_protocol_text(text)
        if not text:
            return ""

        buffer_key = run_id if isinstance(run_id, str) else None

        if buffer_key:
            buffered = self._selector_text_buffers.get(buffer_key)
            if buffered is not None:
                combined = buffered + text
                if _looks_like_tool_selector_text(combined):
                    if _selector_fragment_is_finished(combined):
                        self._selector_text_buffers.pop(buffer_key, None)
                    else:
                        self._selector_text_buffers[buffer_key] = combined
                    return ""

                self._selector_text_buffers.pop(buffer_key, None)
                return _remove_internal_protocol_text(combined)

        if _looks_like_tool_selector_text(text):
            return ""

        if buffer_key and _could_start_tool_selector_text(text):
            self._selector_text_buffers[buffer_key] = text
            return ""

        return text


def _looks_like_tool_selector_text(value: str) -> bool:
    stripped = _unwrap_markdown_code(value.strip())
    if not stripped:
        return False

    parsed = _parse_tool_selector_json(stripped)
    if parsed is not None:
        return True

    lowered = stripped.lower()
    has_tools_key = (
        '"tools"' in lowered
        or '"tools":' in lowered
        or stripped.startswith('tools":')
        or stripped.startswith("tools':")
    )
    return has_tools_key and _is_jsonish_selector_fragment(stripped)


def _could_start_tool_selector_text(value: str) -> bool:
    stripped = _unwrap_markdown_code(value.strip()).lower()
    if not stripped:
        return False

    return (
        stripped in {"{", '{"', "{'"}
        or stripped.startswith('{"t')
        or stripped.startswith("{'t")
    )


def _selector_fragment_is_finished(value: str) -> bool:
    stripped = _unwrap_markdown_code(value.strip())
    return stripped.endswith("}") or len(stripped) > 400


def _parse_tool_selector_json(value: str) -> dict[str, Any] | None:
    candidates = [_unwrap_markdown_code(value)]
    if value.startswith('tools":'):
        candidates.append('{"' + value)

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue

        if _is_tool_selector_object(parsed):
            return parsed

    return None


def _is_tool_selector_object(value: Any) -> bool:
    if not isinstance(value, dict) or set(value.keys()) != {"tools"}:
        return False

    tools = value.get("tools")
    return isinstance(tools, list) and all(isinstance(tool, str) for tool in tools)


def _is_jsonish_selector_fragment(value: str) -> bool:
    allowed_punctuation = set("{}[]:\"'_,.-/ \n\r\t")
    return all(char.isalnum() or char in allowed_punctuation for char in value)


def _unwrap_markdown_code(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()

    if stripped.startswith("`") and stripped.endswith("`") and len(stripped) >= 2:
        return stripped[1:-1].strip()

    return stripped


def _is_empty_markdown_code(value: str) -> bool:
    stripped = value.strip()
    if stripped == "``":
        return True

    if not stripped.startswith("```") or not stripped.endswith("```"):
        return False

    lines = stripped.splitlines()
    return len(lines) >= 2 and not "\n".join(lines[1:-1]).strip()


def _remove_internal_protocol_text(value: str) -> str:
    text = value
    removed_protocol_text = False

    while True:
        cleaned = _remove_one_tool_selector_json(text)
        if cleaned == text:
            break
        removed_protocol_text = True
        text = cleaned

    if removed_protocol_text and not text:
        return ""

    if _is_empty_markdown_code(text):
        return ""

    cleaned = _remove_pseudo_tool_call_text(text)
    if cleaned != text:
        removed_protocol_text = True
        text = cleaned

    if removed_protocol_text and not text.strip():
        return ""

    return text


def _remove_one_tool_selector_json(value: str) -> str:
    for start in _candidate_json_starts(value):
        parsed = _parse_json_object_at(value, start)
        if parsed is None:
            continue

        end, obj = parsed
        if _is_tool_selector_object(obj):
            return value[:start] + value[end:]

    return value


def _candidate_json_starts(value: str) -> list[int]:
    starts = [index for index, char in enumerate(value) if char == "{"]
    if value.startswith('tools":') or value.startswith("tools':"):
        starts.insert(0, 0)
    return starts


def _parse_json_object_at(value: str, start: int) -> tuple[int, Any] | None:
    if start >= len(value):
        return None

    source = value[start:]
    prefix_length = 0
    if source.startswith('tools":'):
        source = '{"' + source
        prefix_length = 2

    decoder = json.JSONDecoder()
    try:
        obj, end = decoder.raw_decode(source)
    except json.JSONDecodeError:
        return None

    return start + end - prefix_length, obj


def _remove_pseudo_tool_call_text(value: str) -> str:
    lines = value.splitlines()
    kept: list[str] = []
    skipping = False

    for line in lines:
        stripped = line.strip()
        lowered = stripped.lower()
        if lowered == "thought":
            skipping = True
            continue
        if _looks_like_pseudo_tool_call(stripped):
            skipping = True
            continue
        if skipping:
            if not stripped or _looks_like_pseudo_tool_call(stripped):
                continue
            skipping = False

        kept.append(line)

    return "\n".join(kept)


def _looks_like_pseudo_tool_call(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith("call:filesystem:") or (
        lowered.startswith("call:") and "{" in lowered
    )
