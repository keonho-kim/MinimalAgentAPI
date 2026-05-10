from langchain_core.tools import tool
from langgraph.prebuilt.tool_node import ToolRuntime

from minial_agent.agents.domain.office_file_editor.subagents.editor_xlsx.tool_utils import json_result
from minial_agent.agents.utils.runtime import sanitize_tool_error, workspace_from_tool_runtime
from minial_agent.integrations.xlsx.exports import (
    commit_workbook,
    export_dataframe,
    export_dataframe_csv,
    export_detected_table_csv,
    export_range,
)
from minial_agent.integrations.xlsx.sessions import XlsxSessionStore


@tool
def export_xlsx_range(
    session_id: str,
    sheet: str,
    range: str,
    output_path: str,
    runtime: ToolRuntime,
) -> str:
    """Export a session workbook range to a new XLSX artifact or user-visible CSV file."""
    try:
        workspace = workspace_from_tool_runtime(runtime)
        session = XlsxSessionStore(workspace).load(session_id)
        return json_result(
            export_range(
                workspace=workspace,
                source_artifact=session.source_artifact(),
                workbook_path=session.working_path,
                sheet=sheet,
                range_ref=range,
                output_path=output_path,
            )
        )
    except Exception as exc:
        return sanitize_tool_error(exc)


@tool
def export_xlsx_dataframe(
    session_id: str,
    dataframe_name: str,
    output_path: str,
    runtime: ToolRuntime,
) -> str:
    """Export a session dataframe to a new XLSX artifact or user-visible CSV file."""
    try:
        workspace = workspace_from_tool_runtime(runtime)
        session = XlsxSessionStore(workspace).load(session_id)
        return json_result(
            export_dataframe(
                workspace=workspace,
                source_artifact=session.source_artifact(),
                dataframe=session.load_dataframe(dataframe_name),
                output_path=output_path,
            )
        )
    except Exception as exc:
        return sanitize_tool_error(exc)


@tool
def export_xlsx_detected_table_csv(
    session_id: str,
    output_filename: str,
    runtime: ToolRuntime,
    sheet: str | None = None,
) -> str:
    """Detect the main data table and export it to a user-visible CSV file."""
    try:
        workspace = workspace_from_tool_runtime(runtime)
        session = XlsxSessionStore(workspace).load(session_id)
        return json_result(
            export_detected_table_csv(
                workspace=workspace,
                workbook_path=session.working_path,
                output_filename=output_filename,
                sheet=sheet,
            )
        )
    except Exception as exc:
        return sanitize_tool_error(exc)


@tool
def export_xlsx_dataframe_csv(
    session_id: str,
    dataframe_name: str,
    output_filename: str,
    runtime: ToolRuntime,
) -> str:
    """Export a session dataframe to a user-visible CSV file, overwriting that filename if it exists."""
    try:
        workspace = workspace_from_tool_runtime(runtime)
        session = XlsxSessionStore(workspace).load(session_id)
        return json_result(
            export_dataframe_csv(
                workspace=workspace,
                dataframe=session.load_dataframe(dataframe_name),
                output_filename=output_filename,
            )
        )
    except Exception as exc:
        return sanitize_tool_error(exc)


@tool
def commit_xlsx_session(
    session_id: str,
    output_path: str,
    summary: str,
    runtime: ToolRuntime,
) -> str:
    """Register the current working XLSX workbook as a new XLSX artifact."""
    try:
        workspace = workspace_from_tool_runtime(runtime)
        session = XlsxSessionStore(workspace).load(session_id)
        return json_result(
            commit_workbook(
                workspace=workspace,
                source_artifact=session.source_artifact(),
                workbook_path=session.working_path,
                output_path=output_path,
                summary=summary,
                changed_items=session.changed_items(),
            )
        )
    except Exception as exc:
        return sanitize_tool_error(exc)
