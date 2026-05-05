from fastapi import APIRouter
from fastapi.responses import FileResponse

from minial_agent.api.fs.schema import (
    FsCreateRequest,
    FsListResponse,
    FsMutationResponse,
    FsPreviewResponse,
    FsSearchResponse,
)
from minial_agent.api.fs.service import fs_service


router = APIRouter(prefix="/api/fs")


@router.get("/list", response_model=FsListResponse)
async def list_files(
    user_id: str,
    uuid: str,
    path: str = "/",
) -> FsListResponse:
    return fs_service.list_files(user_id=user_id, uuid=uuid, path=path)


@router.get("/search", response_model=FsSearchResponse)
async def search_files(
    user_id: str,
    uuid: str,
    q: str,
    limit: int = 10,
) -> FsSearchResponse:
    return fs_service.search_files(user_id=user_id, uuid=uuid, query=q, limit=limit)


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


@router.get("/outputs/{job_id}/files/{filename}")
async def download_output_file(
    job_id: str,
    filename: str,
    user_id: str,
    uuid: str,
) -> FileResponse:
    return FileResponse(
        fs_service.output_file_path(
            user_id=user_id,
            uuid=uuid,
            job_id=job_id,
            filename=filename,
        ),
        filename=filename,
    )


@router.get("/outputs/{job_id}/result.zip")
async def download_output_bundle(
    job_id: str,
    user_id: str,
    uuid: str,
) -> FileResponse:
    return FileResponse(
        fs_service.output_bundle_path(
            user_id=user_id,
            uuid=uuid,
            job_id=job_id,
        ),
        filename="result.zip",
        media_type="application/zip",
    )


@router.post("/files", response_model=FsMutationResponse)
async def create_file(request: FsCreateRequest) -> FsMutationResponse:
    return fs_service.create_file(
        user_id=request.user_id,
        uuid=request.uuid,
        path=request.path,
        content=request.content,
    )


@router.delete("/files", response_model=FsMutationResponse)
async def delete_file(user_id: str, uuid: str, path: str) -> FsMutationResponse:
    return fs_service.delete_file(user_id=user_id, uuid=uuid, path=path)
