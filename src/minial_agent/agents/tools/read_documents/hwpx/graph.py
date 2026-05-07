from langgraph.graph import END, START, StateGraph

from minial_agent.integrations.upload.models import UploadWorkspace

from minial_agent.agents.tools.read_documents.hwpx.nodes import resolve_hwpx_artifact, scan_hwpx_pages
from minial_agent.agents.tools.read_documents.hwpx.state import HwpxReadState
from minial_agent.agents.utils.activity import emit_read_step
from minial_agent.agents.utils.scan import EvidenceJudge, PageScanner, build_evidence_result


def build_hwpx_read_workflow(
    workspace: UploadWorkspace,
    *,
    page_scanner: PageScanner | None = None,
    evidence_judge: EvidenceJudge | None = None,
):
    graph = StateGraph(HwpxReadState)
    graph.add_node(
        "resolve_hwpx_artifact",
        lambda state: _resolve_hwpx_artifact(state, workspace=workspace),
    )
    graph.add_node(
        "scan_hwpx_pages",
        lambda state: _scan_hwpx_pages(
            state,
            page_scanner=page_scanner,
            evidence_judge=evidence_judge,
        ),
    )
    graph.add_node("build_hwpx_answer", _build_hwpx_answer)
    graph.add_edge(START, "resolve_hwpx_artifact")
    graph.add_edge("resolve_hwpx_artifact", "scan_hwpx_pages")
    graph.add_edge("scan_hwpx_pages", "build_hwpx_answer")
    graph.add_edge("build_hwpx_answer", END)
    return graph.compile()


def _resolve_hwpx_artifact(
    state: HwpxReadState,
    *,
    workspace: UploadWorkspace,
) -> HwpxReadState:
    emit_read_step(
        file_type="hwpx",
        step="resolve",
        message="HWPX 파일을 확인합니다.",
        details={"path": state["file_ref"]},
    )
    artifact = resolve_hwpx_artifact(workspace, state["file_ref"])
    emit_read_step(
        file_type="hwpx",
        step="resolve",
        message="HWPX 파일 확인을 완료했습니다.",
        status="completed",
        details={"path": artifact.visible_name},
    )
    return {"artifact": artifact}


def _scan_hwpx_pages(
    state: HwpxReadState,
    *,
    page_scanner: PageScanner | None,
    evidence_judge: EvidenceJudge | None,
) -> HwpxReadState:
    pages = state["artifact"].manifest.get("pages", [])
    page_count = len(pages) if isinstance(pages, list) else 0
    emit_read_step(
        file_type="hwpx",
        step="scan",
        message=f"HWPX 페이지 {page_count}개를 스캔합니다.",
        details={
            "path": state["artifact"].visible_name,
            "description": f"{page_count} pages",
        },
    )
    evidence, scanned_pages, is_sufficient = scan_hwpx_pages(
        state["artifact"],
        question=state.get("question", ""),
        page_scanner=page_scanner,
        evidence_judge=evidence_judge,
    )
    emit_read_step(
        file_type="hwpx",
        step="scan",
        message=f"HWPX 페이지 {scanned_pages}개 스캔을 완료했습니다.",
        status="completed",
        details={
            "path": state["artifact"].visible_name,
            "scannedPages": scanned_pages,
            "evidence": evidence,
            "evidencePageCount": len(evidence),
            "isSufficient": is_sufficient,
        },
    )
    return {
        "evidence": evidence,
        "scanned_pages": scanned_pages,
        "is_sufficient": is_sufficient,
    }


def _build_hwpx_answer(state: HwpxReadState) -> HwpxReadState:
    emit_read_step(
        file_type="hwpx",
        step="answer",
        message="HWPX 근거를 정리해 답변을 준비합니다.",
        details={"path": state["artifact"].visible_name},
    )
    evidence = state.get("evidence", {})
    result = build_evidence_result(evidence)
    emit_read_step(
        file_type="hwpx",
        step="answer",
        message="HWPX 답변 근거 정리를 완료했습니다.",
        status="completed",
        details={
            "path": state["artifact"].visible_name,
            "result": f"{len(evidence)} evidence pages",
        },
    )
    return {"result": result}
