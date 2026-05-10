from typing import Self

from pydantic import BaseModel, Field, model_validator


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


class FsCreateRequest(BaseModel):
    user_id: str = Field(min_length=1)
    uuid: str = Field(min_length=1)
    path: str = Field(min_length=1)
    content: str = ""


class FsMoveRequest(BaseModel):
    user_id: str = Field(min_length=1)
    uuid: str = Field(min_length=1)
    path: str = Field(min_length=1)
    destination_path: str = Field(min_length=1)


class FsRenameRequest(BaseModel):
    user_id: str = Field(min_length=1)
    uuid: str = Field(min_length=1)
    path: str = Field(min_length=1)
    name: str = Field(min_length=1)


class FsPptxTextShapeBoundsRequest(BaseModel):
    left: int = Field(ge=0)
    top: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class FsPptxTextShapeRequest(BaseModel):
    user_id: str = Field(min_length=1)
    uuid: str = Field(min_length=1)
    path: str = Field(min_length=1)
    slide_number: int = Field(ge=1)
    shape_id: int = Field(ge=1)
    text: str | None = None
    bounds: FsPptxTextShapeBoundsRequest | None = None

    @model_validator(mode="after")
    def require_edit(self) -> Self:
        if self.text is None and self.bounds is None:
            raise ValueError("PPTX text shape update requires text or bounds.")
        return self


class FsMutationResponse(BaseModel):
    path: str
