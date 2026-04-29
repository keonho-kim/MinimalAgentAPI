import os
from pathlib import Path

from deepagents.backends.filesystem import FilesystemBackend
from deepagents.middleware.filesystem import FilesystemMiddleware
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from pydantic import SecretStr

from .system_prompt import SYSTEM_PROMPT


class AgentBuilder:
    def __init__(
        self,
    ) -> None:
        pass

    def get_agent(self, user_id: str, uuid: str):
        _store = InMemoryStore()
        _checkpointer = InMemorySaver()
        _root_dir = self._get_workspace_root(user_id=user_id, uuid=uuid)

        return create_agent(
            model=self._get_llm(),
            system_prompt=SYSTEM_PROMPT,
            middleware=[
                FilesystemMiddleware(
                    backend=FilesystemBackend(
                        root_dir=_root_dir,
                        virtual_mode=True,
                        max_file_size_mb=1024,
                    )
                )
            ],
            store=_store,
            checkpointer=_checkpointer,
        )

    def _get_workspace_root(self, user_id: str, uuid: str) -> str:
        self._validate_path_part(user_id)
        self._validate_path_part(uuid)

        base_dir = Path(os.getenv("AGENT_RUNTIME_ROOT_DIR", "./tmpWorkspace"))
        workspace_root = base_dir / user_id / uuid
        workspace_root.mkdir(parents=True, exist_ok=True)
        return str(workspace_root)

    def _validate_path_part(self, value: str) -> None:
        if not value or value in {".", ".."} or Path(value).name != value:
            raise ValueError(f"Invalid workspace path value: {value}")

    def _get_llm(self):
        max_tokens = os.getenv("LLM_MAX_TOKENS")

        return ChatOpenAI(
            model=os.getenv("LLM_MODEL_NAME", ""),
            base_url=os.getenv("LLM_BASE_URL", ""),
            api_key=SecretStr(os.getenv("LLM_API_KEY", "")),
            max_tokens=int(max_tokens) if max_tokens else None,
            stream_usage=True,
        )
