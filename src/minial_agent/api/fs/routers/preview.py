from fastapi import APIRouter
from fastapi.responses import FileResponse

from minial_agent.api.fs.schemas import FsPreviewResponse
from minial_agent.api.fs.service import fs_service


router = APIRouter()


@router.get("/preview", response_model=FsPreviewResponse)
async def preview_file(user_id: str, uuid: str, path: str) -> FsPreviewResponse:
    return fs_service.preview_file(user_id=user_id, uuid=uuid, path=path)


@router.get("/preview/source")
async def preview_source(user_id: str, uuid: str, path: str) -> FileResponse:
    source_path = fs_service.preview_source_path(user_id=user_id, uuid=uuid, path=path)
    return FileResponse(
        source_path,
        filename=source_path.name,
        media_type=fs_service.preview_source_media_type(source_path),
    )
