from langgraph.graph import END, START, StateGraph

from minial_agent.integrations.upload.models import UploadWorkspace

from minial_agent.agents.tools.read_documents.xlsx.nodes import (
    build_xlsx_answer_node,
    inspect_workbook_node,
    read_question_range_node,
    resolve_xlsx_artifact_node,
)
from minial_agent.agents.tools.read_documents.xlsx.state import XlsxReadState


def build_xlsx_read_workflow(
    workspace: UploadWorkspace,
):
    graph = StateGraph(XlsxReadState)
    graph.add_node(
        "resolve_xlsx_artifact",
        lambda state: resolve_xlsx_artifact_node(state, workspace=workspace),
    )
    graph.add_node(
        "inspect_workbook",
        inspect_workbook_node,
    )
    graph.add_node(
        "read_question_range",
        read_question_range_node,
    )
    graph.add_node("build_xlsx_answer", build_xlsx_answer_node)
    graph.add_edge(START, "resolve_xlsx_artifact")
    graph.add_edge("resolve_xlsx_artifact", "inspect_workbook")
    graph.add_edge("inspect_workbook", "read_question_range")
    graph.add_edge("read_question_range", "build_xlsx_answer")
    graph.add_edge("build_xlsx_answer", END)
    return graph.compile()
