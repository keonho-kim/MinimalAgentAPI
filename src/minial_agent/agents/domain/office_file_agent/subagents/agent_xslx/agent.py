from deepagents import SubAgent

from .system_prompt import SYSTEM_PROMPT
from .tools import (
    answer_xlsx_question,
    edit_xlsx,
    inspect_xlsx_sheet,
    inspect_xlsx_workbook,
    map_reduce_xlsx_sheets,
)


def build_xslx_subagent() -> SubAgent:
    return {
        "name": "agent_xslx",
        "description": "Handles XLSX office file question answering, editing, and inspection.",
        "system_prompt": SYSTEM_PROMPT,
        "tools": [
            answer_xlsx_question,
            edit_xlsx,
            inspect_xlsx_workbook,
            inspect_xlsx_sheet,
            map_reduce_xlsx_sheets,
        ],
    }


def build_xlsx_subagent() -> SubAgent:
    return build_xslx_subagent()
