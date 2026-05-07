from langgraph.graph import END, START, StateGraph

from minial_agent.integrations.upload.models import UploadWorkspace

from minial_agent.agents.utils.activity import emit_read_step
from minial_agent.agents.utils.scan import EvidenceJudge, PageScanner, build_evidence_result
from minial_agent.agents.tools.read_documents.pdf.nodes import resolve_pdf_artifact, scan_pdf_pages
from minial_agent.agents.tools.read_documents.pdf.state import PdfReadState


def build_pdf_read_workflow(
    workspace: UploadWorkspace,
    *,
    page_scanner: PageScanner | None = None,
    evidence_judge: EvidenceJudge | None = None,
):
    graph = StateGraph(PdfReadState)
    graph.add_node(
        "resolve_pdf_artifact",
        lambda state: _resolve_pdf_artifact(state, workspace=workspace),
    )
    graph.add_node(
        "scan_pdf_pages",
        lambda state: _scan_pdf_pages(
            state,
            page_scanner=page_scanner,
            evidence_judge=evidence_judge,
        ),
    )
    graph.add_node("build_pdf_answer", _build_pdf_answer)
    graph.add_edge(START, "resolve_pdf_artifact")
    graph.add_edge("resolve_pdf_artifact", "scan_pdf_pages")
    graph.add_edge("scan_pdf_pages", "build_pdf_answer")
    graph.add_edge("build_pdf_answer", END)
    return graph.compile()


def _resolve_pdf_artifact(
    state: PdfReadState,
    *,
    workspace: UploadWorkspace,
) -> PdfReadState:
    emit_read_step(
        file_type="pdf",
        step="resolve",
        message="PDF 파일을 확인합니다.",
        details={"path": state["file_ref"]},
    )
    artifact = resolve_pdf_artifact(workspace, state["file_ref"])
    emit_read_step(
        file_type="pdf",
        step="resolve",
        message="PDF 파일 확인을 완료했습니다.",
        status="completed",
        details={"path": artifact.visible_name},
    )
    return {"artifact": artifact}


def _scan_pdf_pages(
    state: PdfReadState,
    *,
    page_scanner: PageScanner | None,
    evidence_judge: EvidenceJudge | None,
) -> PdfReadState:
    pages = state["artifact"].manifest.get("pages", [])
    page_count = len(pages) if isinstance(pages, list) else 0
    emit_read_step(
        file_type="pdf",
        step="scan",
        message=f"PDF 페이지 {page_count}개를 스캔합니다.",
        details={"path": state["artifact"].visible_name, "description": f"{page_count} pages"},
    )
    evidence, scanned_pages, is_sufficient = scan_pdf_pages(
        state["artifact"],
        question=state.get("question", ""),
        page_scanner=page_scanner,
        evidence_judge=evidence_judge,
    )
    emit_read_step(
        file_type="pdf",
        step="scan",
        message=f"PDF 페이지 {scanned_pages}개 스캔을 완료했습니다.",
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


def _build_pdf_answer(state: PdfReadState) -> PdfReadState:
    emit_read_step(
        file_type="pdf",
        step="answer",
        message="PDF 근거를 정리해 답변을 준비합니다.",
        details={"path": state["artifact"].visible_name},
    )
    evidence = state.get("evidence", {})
    result = build_evidence_result(evidence)
    emit_read_step(
        file_type="pdf",
        step="answer",
        message="PDF 답변 근거 정리를 완료했습니다.",
        status="completed",
        details={
            "path": state["artifact"].visible_name,
            "result": f"{len(evidence)} evidence pages",
        },
    )
    return {
        "result": result,
    }
