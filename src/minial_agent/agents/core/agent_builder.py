import os
from pathlib import Path

import httpx
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.middleware.filesystem import FilesystemMiddleware
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain.agents.middleware import LLMToolSelectorMiddleware
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from pydantic import SecretStr

from minial_agent.integrations.upload import ensure_upload_workspace

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
                ),
                SummarizationMiddleware(
                    model=self._get_llm(),
                    trigger=(
                        "tokens", int(os.getenv("LLM_SUMMARY_TRIGGER_TOKEN_SIZE", 4096))
                    ),
                    keep=(
                        "messages", int(os.getenv("LLM_SUMMARY_KEEP_MESSAGES", "20"))
                    ),
                ),
                LLMToolSelectorMiddleware(
                    model=self._get_llm(),
                    max_tools=5,
                    # always_include=["search"],
                ),
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

    def _get_llm(self):
        max_tokens = os.getenv("LLM_MAX_TOKENS")
        http_verify = self._get_http_verify()
        http_client_config = (
            {}
            if http_verify is True
            else {
                "http_client": httpx.Client(verify=http_verify),
                "http_async_client": httpx.AsyncClient(verify=http_verify),
            }
        )

        return ChatOpenAI(
            model=os.getenv("LLM_MODEL_NAME", ""),
            base_url=os.getenv("LLM_BASE_URL", ""),
            api_key=SecretStr(os.getenv("LLM_API_KEY", "")),
            max_tokens=int(max_tokens) if max_tokens else None,
            stream_usage=True,
            extra_body={
                "enable_thinking": True
            },
            **http_client_config,
        )

    def _get_http_verify(self) -> bool | str:
        tls_verify = os.getenv("LLM_TLS_VERIFY", "true").lower()
        if tls_verify in {"0", "false", "no", "off"}:
            return False

        ca_bundle_path = os.getenv("LLM_CA_BUNDLE_PATH")
        if ca_bundle_path:
            return ca_bundle_path

        return True
