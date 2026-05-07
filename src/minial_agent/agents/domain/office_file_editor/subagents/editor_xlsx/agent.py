from deepagents import SubAgent

from minial_agent.agents.domain.office_file_editor.subagents.editor_xlsx.system_prompt import (
    XLSX_AGENT_SYSTEM_PROMPT,
)
from minial_agent.agents.domain.office_file_editor.subagents.editor_xlsx.tools import (
    XLSX_SESSION_TOOLS,
)


def build_xlsx_subagent() -> SubAgent:
    return {
        "name": "editor_xlsx",
        "description": "Handles XLSX workbook analysis, editing, formulas, dataframe transforms, and export.",
        "system_prompt": XLSX_AGENT_SYSTEM_PROMPT,
        "tools": XLSX_SESSION_TOOLS,
    }
