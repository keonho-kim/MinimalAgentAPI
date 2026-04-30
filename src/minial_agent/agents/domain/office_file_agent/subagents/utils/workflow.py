from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from minial_agent.integrations.upload.models import UploadWorkspace
from minial_agent.integrations.upload.resolver import resolve_upload_artifact

from .runtime import compact_artifact_summary


WorkflowOperation = Literal[
    "answer",
    "edit",
    "inspect_workbook",
    "inspect_sheet",
    "map_reduce_sheets",
]


class OfficeWorkflowState(TypedDict, total=False):
    file_ref: str
    file_type: str
    operation: WorkflowOperation
    question: str
    instruction: str
    sheet_name: str
    artifact: dict[str, Any]
    result: str
    error: str


def build_office_file_workflow(workspace: UploadWorkspace):
    graph = StateGraph(OfficeWorkflowState)

    def resolve_artifact(state: OfficeWorkflowState) -> OfficeWorkflowState:
        artifact = resolve_upload_artifact(
            workspace=workspace,
            file_ref=state["file_ref"],
            expected_file_type=state.get("file_type"),
        )
        return {"artifact": artifact.public_metadata()}

    graph.add_node("resolve_artifact", resolve_artifact)
    graph.add_node("dispatch_placeholder", _dispatch_placeholder)
    graph.add_edge(START, "resolve_artifact")
    graph.add_edge("resolve_artifact", "dispatch_placeholder")
    graph.add_edge("dispatch_placeholder", END)
    return graph.compile()


def _dispatch_placeholder(state: OfficeWorkflowState) -> OfficeWorkflowState:
    artifact = state.get("artifact", {})
    file_type = str(state.get("file_type", "")).upper()
    summary = compact_artifact_summary(artifact)
    operation = state.get("operation")

    if operation == "answer":
        result = (
            f"{file_type} question answering workflow resolved the uploaded file "
            f"({summary}). The VLM scan node is not implemented yet."
        )
    elif operation == "edit":
        result = (
            f"{file_type} edit workflow resolved the uploaded file ({summary}). "
            "The edit execution node is not implemented yet."
        )
    elif operation == "inspect_workbook":
        result = f"XLSX workbook inspection resolved the uploaded file ({summary})."
    elif operation == "inspect_sheet":
        sheet_name = state.get("sheet_name") or "requested sheet"
        result = (
            f"XLSX sheet inspection resolved {sheet_name} in the uploaded file "
            f"({summary})."
        )
    elif operation == "map_reduce_sheets":
        result = (
            f"XLSX sheet map-reduce workflow resolved the uploaded file ({summary}). "
            "The sheet reducer node is not implemented yet."
        )
    else:
        result = f"Office workflow resolved the uploaded file ({summary})."

    return {"result": result}
