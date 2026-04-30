from langchain_core.tools import tool
from langgraph.prebuilt.tool_node import ToolRuntime

from ..utils.runtime import sanitize_tool_error, workspace_from_tool_runtime
from ..utils.workflow import build_office_file_workflow


@tool
def answer_pdf_question(file_path: str, question: str, runtime: ToolRuntime) -> str:
    """Answer a question about a PDF file."""
    try:
        workflow = build_office_file_workflow(workspace_from_tool_runtime(runtime))
        result = workflow.invoke(
            {
                "file_ref": file_path,
                "file_type": "pdf",
                "operation": "answer",
                "question": question,
            }
        )
        return result["result"]
    except Exception as exc:
        return sanitize_tool_error(exc)
