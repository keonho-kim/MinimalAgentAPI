from minial_agent.common.utils.file_registry import resolve_artifact
from minial_agent.integrations.upload.models import UploadWorkspace
from minial_agent.integrations.upload.resolver import ResolvedUploadArtifact

from minial_agent.agents.utils.scan import PageScanner, build_page_answer, scan_artifact_pages
from minial_agent.agents.tools.read_documents.docx.prompts import PAGE_SCAN_PROMPT


def resolve_docx_artifact(
    workspace: UploadWorkspace,
    file_ref: str,
) -> ResolvedUploadArtifact:
    return resolve_artifact(
        workspace=workspace,
        file_ref=file_ref,
        expected_file_type="docx",
    )


def scan_docx_pages(
    artifact: ResolvedUploadArtifact,
    *,
    question: str,
    page_scanner: PageScanner | None = None,
) -> tuple[list[dict], int]:
    return scan_artifact_pages(
        artifact=artifact,
        question=question,
        prompt=PAGE_SCAN_PROMPT,
        page_scanner=page_scanner,
    )


def build_docx_answer(relevant_pages: list[dict], scanned_pages: int) -> dict:
    return build_page_answer(
        relevant_pages=relevant_pages,
        scanned_pages=scanned_pages,
    )
