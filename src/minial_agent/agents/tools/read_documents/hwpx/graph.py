from langgraph.graph import END, START, StateGraph

from minial_agent.integrations.upload.models import UploadWorkspace

from minial_agent.agents.tools.read_documents.hwpx.nodes import (
    build_hwpx_answer_node,
    resolve_hwpx_artifact_node,
    scan_hwpx_pages_node,
)
from minial_agent.agents.tools.read_documents.hwpx.state import HwpxReadState
from minial_agent.agents.utils.scan import EvidenceJudge, PageScanner


def build_hwpx_read_workflow(
    workspace: UploadWorkspace,
    *,
    page_scanner: PageScanner | None = None,
    evidence_judge: EvidenceJudge | None = None,
):
    graph = StateGraph(HwpxReadState)
    graph.add_node(
        "resolve_hwpx_artifact",
        lambda state: resolve_hwpx_artifact_node(state, workspace=workspace),
    )
    graph.add_node(
        "scan_hwpx_pages",
        lambda state: scan_hwpx_pages_node(
            state,
            page_scanner=page_scanner,
            evidence_judge=evidence_judge,
        ),
    )
    graph.add_node("build_hwpx_answer", build_hwpx_answer_node)
    graph.add_edge(START, "resolve_hwpx_artifact")
    graph.add_edge("resolve_hwpx_artifact", "scan_hwpx_pages")
    graph.add_edge("scan_hwpx_pages", "build_hwpx_answer")
    graph.add_edge("build_hwpx_answer", END)
    return graph.compile()
