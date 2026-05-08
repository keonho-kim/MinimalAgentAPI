from langgraph.graph import END, START, StateGraph

from minial_agent.integrations.upload.models import UploadWorkspace

from minial_agent.agents.tools.read_documents.pptx.nodes import (
    build_pptx_answer_node,
    resolve_pptx_artifact_node,
    scan_pptx_pages_node,
)
from minial_agent.agents.tools.read_documents.pptx.state import PptxReadState
from minial_agent.agents.utils.scan import EvidenceJudge, PageScanner


def build_pptx_read_workflow(
    workspace: UploadWorkspace,
    *,
    page_scanner: PageScanner | None = None,
    evidence_judge: EvidenceJudge | None = None,
):
    graph = StateGraph(PptxReadState)
    graph.add_node(
        "resolve_pptx_artifact",
        lambda state: resolve_pptx_artifact_node(state, workspace=workspace),
    )
    graph.add_node(
        "scan_pptx_pages",
        lambda state: scan_pptx_pages_node(
            state,
            page_scanner=page_scanner,
            evidence_judge=evidence_judge,
        ),
    )
    graph.add_node("build_pptx_answer", build_pptx_answer_node)
    graph.add_edge(START, "resolve_pptx_artifact")
    graph.add_edge("resolve_pptx_artifact", "scan_pptx_pages")
    graph.add_edge("scan_pptx_pages", "build_pptx_answer")
    graph.add_edge("build_pptx_answer", END)
    return graph.compile()
