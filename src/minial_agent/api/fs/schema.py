from typing import Any

from pydantic import BaseModel, Field


class FsListItem(BaseModel):
    name: str
    path: str
    type: str
    size: int | None = None
    modified_at: float | None = None


class FsListResponse(BaseModel):
    path: str
    files: list[FsListItem]


class FsSearchResponse(BaseModel):
    matches: list[FsListItem]


class FsPreviewResponse(BaseModel):
    path: str
    filename: str
    file_type: str
    preview_type: str
    source_url: str | None = None
    workbook: dict[str, Any] | None = None


class FsCreateRequest(BaseModel):
    user_id: str = Field(min_length=1)
    uuid: str = Field(min_length=1)
    path: str = Field(min_length=1)
    content: str = ""


class FsMutationResponse(BaseModel):
    path: str
