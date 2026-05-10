from deepagents import SubAgent

from minial_agent.agents.domain.data_expertise.subagents.data_analyst.system_prompt import (
    DATA_ANALYST_SYSTEM_PROMPT,
)


def build_data_analyst_subagent() -> SubAgent:
    return {
        "name": "data_analyst",
        "description": (
            "Handles data-expertise tasks such as dataset inspection, Python analysis, "
            "CSV/JSON/text outputs, and JavaScript or HTML visualizations."
        ),
        "system_prompt": DATA_ANALYST_SYSTEM_PROMPT,
        "tools": [],
    }
