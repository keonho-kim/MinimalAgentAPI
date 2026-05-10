import json

from langchain_core.tools import tool
from langgraph.prebuilt.tool_node import ToolRuntime

from minial_agent.agents.utils.runtime import (
    sanitize_tool_error,
    workspace_from_tool_runtime,
)
from minial_agent.common.utils import file_registry
from minial_agent.integrations.pptx.ingest import load_or_ingest_pptx_deck


@tool
def inspect_pptx_deck(file_path: str, runtime: ToolRuntime) -> str:
    """Inspect PPTX slides, titles, text blocks, notes, and shape bounds."""
    try:
        workspace = workspace_from_tool_runtime(runtime)
        artifact = file_registry.resolve_artifact(
            workspace=workspace,
            file_ref=file_path,
            expected_file_type="pptx",
        )
        return json.dumps(
            {
                "source_file": {
                    "file_id": artifact.file_id,
                    "filename": artifact.visible_name,
                },
                "deck": load_or_ingest_pptx_deck(
                    cache_dir=workspace.cache_dir,
                    source_path=artifact.source_path,
                ).model_dump(mode="json"),
            },
            ensure_ascii=False,
        )
    except Exception as exc:
        return sanitize_tool_error(exc)
