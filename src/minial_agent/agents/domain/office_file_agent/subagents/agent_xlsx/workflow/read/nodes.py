from minial_agent.common.utils.file_registry import resolve_artifact
from minial_agent.integrations.upload.models import UploadWorkspace
from minial_agent.integrations.upload.resolver import ResolvedUploadArtifact

from minial_agent.agents.domain.office_file_agent.subagents.utils.scan import PageScanner, build_page_answer, scan_artifact_pages
from minial_agent.agents.domain.office_file_agent.subagents.agent_xlsx.utils.sheets import (
    SheetMapper,
    find_sheet,
    load_sheet_summary,
    map_relevant_sheets as map_relevant_sheet_summaries,
    public_sheet_entries,
    public_sheet_summary,
    relevant_sheet_pages,
)
from minial_agent.agents.domain.office_file_agent.subagents.agent_xlsx.workflow.read.prompts import PAGE_SCAN_PROMPT, SHEET_SCAN_PROMPT


def resolve_xlsx_artifact(
    workspace: UploadWorkspace,
    file_ref: str,
) -> ResolvedUploadArtifact:
    return resolve_artifact(
        workspace=workspace,
        file_ref=file_ref,
        expected_file_type="xlsx",
    )


def inspect_workbook(artifact: ResolvedUploadArtifact) -> dict:
    workbook_index = artifact.workbook_index or {}
    sheets = workbook_index.get("sheets", [])
    return {
        "file_id": artifact.file_id,
        "filename": artifact.visible_name,
        "sheet_count": workbook_index.get("sheet_count", 0),
        "sheets": public_sheet_entries(sheets if isinstance(sheets, list) else []),
    }


def inspect_sheet(artifact: ResolvedUploadArtifact, sheet_name: str) -> dict:
    sheet = find_sheet(artifact, sheet_name)
    return public_sheet_summary(artifact, load_sheet_summary(sheet))


def map_relevant_sheets(
    artifact: ResolvedUploadArtifact,
    *,
    instruction: str,
    sheet_mapper: SheetMapper | None = None,
) -> list[dict]:
    return map_relevant_sheet_summaries(
        artifact=artifact,
        instruction=instruction,
        prompt=SHEET_SCAN_PROMPT,
        sheet_mapper=sheet_mapper,
    )


def answer_xlsx(
    artifact: ResolvedUploadArtifact,
    *,
    question: str,
    sheet_mapper: SheetMapper | None = None,
    page_scanner: PageScanner | None = None,
) -> dict:
    relevant_sheets = map_relevant_sheets(
        artifact,
        instruction=question,
        sheet_mapper=sheet_mapper,
    )
    relevant_pages, scanned_pages = scan_artifact_pages(
        artifact=artifact,
        question=question,
        prompt=PAGE_SCAN_PROMPT,
        pages=relevant_sheet_pages(artifact, relevant_sheets),
        page_scanner=page_scanner,
    )
    result = build_page_answer(
        relevant_pages=relevant_pages,
        scanned_pages=scanned_pages,
    )
    result["relevant_sheets"] = relevant_sheets
    result["relevant_sheet_count"] = len(relevant_sheets)
    return result

