from deepagents import SubAgent

from .system_prompt import SYSTEM_PROMPT
from .tools import answer_pptx_question, edit_pptx


def build_pptx_subagent() -> SubAgent:
    return {
        "name": "agent_pptx",
        "description": "Handles PPTX office file question answering and editing.",
        "system_prompt": SYSTEM_PROMPT,
        "tools": [answer_pptx_question, edit_pptx],
    }
