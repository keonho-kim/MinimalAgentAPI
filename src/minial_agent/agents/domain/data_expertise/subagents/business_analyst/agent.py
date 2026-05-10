from deepagents import SubAgent

from minial_agent.agents.domain.data_expertise.subagents.business_analyst.system_prompt import (
    BUSINESS_ANALYST_SYSTEM_PROMPT,
)


def build_business_analyst_subagent() -> SubAgent:
    return {
        "name": "business_analyst",
        "description": (
            "Handles business interpretation, KPI framing, stakeholder caveats, "
            "and critique of data analysis conclusions."
        ),
        "system_prompt": BUSINESS_ANALYST_SYSTEM_PROMPT,
        "tools": [],
    }
