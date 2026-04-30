from deepagents import SubAgent

from .system_prompt import SYSTEM_PROMPT
from .tools import answer_hwpx_question, edit_hwpx


def build_hwpx_subagent() -> SubAgent:
    return {
        "name": "agent_hwpx",
        "description": "Handles HWPX office file question answering and editing.",
        "system_prompt": SYSTEM_PROMPT,
        "tools": [answer_hwpx_question, edit_hwpx],
    }
