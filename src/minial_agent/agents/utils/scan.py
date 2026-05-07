import base64
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

from minial_agent.common.llm import llm_client
from minial_agent.integrations.upload.resolver import ResolvedUploadArtifact

from minial_agent.agents.utils.runtime import response_content


PageScanner = Callable[[Path, str], str]
EvidenceJudge = Callable[[str, dict[str, str]], bool]

PAGE_SCAN_BATCH_SIZE = 10

_EVIDENCE_SUFFICIENCY_PROMPT = """You are deciding whether the collected page evidence is enough to answer the user's question.

Return exactly `1` if the evidence is sufficient.
Return exactly `0` if more pages should be scanned.
Do not return JSON, markdown, or explanation.

Question:
{question}

Evidence:
{evidence}
"""


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


def parse_page_answer(raw_scan: Any) -> str | None:
    normalized = raw_scan.strip() if isinstance(raw_scan, str) else str(raw_scan).strip()
    if not normalized or normalized.lower() == "none":
        return None
    return normalized


def judge_evidence_sufficiency(question: str, evidence: dict[str, str]) -> bool:
    if not evidence:
        return False

    response = llm_client(disable_streaming=True).invoke(
        [
            {
                "role": "user",
                "content": _EVIDENCE_SUFFICIENCY_PROMPT.format(
                    question=question,
                    evidence=build_evidence_result(evidence),
                ),
            }
        ]
    )
    verdict = response_content(response).strip()
    if verdict not in {"0", "1"}:
        raise ValueError("Invalid VLM sufficiency output. Expected `0` or `1`.")
    return verdict == "1"


def scan_artifact_pages(
    *,
    artifact: ResolvedUploadArtifact,
    question: str,
    prompt: str,
    pages: list[dict[str, Any]] | None = None,
    page_scanner: PageScanner | None = None,
    evidence_judge: EvidenceJudge | None = None,
    batch_size: int | None = None,
) -> tuple[dict[str, str], int, bool]:
    source_pages = pages if pages is not None else artifact.manifest.get("pages", [])
    if not isinstance(source_pages, list):
        source_pages = []

    page_jobs = build_page_jobs(artifact=artifact, pages=source_pages)
    batch_size = batch_size or page_scan_batch_size()
    if batch_size < 1:
        raise ValueError("Page scan batch size must be at least 1.")

    evidence: dict[str, str] = {}
    scanned_pages = 0
    for start in range(0, len(page_jobs), batch_size):
        batch = page_jobs[start : start + batch_size]
        with ThreadPoolExecutor(max_workers=min(8, max(len(batch), 1))) as executor:
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
                    batch,
                )
            )

        scanned_pages += len(batch)
        for page_job, raw_scan in zip(batch, raw_scans, strict=True):
            answer = parse_page_answer(raw_scan)
            if answer is None:
                continue
            evidence[f"page_{page_job['page_number']}"] = answer

        if evidence and (
            evidence_judge(question, evidence)
            if evidence_judge
            else judge_evidence_sufficiency(question, evidence)
        ):
            return evidence, scanned_pages, True

    return evidence, scanned_pages, False


def build_evidence_result(evidence: dict[str, str]) -> str:
    if not evidence:
        return "None"
    return "\n".join(
        f"{page}: {answer}"
        for page, answer in evidence.items()
        if str(answer).strip()
    ) or "None"


def page_scan_batch_size() -> int:
    raw_value = os.getenv("AGENT_PAGE_SCAN_BATCH_SIZE", str(PAGE_SCAN_BATCH_SIZE))
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError("AGENT_PAGE_SCAN_BATCH_SIZE must be a positive integer.") from exc
    if value < 1:
        raise ValueError("AGENT_PAGE_SCAN_BATCH_SIZE must be a positive integer.")
    return value
