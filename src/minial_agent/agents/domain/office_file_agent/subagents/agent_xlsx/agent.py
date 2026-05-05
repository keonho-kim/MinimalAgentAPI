from deepagents import SubAgent

from minial_agent.agents.domain.office_file_agent.subagents.agent_xlsx.system_prompt import SYSTEM_PROMPT
from minial_agent.agents.domain.office_file_agent.subagents.agent_xlsx.workflow.edit import edit_xlsx
from minial_agent.agents.domain.office_file_agent.subagents.agent_xlsx.workflow.read import answer_xlsx_question


def build_xlsx_subagent() -> SubAgent:
    return {
        "name": "agent_xlsx",
        "description": "Handles XLSX office file question answering and editing.",
        "system_prompt": SYSTEM_PROMPT,
        "tools": [
            answer_xlsx_question,
            edit_xlsx,
        ],
    }
