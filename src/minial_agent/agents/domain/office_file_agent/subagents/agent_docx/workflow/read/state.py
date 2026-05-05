from typing import Any, TypedDict


class DocxReadState(TypedDict, total=False):
    file_ref: str
    question: str
    artifact: Any
    relevant_pages: list[dict]
    scanned_pages: int
    answer_payload: dict
    result: str
