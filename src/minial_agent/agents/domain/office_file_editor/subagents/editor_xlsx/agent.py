from deepagents import SubAgent

from minial_agent.agents.domain.office_file_editor.subagents.editor_xlsx.system_prompt import (
    XLSX_AGENT_SYSTEM_PROMPT,
)
from minial_agent.agents.domain.office_file_editor.subagents.editor_xlsx.workflow.edit import edit_xlsx


def build_xlsx_subagent() -> SubAgent:
    return {
        "name": "editor_xlsx",
        "description": "Handles XLSX office file editing.",
        "system_prompt": XLSX_AGENT_SYSTEM_PROMPT,
        "tools": [edit_xlsx],
    }
