import os
from pathlib import Path

from deepagents.backends import CompositeBackend
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.middleware.filesystem import FilesystemMiddleware
from deepagents.middleware.patch_tool_calls import PatchToolCallsMiddleware
from deepagents.middleware.skills import SkillsMiddleware
from deepagents.middleware.subagents import SubAgentMiddleware
from langchain.agents import create_agent
from langchain.agents.middleware import (
    HumanInTheLoopMiddleware,
    SummarizationMiddleware,
)
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from minial_agent.agents.core.system_prompt import CORE_AGENT_SYSTEM_PROMPT
from minial_agent.agents.domain.office_file_agent import build_office_file_subagent
from minial_agent.common.llm import llm_client
from minial_agent.integrations.upload import ensure_upload_workspace

WORKSPACE_SKILL_SOURCE = ("/.agents/skills", "Workspace")

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


class AgentBuilder:
    def __init__(
        self,
    ) -> None:
        pass

    def get_agent(self, user_id: str, uuid: str):
        _store = InMemoryStore()
        _checkpointer = InMemorySaver()
        model = llm_client()

        # set workspace
        workspace = self._get_workspace(user_id=user_id, uuid=uuid)

        # build backend
        files_backend = FilesystemBackend(
            root_dir=workspace.files_dir,
            virtual_mode=True,
            max_file_size_mb=1024,
        )
        skills_backend = FilesystemBackend(
            root_dir=workspace.agents_dir,
            virtual_mode=True,
            max_file_size_mb=1024,
        )
        core_backend = CompositeBackend(
            default=files_backend,
            routes={"/.agents/": skills_backend},
        )

        #####################################
        ############# SUBAGENTS #############
        #####################################

        office_subagent = build_office_file_subagent(
            model=model,
            backend=files_backend,
            store=_store,
            checkpointer=_checkpointer,
        )

        #####################################
        ############# MIDDLEWARE ############
        #####################################

        middlewares = [
            FilesystemMiddleware(
                backend=core_backend,
            ),
            SkillsMiddleware(
                backend=core_backend,
                sources=[WORKSPACE_SKILL_SOURCE],
            ),
            SubAgentMiddleware(
                backend=files_backend,
                subagents=[office_subagent],
            ),
            SummarizationMiddleware(
                model=llm_client(),
                trigger=(
                    "tokens",
                    int(os.getenv("LLM_SUMMARY_TRIGGER_TOKEN_SIZE", 4096)),
                ),
                keep=(
                    "messages",
                    int(os.getenv("LLM_SUMMARY_KEEP_MESSAGES", "20")),
                ),
            ),
            HumanInTheLoopMiddleware(interrupt_on=FILESYSTEM_HITL_POLICY),
            PatchToolCallsMiddleware(),
        ]

        return create_agent(
            model=model,
            system_prompt=CORE_AGENT_SYSTEM_PROMPT,
            middleware=middlewares,
            store=_store,
            checkpointer=_checkpointer,
        )

    def _get_workspace_root(self, user_id: str, uuid: str) -> str:
        return str(self._get_workspace(user_id=user_id, uuid=uuid).files_dir)

    def _get_workspace(self, user_id: str, uuid: str):
        self._validate_path_part(user_id)
        self._validate_path_part(uuid)

        base_dir = Path(os.getenv("AGENT_RUNTIME_ROOT_DIR", "./tmpWorkspace"))
        workspace_root = base_dir / user_id
        return ensure_upload_workspace(workspace_root)

    def _validate_path_part(self, value: str) -> None:
        if not value or value in {".", ".."} or Path(value).name != value:
            raise ValueError(f"Invalid workspace path value: {value}")
