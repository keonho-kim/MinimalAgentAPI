import base64
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

from minial_agent.common.llm import llm_client
from minial_agent.integrations.upload.resolver import ResolvedUploadArtifact

from minial_agent.agents.utils.runtime import response_content


PageScanner = Callable[[Path, str], str]


def build_page_jobs(
    *,
    artifact: ResolvedUploadArtifact,
    pages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    jobs = []
    for page in pages:
        jobs.append(
            {
                "file_id": artifact.file_id,
                "source_filename": artifact.visible_name,
                "page_number": int(page.get("page_number", 0)),
                "filename": str(page.get("image_filename", "")),
                "image_path": Path(str(page.get("image_path", ""))),
            }
        )
    return jobs


def scan_page(
    *,
    page_path: Path,
    question: str,
    prompt: str,
) -> str:
    if not page_path.is_file():
        raise ValueError("Page image not found for VLM scan.")
    encoded = base64.b64encode(page_path.read_bytes()).decode("ascii")
    response = llm_client(disable_streaming=True).invoke(
        [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt.format(question=question)},
                    {
                        "type": "image",
                        "base64": encoded,
                        "mime_type": "image/png",
                        "filename": page_path.name,
                    },
                ],
            }
        ]
    )
    return response_content(response)


def parse_page_scan(raw_scan: str) -> tuple[bool, str]:
    normalized = raw_scan.strip()
    if "\n" in normalized or "\r" in normalized:
        raise ValueError("Invalid VLM scan output. Expected one line.")
    parts = [part.strip() for part in normalized.split(";", 1)]
    if len(parts) != 2 or parts[0] not in {"0", "1"}:
        raise ValueError("Invalid VLM scan output. Expected `<0/1>; <evidence>`.")
    return parts[0] == "1", parts[1]


def scan_artifact_pages(
    *,
    artifact: ResolvedUploadArtifact,
    question: str,
    prompt: str,
    pages: list[dict[str, Any]] | None = None,
    page_scanner: PageScanner | None = None,
) -> tuple[list[dict], int]:
    source_pages = pages if pages is not None else artifact.manifest.get("pages", [])
    if not isinstance(source_pages, list):
        source_pages = []

    page_jobs = build_page_jobs(artifact=artifact, pages=source_pages)
    relevant_pages = []
    with ThreadPoolExecutor(max_workers=min(8, max(len(page_jobs), 1))) as executor:
        raw_scans = list(
            executor.map(
                lambda job: (
                    page_scanner(job["image_path"], question)
                    if page_scanner
                    else scan_page(
                        page_path=job["image_path"],
                        question=question,
                        prompt=prompt,
                    )
                ),
                page_jobs,
            )
        )

    for page_job, raw_scan in zip(page_jobs, raw_scans, strict=True):
        raw_scan = (
            raw_scan.strip()
            if isinstance(raw_scan, str)
            else str(raw_scan).strip()
        )
        is_relevant, evidence = parse_page_scan(raw_scan)
        if not is_relevant:
            continue
        relevant_pages.append(
            {
                "file_id": page_job["file_id"],
                "source_filename": page_job["source_filename"],
                "page_number": page_job["page_number"],
                "filename": page_job["filename"],
                "is_relevant": 1,
                "evidence": evidence,
            }
        )
    return relevant_pages, len(page_jobs)


def build_page_answer(
    *,
    relevant_pages: list[dict],
    scanned_pages: int,
) -> dict:
    answer = build_evidence_answer(relevant_pages)
    return {
        "answer": answer,
        "relevant_pages": relevant_pages,
        "scanned_pages": scanned_pages,
        "relevant_page_count": len(relevant_pages),
    }


def build_evidence_answer(relevant_pages: list[dict]) -> str:
    if not relevant_pages:
        return "질문과 직접 관련된 페이지를 찾지 못했습니다."

    locations = ", ".join(
        f"{page['source_filename']}의 {page['page_number']}페이지"
        for page in relevant_pages
    )
    evidence = " ".join(
        str(page.get("evidence", "")).strip()
        for page in relevant_pages[:3]
        if str(page.get("evidence", "")).strip()
    )
    if evidence:
        return f"관련 근거는 {locations}에서 확인됩니다. 주요 근거: {evidence}"
    return f"관련 근거는 {locations}에서 확인됩니다."
