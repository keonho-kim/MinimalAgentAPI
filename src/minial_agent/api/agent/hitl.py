from dataclasses import dataclass
from typing import Any

from langgraph.types import Interrupt

from minial_agent.api.agent.schema import ChatRequest

APPROVAL_SCOPE_PREFIX = "Approval scope:"


@dataclass(frozen=True)
class PendingHitl:
    stream_id: str
    user_id: str
    uuid: str
    thread_id: str
    request: ChatRequest
    payload: dict[str, Any]


def extract_hitl_payload(*, stream_id: str, event: Any) -> dict[str, Any] | None:
    interrupts = event_interrupts(event)
    if not interrupts:
        return None

    interrupt = interrupts[0]
    value = interrupt_value(interrupt)
    if not isinstance(value, dict):
        return None

    actions = list_value(value.get("action_requests"))
    review_configs = list_value(value.get("review_configs"))
    normalized_actions = []
    approval_scopes = []
    for index, action in enumerate(actions):
        if not isinstance(action, dict):
            continue
        config = review_configs[index] if index < len(review_configs) else {}
        config = config if isinstance(config, dict) else {}
        description, approval_scope = split_approval_scope(action.get("description"))
        if approval_scope:
            approval_scopes.append(approval_scope)
        normalized_actions.append(
            {
                "name": action.get("name"),
                "args": action.get("args") or {},
                "description": description,
                "allowed_decisions": config.get("allowed_decisions") or [],
            }
        )
    request_scope = approval_scopes[0] if approval_scopes else None
    if any(scope != request_scope for scope in approval_scopes):
        request_scope = None
    return {
        "stream_id": stream_id,
        "actions": normalized_actions,
        "approval_scope": request_scope,
    }


def split_approval_scope(description: Any) -> tuple[Any, str | None]:
    if not isinstance(description, str):
        return description, None

    kept_lines = []
    approval_scope = None
    for line in description.splitlines():
        stripped = line.strip()
        if stripped.startswith(APPROVAL_SCOPE_PREFIX):
            value = stripped.removeprefix(APPROVAL_SCOPE_PREFIX).strip()
            approval_scope = value or None
            continue
        kept_lines.append(line)

    return "\n".join(kept_lines).strip() or None, approval_scope


def event_interrupts(event: Any) -> list[Any]:
    if not isinstance(event, dict):
        return []

    interrupts = coerce_interrupts(event.get("interrupts"))
    data = event.get("data")
    if isinstance(data, dict):
        interrupts.extend(find_interrupts(data))
    return interrupts


def find_interrupts(value: Any) -> list[Any]:
    if isinstance(value, dict):
        interrupts = value.get("__interrupt__")
        found = coerce_interrupts(interrupts)
        if found:
            return found
        for child in value.values():
            child_found = find_interrupts(child)
            if child_found:
                return child_found
    elif isinstance(value, (list, tuple)):
        for child in value:
            found = find_interrupts(child)
            if found:
                return found
    return []


def coerce_interrupts(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list | tuple):
        return list(value)
    return [value]


def interrupt_value(interrupt: Any) -> Any:
    if isinstance(interrupt, Interrupt):
        return interrupt.value
    if isinstance(interrupt, dict):
        return interrupt.get("value")
    return None


def list_value(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list | tuple) else []
