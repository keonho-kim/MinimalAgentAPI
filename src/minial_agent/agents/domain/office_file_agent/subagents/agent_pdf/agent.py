from deepagents import SubAgent

from minial_agent.agents.domain.office_file_agent.subagents.agent_pdf.system_prompt import (
    PDF_AGENT_SYSTEM_PROMPT,
)
from minial_agent.agents.domain.office_file_agent.subagents.agent_pdf.workflow.read import answer_pdf_question


def build_pdf_subagent() -> SubAgent:
    return {
        "name": "agent_pdf",
        "description": "Handles PDF question answering. PDF editing is unsupported.",
        "system_prompt": PDF_AGENT_SYSTEM_PROMPT,
        "tools": [answer_pdf_question],
    }
