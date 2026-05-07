import json
from typing import Any

from langchain_core.tools import tool
from langgraph.prebuilt.tool_node import ToolRuntime

from minial_agent.common.utils import file_registry
from minial_agent.integrations.xlsx.exports import (
    commit_workbook,
    export_dataframe,
    export_dataframe_csv,
    export_detected_table_csv,
    export_range,
)
from minial_agent.integrations.xlsx.sessions import XlsxSessionStore

from minial_agent.agents.utils.runtime import sanitize_tool_error, workspace_from_tool_runtime


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
        return _json(
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
        return _json({"session_id": session_id, "workbook": session.inspect()})
    except Exception as exc:
        return sanitize_tool_error(exc)


@tool
def load_xlsx_range(
    session_id: str,
    sheet: str,
    range: str,
    dataframe_name: str,
    runtime: ToolRuntime,
    header: bool = True,
) -> str:
    """Load an XLSX cell range into a named dataframe inside the session."""
    try:
        session = XlsxSessionStore(workspace_from_tool_runtime(runtime)).load(session_id)
        return _json(
            session.load_range(
                sheet=sheet,
                range_ref=range,
                dataframe_name=dataframe_name,
                header=header,
            )
        )
    except Exception as exc:
        return sanitize_tool_error(exc)


@tool
def profile_xlsx_dataframe(session_id: str, dataframe_name: str, runtime: ToolRuntime) -> str:
    """Return dataframe shape, columns, dtypes, null counts, and value statistics."""
    try:
        session = XlsxSessionStore(workspace_from_tool_runtime(runtime)).load(session_id)
        return _json(session.dataframe_profile(dataframe_name))
    except Exception as exc:
        return sanitize_tool_error(exc)


@tool
def preview_xlsx_dataframe(
    session_id: str,
    dataframe_name: str,
    runtime: ToolRuntime,
    max_rows: int = 20,
) -> str:
    """Return the first rows of a dataframe stored in an XLSX session."""
    try:
        session = XlsxSessionStore(workspace_from_tool_runtime(runtime)).load(session_id)
        return _json(
            {
                "session_id": session_id,
                "dataframe": dataframe_name,
                "rows": session.dataframe_preview(dataframe_name, max_rows=max_rows),
            }
        )
    except Exception as exc:
        return sanitize_tool_error(exc)


@tool
def transform_xlsx_dataframe(
    session_id: str,
    input_dataframe: str,
    output_dataframe: str,
    code: str,
    explanation: str,
    runtime: ToolRuntime,
) -> str:
    """Run a restricted pandas transform(df) function on a session dataframe."""
    try:
        session = XlsxSessionStore(workspace_from_tool_runtime(runtime)).load(session_id)
        return _json(
            session.transform(
                input_dataframe=input_dataframe,
                output_dataframe=output_dataframe,
                code=code,
                explanation=explanation,
            )
        )
    except Exception as exc:
        return sanitize_tool_error(exc)


@tool
def write_xlsx_dataframe(
    session_id: str,
    dataframe_name: str,
    sheet: str,
    start_cell: str,
    runtime: ToolRuntime,
    include_header: bool = True,
) -> str:
    """Write a session dataframe into the working XLSX workbook."""
    try:
        session = XlsxSessionStore(workspace_from_tool_runtime(runtime)).load(session_id)
        return _json(
            {
                "session_id": session_id,
                "result": session.write_dataframe(
                    dataframe_name=dataframe_name,
                    sheet=sheet,
                    start_cell=start_cell,
                    include_header=include_header,
                ),
            }
        )
    except Exception as exc:
        return sanitize_tool_error(exc)


@tool
def write_xlsx_values(
    session_id: str,
    sheet: str,
    start_cell: str,
    values: list[list[Any]],
    runtime: ToolRuntime,
) -> str:
    """Write a small matrix of values into the working XLSX workbook."""
    try:
        session = XlsxSessionStore(workspace_from_tool_runtime(runtime)).load(session_id)
        return _json(
            {
                "session_id": session_id,
                "result": session.write_values(sheet=sheet, start_cell=start_cell, values=values),
            }
        )
    except Exception as exc:
        return sanitize_tool_error(exc)


@tool
def add_xlsx_formula(
    session_id: str,
    sheet: str,
    cell: str,
    formula: str,
    runtime: ToolRuntime,
    fill_range: str | None = None,
) -> str:
    """Add a formula to one cell or fill a formula pattern across a range."""
    try:
        session = XlsxSessionStore(workspace_from_tool_runtime(runtime)).load(session_id)
        return _json(
            {
                "session_id": session_id,
                "result": session.add_formula(
                    sheet=sheet,
                    cell=cell,
                    formula=formula,
                    fill_range=fill_range,
                ),
            }
        )
    except Exception as exc:
        return sanitize_tool_error(exc)


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
        return _json(
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
        return _json(
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
        return _json(
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
        return _json(
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
        return _json(
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


@tool
def discard_xlsx_session(session_id: str, runtime: ToolRuntime) -> str:
    """Discard a temporary XLSX session and its internal working files."""
    try:
        session = XlsxSessionStore(workspace_from_tool_runtime(runtime)).load(session_id)
        return _json(session.discard())
    except Exception as exc:
        return sanitize_tool_error(exc)


XLSX_SESSION_TOOLS = [
    start_xlsx_session,
    inspect_xlsx_session,
    load_xlsx_range,
    profile_xlsx_dataframe,
    preview_xlsx_dataframe,
    transform_xlsx_dataframe,
    write_xlsx_dataframe,
    write_xlsx_values,
    add_xlsx_formula,
    export_xlsx_range,
    export_xlsx_dataframe,
    export_xlsx_detected_table_csv,
    export_xlsx_dataframe_csv,
    commit_xlsx_session,
    discard_xlsx_session,
]


def _json(value: dict | list) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)
