from deepagents.backends.protocol import BackendProtocol
from deepagents.middleware.patch_tool_calls import PatchToolCallsMiddleware
from deepagents.middleware.subagents import CompiledSubAgent
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.store.base import BaseStore

from minial_agent.agents.domain.office_file_editor.subagents import (
    build_docx_subagent,
    build_hwpx_subagent,
    build_pptx_subagent,
    build_xlsx_subagent,
)


WORKER_HITL_TOOLS = {
    "editor_docx": {"edit_docx"},
    "editor_hwpx": {"edit_hwpx"},
    "editor_pptx": {"edit_pptx"},
    "editor_xlsx": {
        "commit_xlsx_session",
        "export_xlsx_range",
        "export_xlsx_dataframe",
        "export_xlsx_detected_table_csv",
        "export_xlsx_dataframe_csv",
    },
}


def build_office_edit_subagents(
    *,
    model: BaseChatModel,
    backend: BackendProtocol,
    store: BaseStore | None = None,
    checkpointer: BaseCheckpointSaver | bool | None = None,
) -> list[CompiledSubAgent]:
    return [
        _compile_worker_subagent(
            spec=spec,
            model=model,
            backend=backend,
            store=store,
            checkpointer=checkpointer,
        )
        for spec in (
            build_hwpx_subagent(),
            build_docx_subagent(),
            build_pptx_subagent(),
            build_xlsx_subagent(),
        )
    ]


def _compile_worker_subagent(
    *,
    spec: dict,
    model: BaseChatModel,
    backend: BackendProtocol,
    store: BaseStore | None,
    checkpointer: BaseCheckpointSaver | bool | None,
) -> CompiledSubAgent:
    from minial_agent.agents.tools import ALL_AGENT_TOOLS

    hitl_tools = WORKER_HITL_TOOLS.get(spec["name"])
    if not hitl_tools:
        raise ValueError(f"Unsupported office edit subagent: {spec['name']}")

    interrupt_on = {
        tool_name: {
            "allowed_decisions": ["approve", "edit", "reject"],
            "description": "An office file edit requires approval before it changes the workspace.",
        }
        for tool_name in hitl_tools
    }

    middleware = [
        HumanInTheLoopMiddleware(interrupt_on=interrupt_on),
        PatchToolCallsMiddleware(),
    ]

    runnable = create_agent(
        model=model,
        system_prompt=spec["system_prompt"],
        tools=[*ALL_AGENT_TOOLS, *spec["tools"]],
        middleware=middleware,
        store=store,
        checkpointer=checkpointer,
        name=spec["name"],
    )
    return CompiledSubAgent(
        name=spec["name"],
        description=spec["description"],
        runnable=runnable,
    )
