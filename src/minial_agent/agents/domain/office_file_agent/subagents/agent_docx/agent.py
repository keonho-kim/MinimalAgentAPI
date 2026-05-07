from deepagents import SubAgent

from minial_agent.agents.domain.office_file_agent.subagents.agent_docx.system_prompt import (
    DOCX_AGENT_SYSTEM_PROMPT,
)
from minial_agent.agents.domain.office_file_agent.subagents.agent_docx.workflow.edit import edit_docx
from minial_agent.agents.domain.office_file_agent.subagents.agent_docx.workflow.read import answer_docx_question


def build_docx_subagent() -> SubAgent:
    return {
        "name": "agent_docx",
        "description": "Handles DOCX office file question answering and editing.",
        "system_prompt": DOCX_AGENT_SYSTEM_PROMPT,
        "tools": [answer_docx_question, edit_docx],
    }
