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


class FsMutationResponse(BaseModel):
    path: str
