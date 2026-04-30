from deepagents import SubAgent

from .system_prompt import SYSTEM_PROMPT
from .tools import answer_docx_question, edit_docx


def build_docx_subagent() -> SubAgent:
    return {
        "name": "agent_docx",
        "description": "Handles DOCX office file question answering and editing.",
        "system_prompt": SYSTEM_PROMPT,
        "tools": [answer_docx_question, edit_docx],
    }
