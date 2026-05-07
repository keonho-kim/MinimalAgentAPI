from typing import Any

from pydantic import BaseModel


class FsPreviewResponse(BaseModel):
    path: str
    filename: str
    file_type: str
    preview_type: str
    source_url: str | None = None
    workbook: dict[str, Any] | None = None
