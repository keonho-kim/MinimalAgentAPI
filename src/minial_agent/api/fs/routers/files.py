from fastapi import APIRouter

from minial_agent.api.fs.schemas import (
    FsCreateRequest,
    FsListResponse,
    FsMoveRequest,
    FsMutationResponse,
    FsRenameRequest,
    FsSearchResponse,
)
from minial_agent.api.fs.dependencies import fs_service


router = APIRouter()


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


@router.post("/move", response_model=FsMutationResponse)
async def move_path(request: FsMoveRequest) -> FsMutationResponse:
    return fs_service.move_path(
        user_id=request.user_id,
        uuid=request.uuid,
        path=request.path,
        destination_path=request.destination_path,
    )


@router.post("/rename", response_model=FsMutationResponse)
async def rename_path(request: FsRenameRequest) -> FsMutationResponse:
    return fs_service.rename_path(
        user_id=request.user_id,
        uuid=request.uuid,
        path=request.path,
        name=request.name,
    )
