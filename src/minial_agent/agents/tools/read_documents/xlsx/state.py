from typing import Any, TypedDict


class XlsxReadState(TypedDict, total=False):
    file_ref: str
    question: str
    artifact: Any
    workbook: dict
    selected_range: dict
    data_profile: dict
    answer_payload: dict
    result: str
