from typing import Any, TypedDict


class XlsxReadState(TypedDict, total=False):
    file_ref: str
    question: str
    artifact: Any
    workbook: dict
    relevant_sheets: list[dict]
    relevant_pages: list[dict]
    scanned_pages: int
    answer_payload: dict
    result: str
