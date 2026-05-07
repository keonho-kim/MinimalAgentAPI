from deepagents import SubAgent

from minial_agent.agents.domain.office_file_editor.subagents.editor_hwpx.system_prompt import (
    HWPX_AGENT_SYSTEM_PROMPT,
)
from minial_agent.agents.domain.office_file_editor.subagents.editor_hwpx.workflow.edit import edit_hwpx


def build_hwpx_subagent() -> SubAgent:
    return {
        "name": "editor_hwpx",
        "description": "Handles HWPX office file editing.",
        "system_prompt": HWPX_AGENT_SYSTEM_PROMPT,
        "tools": [edit_hwpx],
    }
