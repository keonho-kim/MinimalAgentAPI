from deepagents import SubAgent

from minial_agent.agents.domain.office_file_editor.subagents.editor_pptx.system_prompt import (
    PPTX_AGENT_SYSTEM_PROMPT,
)
from minial_agent.agents.domain.office_file_editor.subagents.editor_pptx.tools import (
    inspect_pptx_deck,
)
from minial_agent.agents.domain.office_file_editor.subagents.editor_pptx.workflow.edit import edit_pptx


def build_pptx_subagent() -> SubAgent:
    return {
        "name": "editor_pptx",
        "description": "Handles PPTX office file editing.",
        "system_prompt": PPTX_AGENT_SYSTEM_PROMPT,
        "tools": [inspect_pptx_deck, edit_pptx],
    }
