from langchain_core.tools import tool
from langgraph.prebuilt.tool_node import ToolRuntime

from minial_agent.agents.domain.office_file_editor.subagents.editor_xlsx.tool_utils import json_result
from minial_agent.agents.utils.runtime import sanitize_tool_error, workspace_from_tool_runtime
from minial_agent.common.utils import file_registry
from minial_agent.integrations.xlsx.sessions import XlsxSessionStore


@tool
def start_xlsx_session(file_path: str, instruction: str, runtime: ToolRuntime) -> str:
    """Start a stateful XLSX work session for analysis, editing, or export."""
    try:
        workspace = workspace_from_tool_runtime(runtime)
        artifact = file_registry.resolve_artifact(
            workspace=workspace,
            file_ref=file_path,
            expected_file_type="xlsx",
        )
        session = XlsxSessionStore(workspace).create(
            artifact=artifact,
            instruction=instruction,
        )
        return json_result(
            {
                "session_id": session.manifest.session_id,
                "source_file": {
                    "file_id": artifact.file_id,
                    "filename": artifact.visible_name,
                },
                "workbook": session.inspect(),
            }
        )
    except Exception as exc:
        return sanitize_tool_error(exc)


@tool
def inspect_xlsx_session(session_id: str, runtime: ToolRuntime) -> str:
    """Inspect sheets, used ranges, tables, formulas, and candidate ranges for an XLSX session."""
    try:
        session = XlsxSessionStore(workspace_from_tool_runtime(runtime)).load(session_id)
        return json_result({"session_id": session_id, "workbook": session.inspect()})
    except Exception as exc:
        return sanitize_tool_error(exc)


@tool
def discard_xlsx_session(session_id: str, runtime: ToolRuntime) -> str:
    """Discard a temporary XLSX session and its internal working files."""
    try:
        session = XlsxSessionStore(workspace_from_tool_runtime(runtime)).load(session_id)
        return json_result(session.discard())
    except Exception as exc:
        return sanitize_tool_error(exc)
