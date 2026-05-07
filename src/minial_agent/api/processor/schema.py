from pydantic import BaseModel


class UploadedFileResponse(BaseModel):
    file_id: str
    filename: str
    file_type: str
    status: str
    path: str | None = None
    error: str | None = None


class UploadResponse(BaseModel):
    uploaded_files: list[UploadedFileResponse]
