from deepagents import SubAgent

from minial_agent.agents.domain.office_file_agent.subagents.agent_pptx.system_prompt import SYSTEM_PROMPT
from minial_agent.agents.domain.office_file_agent.subagents.agent_pptx.workflow.edit import edit_pptx
from minial_agent.agents.domain.office_file_agent.subagents.agent_pptx.workflow.read import answer_pptx_question


def build_pptx_subagent() -> SubAgent:
    return {
        "name": "agent_pptx",
        "description": "Handles PPTX office file question answering and editing.",
        "system_prompt": SYSTEM_PROMPT,
        "tools": [answer_pptx_question, edit_pptx],
    }
