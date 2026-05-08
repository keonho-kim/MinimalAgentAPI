from langgraph.graph import END, START, StateGraph

from minial_agent.integrations.upload.models import UploadWorkspace

from minial_agent.agents.tools.read_documents.docx.nodes import (
    build_docx_answer_node,
    resolve_docx_artifact_node,
    scan_docx_pages_node,
)
from minial_agent.agents.tools.read_documents.docx.state import DocxReadState
from minial_agent.agents.utils.scan import EvidenceJudge, PageScanner


def build_docx_read_workflow(
    workspace: UploadWorkspace,
    *,
    page_scanner: PageScanner | None = None,
    evidence_judge: EvidenceJudge | None = None,
):
    graph = StateGraph(DocxReadState)
    graph.add_node(
        "resolve_docx_artifact",
        lambda state: resolve_docx_artifact_node(state, workspace=workspace),
    )
    graph.add_node(
        "scan_docx_pages",
        lambda state: scan_docx_pages_node(
            state,
            page_scanner=page_scanner,
            evidence_judge=evidence_judge,
        ),
    )
    graph.add_node("build_docx_answer", build_docx_answer_node)
    graph.add_edge(START, "resolve_docx_artifact")
    graph.add_edge("resolve_docx_artifact", "scan_docx_pages")
    graph.add_edge("scan_docx_pages", "build_docx_answer")
    graph.add_edge("build_docx_answer", END)
    return graph.compile()
