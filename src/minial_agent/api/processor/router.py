from fastapi import APIRouter, File, Form, UploadFile

from minial_agent.api.processor.schema import UploadResponse
from minial_agent.api.processor.service import processor_service


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
