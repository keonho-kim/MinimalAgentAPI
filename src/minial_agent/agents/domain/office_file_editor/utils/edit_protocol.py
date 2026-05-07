from typing import Callable

from minial_agent.agents.utils.runtime import invoke_text_llm


OperationSelector = Callable[[str], str]
SlotFiller = Callable[[str, str], str]


def select_operation(
    *,
    instruction: str,
    prompt: str,
    selector: OperationSelector | None = None,
) -> str:
    operation = (
        selector(instruction)
        if selector
        else invoke_text_llm(
            prompt.format(instruction=instruction),
            disable_streaming=True,
        )
    )
    operation = _strict_one_line(operation, "Edit operation output")
    if "=" in operation or ";" in operation:
        raise ValueError("Edit operation output must contain only the operation name.")
    return operation


def fill_slots(
    *,
    operation: str,
    instruction: str,
    prompt: str,
    slot_filler: SlotFiller | None = None,
) -> dict[str, str]:
    raw_slots = (
        slot_filler(operation, instruction)
        if slot_filler
        else invoke_text_llm(
            prompt.format(operation=operation, instruction=instruction),
            disable_streaming=True,
        )
    )
    return parse_slots(raw_slots)


def parse_slots(instruction: str) -> dict[str, str]:
    instruction = _strict_one_line(instruction, "Edit slot output")
    fields = {}
    for item in instruction.split(";"):
        item = item.strip()
        if not item:
            raise ValueError("Edit slot output contains an empty segment.")
        if "=" not in item:
            raise ValueError("Edit slot output must use KEY=VALUE format.")
        key, value = item.split("=", 1)
        key = key.strip().upper()
        value = value.strip()
        if not key or value == "":
            raise ValueError("Edit slot output must use non-empty KEY=VALUE pairs.")
        fields[key] = value
    if not fields:
        raise ValueError("Edit slot output must use KEY=VALUE format.")
    return fields


def require_slots(
    *,
    operation: str,
    slots: dict[str, str],
    required: set[str],
) -> None:
    missing = sorted(required - set(slots))
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"{operation} requires slot(s): {joined}.")


def _strict_one_line(value: str, label: str) -> str:
    normalized = value.strip()
    if "\n" in normalized or "\r" in normalized:
        raise ValueError(f"{label} must be one line.")
    if normalized.startswith(("{", "[", "```")):
        raise ValueError(f"{label} must not be JSON or markdown.")
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized
