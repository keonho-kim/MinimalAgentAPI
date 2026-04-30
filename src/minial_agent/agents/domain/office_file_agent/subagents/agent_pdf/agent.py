from deepagents import SubAgent

from .system_prompt import SYSTEM_PROMPT
from .tools import answer_pdf_question


def build_pdf_subagent() -> SubAgent:
    return {
        "name": "agent_pdf",
        "description": "Handles PDF question answering. PDF editing is unsupported.",
        "system_prompt": SYSTEM_PROMPT,
        "tools": [answer_pdf_question],
    }
