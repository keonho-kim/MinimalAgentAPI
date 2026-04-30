from pydantic import BaseModel


class UploadedFileResponse(BaseModel):
    file_id: str
    filename: str
    file_type: str
    status: str
    error: str | None = None


class UploadResponse(BaseModel):
    uploaded_files: list[UploadedFileResponse]


class FileListItem(BaseModel):
    file_id: str
    filename: str
    file_type: str
    status: str
    error: str | None = None


class FileListResponse(BaseModel):
    files: list[FileListItem]
