from deepagents import SubAgent

from minial_agent.agents.domain.office_file_editor.subagents.editor_docx.system_prompt import (
    DOCX_AGENT_SYSTEM_PROMPT,
)
from minial_agent.agents.domain.office_file_editor.subagents.editor_docx.workflow.edit import edit_docx


def build_docx_subagent() -> SubAgent:
    return {
        "name": "editor_docx",
        "description": "Handles DOCX office file editing.",
        "system_prompt": DOCX_AGENT_SYSTEM_PROMPT,
        "tools": [edit_docx],
    }
