from langchain_core.tools import tool
from langgraph.prebuilt.tool_node import ToolRuntime

from minial_agent.agents.domain.office_file_editor.subagents.editor_pptx.workflow.edit.graph import (
    build_pptx_edit_workflow,
)
from minial_agent.agents.utils.runtime import (
    sanitize_tool_error,
    workspace_from_tool_runtime,
)


@tool
def edit_pptx(file_path: str, instruction: str, runtime: ToolRuntime) -> str:
    """Edit a PPTX file."""
    try:
        workflow = build_pptx_edit_workflow(workspace_from_tool_runtime(runtime))
        result = workflow.invoke({"file_ref": file_path, "instruction": instruction})
        return result["result"]
    except Exception as exc:
        return sanitize_tool_error(exc)

__all__ = ["build_pptx_edit_workflow", "edit_pptx"]
