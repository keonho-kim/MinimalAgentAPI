from langchain_core.tools import tool
from langgraph.prebuilt.tool_node import ToolRuntime

from ..utils.runtime import sanitize_tool_error, workspace_from_tool_runtime
from ..utils.workflow import build_office_file_workflow


def _run_xlsx_workflow(
    *,
    file_path: str,
    runtime: ToolRuntime,
    operation: str,
    question: str | None = None,
    instruction: str | None = None,
    sheet_name: str | None = None,
) -> str:
    workflow = build_office_file_workflow(workspace_from_tool_runtime(runtime))
    result = workflow.invoke(
        {
            "file_ref": file_path,
            "file_type": "xlsx",
            "operation": operation,
            "question": question or "",
            "instruction": instruction or "",
            "sheet_name": sheet_name or "",
        }
    )
    return result["result"]


@tool
def answer_xlsx_question(file_path: str, question: str, runtime: ToolRuntime) -> str:
    """Answer a question about an XLSX workbook."""
    try:
        return _run_xlsx_workflow(
            file_path=file_path,
            runtime=runtime,
            operation="answer",
            question=question,
        )
    except Exception as exc:
        return sanitize_tool_error(exc)


@tool
def edit_xlsx(file_path: str, instruction: str, runtime: ToolRuntime) -> str:
    """Edit an XLSX workbook according to the instruction."""
    try:
        return _run_xlsx_workflow(
            file_path=file_path,
            runtime=runtime,
            operation="edit",
            instruction=instruction,
        )
    except Exception as exc:
        return sanitize_tool_error(exc)


@tool
def inspect_xlsx_workbook(file_path: str, runtime: ToolRuntime) -> str:
    """Inspect workbook-level metadata and sheet names for an XLSX file."""
    try:
        return _run_xlsx_workflow(
            file_path=file_path,
            runtime=runtime,
            operation="inspect_workbook",
        )
    except Exception as exc:
        return sanitize_tool_error(exc)


@tool
def inspect_xlsx_sheet(
    file_path: str,
    sheet_name: str,
    runtime: ToolRuntime,
) -> str:
    """Inspect a single sheet in an XLSX workbook."""
    try:
        return _run_xlsx_workflow(
            file_path=file_path,
            runtime=runtime,
            operation="inspect_sheet",
            sheet_name=sheet_name,
        )
    except Exception as exc:
        return sanitize_tool_error(exc)


@tool
def map_reduce_xlsx_sheets(
    file_path: str,
    instruction: str,
    runtime: ToolRuntime,
) -> str:
    """Run a map-reduce style analysis across sheets in an XLSX workbook."""
    try:
        return _run_xlsx_workflow(
            file_path=file_path,
            runtime=runtime,
            operation="map_reduce_sheets",
            instruction=instruction,
        )
    except Exception as exc:
        return sanitize_tool_error(exc)
