from langchain_core.tools import tool
from langgraph.prebuilt.tool_node import ToolRuntime

from minial_agent.agents.tools.read_documents.docx import (
    build_docx_read_workflow,
)
from minial_agent.agents.tools.read_documents.hwpx import (
    build_hwpx_read_workflow,
)
from minial_agent.agents.tools.read_documents.pdf import (
    build_pdf_read_workflow,
)
from minial_agent.agents.tools.read_documents.pptx import (
    build_pptx_read_workflow,
)
from minial_agent.agents.tools.read_documents.xlsx import (
    build_xlsx_read_workflow,
)
from minial_agent.agents.utils.runtime import (
    sanitize_tool_error,
    workspace_from_tool_runtime,
)


@tool
def read_pdf_file(
    file_path: str,
    question: str,
    runtime: ToolRuntime,
    full_scan: int = 0,
) -> str:
    """Read a PDF file. Use full_scan=1 for full-document summaries or reviews."""
    try:
        scan_all_pages = _full_scan_enabled(full_scan)
        workflow = build_pdf_read_workflow(workspace_from_tool_runtime(runtime))
        result = workflow.invoke(
            {
                "file_ref": file_path,
                "question": question,
                "full_scan": scan_all_pages,
            }
        )
        return result["result"]
    except Exception as exc:
        return sanitize_tool_error(exc)


@tool
def read_docx_file(
    file_path: str,
    question: str,
    runtime: ToolRuntime,
    full_scan: int = 0,
) -> str:
    """Read a DOCX file. Use full_scan=1 for full-document summaries or reviews."""
    try:
        scan_all_pages = _full_scan_enabled(full_scan)
        workflow = build_docx_read_workflow(workspace_from_tool_runtime(runtime))
        result = workflow.invoke(
            {
                "file_ref": file_path,
                "question": question,
                "full_scan": scan_all_pages,
            }
        )
        return result["result"]
    except Exception as exc:
        return sanitize_tool_error(exc)


@tool
def read_hwpx_file(
    file_path: str,
    question: str,
    runtime: ToolRuntime,
    full_scan: int = 0,
) -> str:
    """Read an HWPX file. Use full_scan=1 for full-document summaries or reviews."""
    try:
        scan_all_pages = _full_scan_enabled(full_scan)
        workflow = build_hwpx_read_workflow(workspace_from_tool_runtime(runtime))
        result = workflow.invoke(
            {
                "file_ref": file_path,
                "question": question,
                "full_scan": scan_all_pages,
            }
        )
        return result["result"]
    except Exception as exc:
        return sanitize_tool_error(exc)


@tool
def read_pptx_file(
    file_path: str,
    question: str,
    runtime: ToolRuntime,
    full_scan: int = 0,
) -> str:
    """Read a PPTX file. Use full_scan=1 for full-document summaries or reviews."""
    try:
        scan_all_pages = _full_scan_enabled(full_scan)
        workflow = build_pptx_read_workflow(workspace_from_tool_runtime(runtime))
        result = workflow.invoke(
            {
                "file_ref": file_path,
                "question": question,
                "full_scan": scan_all_pages,
            }
        )
        return result["result"]
    except Exception as exc:
        return sanitize_tool_error(exc)


@tool
def read_xlsx_file(file_path: str, question: str, runtime: ToolRuntime) -> str:
    """Read XLSX workbook structure, sheet metadata, and explicit cell ranges."""
    try:
        workflow = build_xlsx_read_workflow(workspace_from_tool_runtime(runtime))
        result = workflow.invoke(
            {
                "file_ref": file_path,
                "question": question,
            }
        )
        return result["result"]
    except Exception as exc:
        return sanitize_tool_error(exc)


def _full_scan_enabled(full_scan: int) -> bool:
    if isinstance(full_scan, bool) or full_scan not in {0, 1}:
        raise ValueError("full_scan must be 0 or 1.")
    return full_scan == 1


__all__ = ["read_pdf_file", "read_docx_file", "read_hwpx_file", "read_pptx_file", "read_xlsx_file"]
