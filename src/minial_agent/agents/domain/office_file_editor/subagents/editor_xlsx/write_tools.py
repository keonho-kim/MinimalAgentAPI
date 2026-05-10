from typing import Any

from langchain_core.tools import tool
from langgraph.prebuilt.tool_node import ToolRuntime

from minial_agent.agents.domain.office_file_editor.subagents.editor_xlsx.tool_utils import json_result
from minial_agent.agents.utils.runtime import sanitize_tool_error, workspace_from_tool_runtime
from minial_agent.integrations.xlsx.sessions import XlsxSessionStore


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
        return json_result(
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
        return json_result(
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
        return json_result(
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
