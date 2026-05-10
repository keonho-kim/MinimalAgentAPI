from deepagents import SubAgent

from minial_agent.agents.domain.data_expertise.subagents.data_scientist.system_prompt import (
    DATA_SCIENTIST_SYSTEM_PROMPT,
)


def build_data_scientist_subagent() -> SubAgent:
    return {
        "name": "data_scientist",
        "description": (
            "Handles statistical checks, modeling judgment, uncertainty, validation, "
            "and critique of analytical methods."
        ),
        "system_prompt": DATA_SCIENTIST_SYSTEM_PROMPT,
        "tools": [],
    }
