import os
from textwrap import dedent
from pathlib import Path

from deepagents.backends.filesystem import FilesystemBackend
from deepagents.middleware.subagents import CompiledSubAgent
from deepagents.middleware.filesystem import FilesystemMiddleware
from deepagents.middleware.patch_tool_calls import PatchToolCallsMiddleware
from deepagents.middleware.subagents import SubAgentMiddleware
from langchain.agents import create_agent
from langchain.agents.middleware import (
    HumanInTheLoopMiddleware,
    SummarizationMiddleware,
)
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from minial_agent.common.llm import llm_client
from minial_agent.agents.domain.office_file_agent import build_office_file_agent
from minial_agent.integrations.upload import ensure_upload_workspace

from minial_agent.agents.core.system_prompt import CORE_AGENT_SYSTEM_PROMPT


class AgentBuilder:
    def __init__(
        self,
    ) -> None:
        pass

    def get_agent(self, user_id: str, uuid: str):
        _store = InMemoryStore()
        _checkpointer = InMemorySaver()
        _root_dir = self._get_workspace_root(user_id=user_id, uuid=uuid)
        backend = FilesystemBackend(
            root_dir=_root_dir,
            virtual_mode=True,
            max_file_size_mb=1024,
        )

        model = llm_client()
        
        office_agent = build_office_file_agent(
            model=model,
            backend=backend,
            store=_store,
            checkpointer=_checkpointer,
        )
        
        office_subagent = CompiledSubAgent(
            name="office_file_agent",
            description=dedent("""
            Routes office file requests to HWPX, DOCX, PPTX, XLSX, and PDF worker agents.
            """.strip()),
            runnable=office_agent,
        )

        return create_agent(
            model=model,
            system_prompt=CORE_AGENT_SYSTEM_PROMPT,
            middleware=[
                FilesystemMiddleware(
                    backend=backend,
                ),
                SubAgentMiddleware(
                    backend=backend,
                    subagents=[office_subagent],
                ),
                SummarizationMiddleware(
                    model=llm_client(),
                    trigger=(
                        "tokens", int(os.getenv("LLM_SUMMARY_TRIGGER_TOKEN_SIZE", 4096)),
                    ),
                    keep=(
                        "messages", int(os.getenv("LLM_SUMMARY_KEEP_MESSAGES", "20")),
                    ),
                ),
                HumanInTheLoopMiddleware(
                    interrupt_on={
                        "write_file": {
                            "allowed_decisions": ["approve", "edit", "reject"],
                            "description": (
                                "A file write requires approval before it changes "
                                "the workspace."
                            ),
                        },
                        "edit_file": {
                            "allowed_decisions": ["approve", "edit", "reject"],
                            "description": (
                                "A file edit requires approval before it changes "
                                "the workspace."
                            ),
                        },
                    },
                ),
                PatchToolCallsMiddleware(),
            ],
            store=_store,
            checkpointer=_checkpointer,
        )

    def _get_workspace_root(self, user_id: str, uuid: str) -> str:
        self._validate_path_part(user_id)
        self._validate_path_part(uuid)

        base_dir = Path(os.getenv("AGENT_RUNTIME_ROOT_DIR", "./tmpWorkspace"))
        workspace_root = base_dir / user_id
        workspace = ensure_upload_workspace(workspace_root)
        return str(workspace.files_dir)

    def _validate_path_part(self, value: str) -> None:
        if not value or value in {".", ".."} or Path(value).name != value:
            raise ValueError(f"Invalid workspace path value: {value}")
