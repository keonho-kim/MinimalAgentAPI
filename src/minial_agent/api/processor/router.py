from fastapi import APIRouter, File, Form, UploadFile

from .schema import FileListResponse, UploadResponse
from .service import processor_service


router = APIRouter(prefix="/api")


@router.post("/upload", response_model=UploadResponse)
async def upload(
    user_id: str = Form(...),
    uuid: str = Form(...),
    files: list[UploadFile] = File(...),
) -> UploadResponse:
    return await processor_service.upload_files(
        user_id=user_id,
        uuid=uuid,
        files=files,
    )


@router.get("/files", response_model=FileListResponse)
async def list_files(user_id: str, uuid: str) -> FileListResponse:
    return processor_service.list_files(user_id=user_id, uuid=uuid)
