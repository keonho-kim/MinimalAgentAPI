from minial_agent.common.utils.file_registry import resolve_artifact
from minial_agent.integrations.upload.models import UploadWorkspace
from minial_agent.integrations.upload.resolver import ResolvedUploadArtifact

from minial_agent.agents.utils.scan import EvidenceJudge, PageScanner, scan_artifact_pages
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
) -> tuple[dict[str, str], int, bool]:
    return scan_artifact_pages(
        artifact=artifact,
        question=question,
        prompt=PAGE_SCAN_PROMPT,
        page_scanner=page_scanner,
        evidence_judge=evidence_judge,
    )
