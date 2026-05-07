from typing import Any

from minial_agent.constants.agent_mapper import (
    get_agent_label,
    get_agent_message,
    is_agent_name,
)
from minial_agent.constants.tool_mapper import get_tool_label, get_tool_message

from minial_agent.api.agent.events.activity.details import string_value


def activity_display(
    name: str | None,
    status: str,
    details: dict[str, Any],
) -> tuple[str, str]:
    agent_name = string_value(details.get("agentName")) or (
        name if is_agent_name(name) else None
    )
    agent_label = get_agent_label(agent_name)
    agent_message = get_agent_message(agent_name, status)
    if agent_label and agent_message:
        return agent_label, agent_message

    return get_tool_label(name), get_tool_message(name, status)
