from deepagents.backends.protocol import BackendProtocol
from deepagents.middleware.filesystem import FilesystemMiddleware
from deepagents.middleware.patch_tool_calls import PatchToolCallsMiddleware
from deepagents.middleware.subagents import CompiledSubAgent
from deepagents.middleware.subagents import SubAgentMiddleware
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.store.base import BaseStore

from minial_agent.agents.domain.data_expertise.execution_backend import (
    DataExecutionBackend,
)
from minial_agent.agents.domain.data_expertise.system_prompt import (
    DATA_EXPERTISE_SYSTEM_PROMPT,
)
from minial_agent.agents.domain.data_expertise.subagents import (
    build_business_analyst_subagent,
    build_data_analyst_subagent,
    build_data_scientist_subagent,
)
from minial_agent.agents.tools import ALL_AGENT_TOOLS


DATA_EXPERTISE_HITL_TOOLS = {
    "write_file",
    "edit_file",
    "execute",
}
DATA_EXPERTISE_MAX_EXECUTE_TIMEOUT_SECONDS = 600
DATA_EXPERTISE_APPROVAL_DESCRIPTION = (
    "A data expertise file write or code execution requires approval.\n"
    "Approval scope: data_expertise"
)

ROUND_TABLE_TASK_DESCRIPTION = """Delegate one visible round-table turn to a data expertise worker.

Available workers:
{available_agents}

Use this task tool for each worker turn. Pass the current round, prior worker outputs,
the transcript path, and the exact artifact folder the worker owns."""


def build_data_expertise_subagents(
    *,
    model: BaseChatModel,
    backend: BackendProtocol,
    store: BaseStore | None = None,
    checkpointer: BaseCheckpointSaver | bool | None = None,
) -> list[CompiledSubAgent]:
    execution_backend = DataExecutionBackend.from_backend(backend)
    worker_subagents = [
        _compile_worker_subagent(
            spec=spec,
            model=model,
            backend=execution_backend,
            store=store,
            checkpointer=checkpointer,
        )
        for spec in (
            build_data_analyst_subagent(),
            build_business_analyst_subagent(),
            build_data_scientist_subagent(),
        )
    ]
    return [
        _compile_team_subagent(
            model=model,
            backend=execution_backend,
            worker_subagents=worker_subagents,
            store=store,
            checkpointer=checkpointer,
        )
    ]


def _compile_worker_subagent(
    *,
    spec: dict,
    model: BaseChatModel,
    backend: DataExecutionBackend,
    store: BaseStore | None,
    checkpointer: BaseCheckpointSaver | bool | None,
) -> CompiledSubAgent:
    interrupt_on = {
        tool_name: {
            "allowed_decisions": ["approve", "edit", "reject"],
            "description": DATA_EXPERTISE_APPROVAL_DESCRIPTION,
        }
        for tool_name in DATA_EXPERTISE_HITL_TOOLS
    }

    runnable = create_agent(
        model=model,
        system_prompt=spec["system_prompt"],
        tools=[*ALL_AGENT_TOOLS, *spec["tools"]],
        middleware=[
            FilesystemMiddleware(
                backend=backend,
                max_execute_timeout=DATA_EXPERTISE_MAX_EXECUTE_TIMEOUT_SECONDS,
            ),
            HumanInTheLoopMiddleware(interrupt_on=interrupt_on),
            PatchToolCallsMiddleware(),
        ],
        store=store,
        checkpointer=checkpointer,
        name=spec["name"],
    )
    return CompiledSubAgent(
        name=spec["name"],
        description=spec["description"],
        runnable=runnable,
    )


def _compile_team_subagent(
    *,
    model: BaseChatModel,
    backend: DataExecutionBackend,
    worker_subagents: list[CompiledSubAgent],
    store: BaseStore | None,
    checkpointer: BaseCheckpointSaver | bool | None,
) -> CompiledSubAgent:
    interrupt_on = {
        tool_name: {
            "allowed_decisions": ["approve", "edit", "reject"],
            "description": DATA_EXPERTISE_APPROVAL_DESCRIPTION,
        }
        for tool_name in DATA_EXPERTISE_HITL_TOOLS
    }

    runnable = create_agent(
        model=model,
        system_prompt=DATA_EXPERTISE_SYSTEM_PROMPT,
        tools=ALL_AGENT_TOOLS,
        middleware=[
            FilesystemMiddleware(
                backend=backend,
                max_execute_timeout=DATA_EXPERTISE_MAX_EXECUTE_TIMEOUT_SECONDS,
            ),
            SubAgentMiddleware(
                backend=backend,
                subagents=worker_subagents,
                task_description=ROUND_TABLE_TASK_DESCRIPTION,
            ),
            HumanInTheLoopMiddleware(interrupt_on=interrupt_on),
            PatchToolCallsMiddleware(),
        ],
        store=store,
        checkpointer=checkpointer,
        name="data_expertise",
    )
    return CompiledSubAgent(
        name="data_expertise",
        description=(
            "Coordinates a live data expertise round-table between data analyst, "
            "business analyst, and data scientist workers until they reach consensus."
        ),
        runnable=runnable,
    )
