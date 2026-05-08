from typing import Any, TypedDict


class DocxReadState(TypedDict, total=False):
    file_ref: str
    question: str
    full_scan: bool
    artifact: Any
    evidence: dict[str, str]
    scanned_pages: int
    is_sufficient: bool
    result: str
