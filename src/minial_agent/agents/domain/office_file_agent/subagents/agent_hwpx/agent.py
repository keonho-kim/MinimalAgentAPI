from deepagents import SubAgent

from minial_agent.agents.domain.office_file_agent.subagents.agent_hwpx.system_prompt import SYSTEM_PROMPT
from minial_agent.agents.domain.office_file_agent.subagents.agent_hwpx.workflow.edit import edit_hwpx
from minial_agent.agents.domain.office_file_agent.subagents.agent_hwpx.workflow.read import answer_hwpx_question


def build_hwpx_subagent() -> SubAgent:
    return {
        "name": "agent_hwpx",
        "description": "Handles HWPX office file question answering and editing.",
        "system_prompt": SYSTEM_PROMPT,
        "tools": [answer_hwpx_question, edit_hwpx],
    }
