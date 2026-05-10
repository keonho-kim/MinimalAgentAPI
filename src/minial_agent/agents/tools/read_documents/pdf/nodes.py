from minial_agent.common.utils.file_registry import resolve_artifact
from minial_agent.integrations.upload.models import UploadWorkspace
from minial_agent.integrations.upload.resolver import ResolvedUploadArtifact

from minial_agent.agents.tools.read_documents.pdf.state import PdfReadState
from minial_agent.agents.utils.activity import emit_read_step
from minial_agent.agents.utils.scan import (
    EvidenceJudge,
    PageScanner,
    build_evidence_result,
    scan_artifact_pages,
)
from minial_agent.agents.tools.read_documents.pdf.prompts import PAGE_SCAN_PROMPT


def resolve_pdf_artifact(
    workspace: UploadWorkspace,
    file_ref: str,
) -> ResolvedUploadArtifact:
    return resolve_artifact(
        workspace=workspace,
        file_ref=file_ref,
        expected_file_type="pdf",
    )


def scan_pdf_pages(
    artifact: ResolvedUploadArtifact,
    *,
    question: str,
    page_scanner: PageScanner | None = None,
    evidence_judge: EvidenceJudge | None = None,
    full_scan: bool = False,
) -> tuple[dict[str, str], int, bool]:
    return scan_artifact_pages(
        artifact=artifact,
        question=question,
        prompt=PAGE_SCAN_PROMPT,
        page_scanner=page_scanner,
        evidence_judge=evidence_judge,
        full_scan=full_scan,
    )


def resolve_pdf_artifact_node(
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


def scan_pdf_pages_node(
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
        details={
            "path": state["artifact"].visible_name,
            "description": f"{page_count} pages",
        },
    )
    evidence, scanned_pages, is_sufficient = scan_pdf_pages(
        state["artifact"],
        question=state.get("question", ""),
        page_scanner=page_scanner,
        evidence_judge=evidence_judge,
        full_scan=bool(state.get("full_scan", False)),
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


def build_pdf_answer_node(state: PdfReadState) -> PdfReadState:
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
    return {"result": result}
