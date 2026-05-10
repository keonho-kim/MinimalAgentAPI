from langgraph.graph import END, START, StateGraph

from minial_agent.integrations.upload.models import UploadWorkspace

from minial_agent.agents.tools.read_documents.pdf.nodes import (
    build_pdf_answer_node,
    resolve_pdf_artifact_node,
    scan_pdf_pages_node,
)
from minial_agent.agents.tools.read_documents.pdf.state import PdfReadState
from minial_agent.agents.utils.scan import EvidenceJudge, PageScanner


def build_pdf_read_workflow(
    workspace: UploadWorkspace,
    *,
    page_scanner: PageScanner | None = None,
    evidence_judge: EvidenceJudge | None = None,
):
    graph = StateGraph(PdfReadState)
    graph.add_node(
        "resolve_pdf_artifact",
        lambda state: resolve_pdf_artifact_node(state, workspace=workspace),
    )
    graph.add_node(
        "scan_pdf_pages",
        lambda state: scan_pdf_pages_node(
            state,
            page_scanner=page_scanner,
            evidence_judge=evidence_judge,
        ),
    )
    graph.add_node("build_pdf_answer", build_pdf_answer_node)
    graph.add_edge(START, "resolve_pdf_artifact")
    graph.add_edge("resolve_pdf_artifact", "scan_pdf_pages")
    graph.add_edge("scan_pdf_pages", "build_pdf_answer")
    graph.add_edge("build_pdf_answer", END)
    return graph.compile()
