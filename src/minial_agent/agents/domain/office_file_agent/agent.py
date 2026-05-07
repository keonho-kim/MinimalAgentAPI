from textwrap import dedent

from deepagents.backends.protocol import BackendProtocol
from deepagents.middleware.filesystem import FilesystemMiddleware
from deepagents.middleware.patch_tool_calls import PatchToolCallsMiddleware
from deepagents.middleware.subagents import CompiledSubAgent, SubAgentMiddleware
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware, ToolCallLimitMiddleware
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.store.base import BaseStore

from minial_agent.agents.domain.office_file_agent.subagents import (
    build_docx_subagent,
    build_hwpx_subagent,
    build_pdf_subagent,
    build_pptx_subagent,
    build_xlsx_subagent,
)
from minial_agent.agents.domain.office_file_agent.system_prompt import OFFICE_FILE_AGENT_SYSTEM_PROMPT

FILESYSTEM_HITL_POLICY = {
    "write_file": {
        "allowed_decisions": ["approve", "edit", "reject"],
        "description": (
            "A file write requires approval before it changes the workspace."
        ),
    },
    "edit_file": {
        "allowed_decisions": ["approve", "edit", "reject"],
        "description": (
            "A file edit requires approval before it changes the workspace."
        ),
    },
}


WORKER_EDIT_TOOLS = {
    "agent_docx": "edit_docx",
    "agent_hwpx": "edit_hwpx",
    "agent_pptx": "edit_pptx",
    "agent_xlsx": "edit_xlsx",
}

WORKER_TOOL_LIMITS = {
    "agent_pdf": [
        {
            "tool_name": "answer_pdf_question",
            "run_limit": 1,
            "exit_behavior": "continue",
        }
    ],
}


def build_office_file_subagent(
    *,
    model: BaseChatModel,
    backend: BackendProtocol,
    store: BaseStore | None = None,
    checkpointer: BaseCheckpointSaver | bool | None = None,
):

    agent = create_agent(
        model=model,
        system_prompt=OFFICE_FILE_AGENT_SYSTEM_PROMPT,
        middleware=[
            FilesystemMiddleware(
                backend=backend,
            ),
            SubAgentMiddleware(
                backend=backend,
                subagents=_build_worker_subagents(
                    model=model,
                    backend=backend,
                    store=store,
                    checkpointer=checkpointer,
                ),
            ),
            HumanInTheLoopMiddleware(interrupt_on=FILESYSTEM_HITL_POLICY),
            PatchToolCallsMiddleware(),
        ],
        store=store,
        checkpointer=checkpointer,
    )

    return CompiledSubAgent(
        name="office_file_agent",
        description=dedent(
            """
        Routes office file requests to HWPX, DOCX, PPTX, XLSX, and PDF worker agents.
        """.strip()
        ),
        runnable=agent,
    )


def _build_worker_subagents(
    *,
    model: BaseChatModel,
    backend: BackendProtocol,
    store: BaseStore | None,
    checkpointer: BaseCheckpointSaver | bool | None,
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
            build_pdf_subagent(),
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

    interrupt_on = dict(FILESYSTEM_HITL_POLICY)
    edit_tool = WORKER_EDIT_TOOLS.get(spec["name"])

    if edit_tool:
        interrupt_on[edit_tool] = {
            "allowed_decisions": ["approve", "edit", "reject"],
            "description": (
                "An office file edit requires approval before it changes the workspace."
            ),
        }

    middleware = [
        FilesystemMiddleware(backend=backend),
        HumanInTheLoopMiddleware(interrupt_on=interrupt_on),
    ]
    middleware.extend(
        ToolCallLimitMiddleware(**limit)
        for limit in WORKER_TOOL_LIMITS.get(spec["name"], [])
    )
    middleware.append(PatchToolCallsMiddleware())

    runnable = create_agent(
        model=model,
        system_prompt=spec["system_prompt"],
        tools=spec["tools"],
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
