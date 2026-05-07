from typing import Any, TypedDict


class PptxReadState(TypedDict, total=False):
    file_ref: str
    question: str
    artifact: Any
    evidence: dict[str, str]
    scanned_pages: int
    is_sufficient: bool
    result: str
