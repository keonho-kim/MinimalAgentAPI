from fastapi import APIRouter

from .schema import FsCreateRequest, FsListResponse, FsMutationResponse
from .service import fs_service


router = APIRouter(prefix="/api/fs")


@router.get("/list", response_model=FsListResponse)
async def list_files(
    user_id: str,
    uuid: str,
    path: str = "/",
) -> FsListResponse:
    return fs_service.list_files(user_id=user_id, uuid=uuid, path=path)


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
