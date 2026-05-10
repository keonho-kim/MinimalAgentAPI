from langchain_core.tools import tool
from langgraph.prebuilt.tool_node import ToolRuntime

from minial_agent.agents.domain.office_file_editor.subagents.editor_xlsx.tool_utils import json_result
from minial_agent.agents.utils.runtime import sanitize_tool_error, workspace_from_tool_runtime
from minial_agent.integrations.xlsx.sessions import XlsxSessionStore


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
        return json_result(
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
        return json_result(session.dataframe_profile(dataframe_name))
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
        return json_result(
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
        return json_result(
            session.transform(
                input_dataframe=input_dataframe,
                output_dataframe=output_dataframe,
                code=code,
                explanation=explanation,
            )
        )
    except Exception as exc:
        return sanitize_tool_error(exc)
