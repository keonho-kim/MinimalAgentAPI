import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

from minial_agent.common.llm import llm_client
from minial_agent.integrations.upload.resolver import ResolvedUploadArtifact

from minial_agent.agents.domain.office_file_agent.subagents.utils.runtime import response_content


SheetMapper = Callable[[dict[str, Any], str], str]


def parse_sheet_scan(raw_scan: str) -> tuple[bool, str, str]:
    normalized = raw_scan.strip()
    if "\n" in normalized or "\r" in normalized:
        raise ValueError("Invalid XLSX sheet scan output. Expected one line.")
    parts = [part.strip() for part in normalized.split(";", 2)]
    if len(parts) != 3 or parts[0] not in {"0", "1"}:
        raise ValueError(
            "Invalid XLSX sheet scan output. Expected `<0/1>; <ranges>; <evidence>`."
        )
    return parts[0] == "1", parts[1], parts[2]


def map_relevant_sheets(
    *,
    artifact: ResolvedUploadArtifact,
    instruction: str,
    prompt: str,
    sheet_mapper: SheetMapper | None = None,
) -> list[dict[str, Any]]:
    summaries = load_workbook_sheet_summaries(artifact)
    if not summaries:
        return []

    relevant_sheets = []
    with ThreadPoolExecutor(max_workers=min(8, len(summaries))) as executor:
        raw_scans = list(
            executor.map(
                lambda summary: (
                    sheet_mapper(summary, instruction)
                    if sheet_mapper
                    else scan_sheet(summary=summary, question=instruction, prompt=prompt)
                ),
                summaries,
            )
        )

    for summary, raw_scan in zip(summaries, raw_scans, strict=True):
        is_relevant, candidate_ranges, evidence = parse_sheet_scan(raw_scan)
        if not is_relevant:
            continue
        public_summary = public_sheet_summary(artifact, summary)
        public_summary["candidate_ranges"] = candidate_ranges
        public_summary["evidence"] = evidence
        relevant_sheets.append(public_summary)
    return relevant_sheets


def scan_sheet(*, summary: dict[str, Any], question: str, prompt: str) -> str:
    response = llm_client(disable_streaming=True).invoke(
        prompt.format(
            question=question,
            sheet=json.dumps(summary, ensure_ascii=False),
        )
    )
    return response_content(response)


def find_sheet(artifact: ResolvedUploadArtifact, sheet_name: str) -> dict[str, Any]:
    workbook_index = artifact.workbook_index or {}
    sheets = workbook_index.get("sheets", [])
    if not isinstance(sheets, list):
        raise ValueError("XLSX workbook index is invalid.")
    for sheet in sheets:
        if sheet.get("sheet_id") == sheet_name or sheet.get("sheet_name") == sheet_name:
            return sheet
    raise ValueError(f"XLSX sheet not found: {sheet_name}")


def load_workbook_sheet_summaries(
    artifact: ResolvedUploadArtifact,
) -> list[dict[str, Any]]:
    workbook_index = artifact.workbook_index or {}
    sheets = workbook_index.get("sheets", [])
    if not isinstance(sheets, list):
        return []
    return [load_sheet_summary(sheet) for sheet in sheets]


def relevant_sheet_pages(
    artifact: ResolvedUploadArtifact,
    relevant_sheets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    relevant_ids = {str(sheet.get("sheet_id", "")) for sheet in relevant_sheets}
    pages = []
    for summary in load_workbook_sheet_summaries(artifact):
        if str(summary.get("sheet_id", "")) not in relevant_ids:
            continue
        sheet_pages = summary.get("pages", [])
        if isinstance(sheet_pages, list):
            pages.extend(sheet_pages)
    return pages


def load_sheet_summary(sheet: dict[str, Any]) -> dict[str, Any]:
    path = Path(str(sheet.get("sheet_summary_path", "")))
    if not path.is_file():
        return dict(sheet)
    return json.loads(path.read_text(encoding="utf-8"))


def public_sheet_entries(sheets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "sheet_id": str(sheet.get("sheet_id", "")),
            "sheet_name": str(sheet.get("sheet_name", "")),
            "visible": bool(sheet.get("visible", False)),
            "used_range": str(sheet.get("used_range", "")),
            "has_formulas": bool(sheet.get("has_formulas", False)),
            "formula_count": int(sheet.get("formula_count", 0)),
        }
        for sheet in sheets
    ]


def public_sheet_summary(
    artifact: ResolvedUploadArtifact,
    sheet: dict[str, Any],
) -> dict[str, Any]:
    public = public_sheet_entries([sheet])[0]
    public["file_id"] = artifact.file_id
    public["headers"] = sheet.get("headers", [])
    public["sample_rows"] = sheet.get("sample_rows", [])
    public["formula_summary"] = sheet.get("formula_summary", "")
    public["chart_summary"] = sheet.get("chart_summary", "")
    public["text_summary"] = sheet.get("text_summary", "")
    return public
