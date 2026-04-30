from typing import Any

from deepagents.backends.filesystem import FilesystemBackend
from langchain_core.language_models import BaseChatModel
from langchain.agents import create_agent
from deepagents.middleware.filesystem import FilesystemMiddleware
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.store.base import BaseStore

from .subagents.agent_docx.agent import build_docx_subagent
from .subagents.agent_hwpx.agent import build_hwpx_subagent
from .subagents.agent_pdf.agent import build_pdf_subagent
from .subagents.agent_pptx.agent import build_pptx_subagent
from .subagents.agent_xslx.agent import build_xslx_subagent
from .system_prompt import SYSTEM_PROMPT


def build_office_file_agent(
    *,
    model: BaseChatModel,
    root_dir: str,
    store: BaseStore | None = None,
    checkpointer: BaseCheckpointSaver | bool | None = None,
):
    return create_agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        subagents=[
            build_hwpx_subagent(),
            build_docx_subagent(),
            build_pptx_subagent(),
            build_xslx_subagent(),
            build_pdf_subagent(),
        ],
        middleware=[
            FilesystemMiddleware(
                backend=FilesystemBackend(
                    root_dir=root_dir,
                    virtual_mode=True,
                    max_file_size_mb=1024,
                )
            )
        ],
        backend=FilesystemBackend(
            root_dir=root_dir,
            virtual_mode=True,
            max_file_size_mb=1024,
        ),
        store=store,
        checkpointer=checkpointer,
    )
