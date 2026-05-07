from pathlib import Path
from urllib.parse import urlencode

from fastapi import HTTPException

from minial_agent.api.fs.schemas import (
    FsListItem,
    FsListResponse,
    FsMutationResponse,
    FsPreviewResponse,
    FsSearchResponse,
)
from minial_agent.integrations.fs import WorkspaceFsError, WorkspaceFsService
from minial_agent.integrations.fs import workspace_fs_service as default_fs_service
from minial_agent.integrations.fs.models import FsListItem as FsListItemData


class FsApiService:
    def __init__(self, fs_service: WorkspaceFsService | None = None) -> None:
        self.fs_service = fs_service or default_fs_service

    def list_files(self, *, user_id: str, uuid: str, path: str = "/") -> FsListResponse:
        result = self._call(
            self.fs_service.list_files,
            user_id=user_id,
            uuid=uuid,
            path=path,
        )
        return FsListResponse(
            path=result.path,
            files=[self._list_item(item) for item in result.files],
        )

    def search_files(
        self,
        *,
        user_id: str,
        uuid: str,
        query: str,
        limit: int = 10,
    ) -> FsSearchResponse:
        result = self._call(
            self.fs_service.search_files,
            user_id=user_id,
            uuid=uuid,
            query=query,
            limit=limit,
        )
        return FsSearchResponse(matches=[self._list_item(item) for item in result.matches])

    def preview_file(self, *, user_id: str, uuid: str, path: str) -> FsPreviewResponse:
        result = self._call(
            self.fs_service.preview_file,
            user_id=user_id,
            uuid=uuid,
            path=path,
        )
        source_url = None
        if result.preview_type != "xlsx_grid":
            source_url = self._preview_source_url(
                user_id=user_id,
                uuid=uuid,
                path=result.path,
            )
        return FsPreviewResponse(
            path=result.path,
            filename=result.filename,
            file_type=result.file_type,
            preview_type=result.preview_type,
            source_url=source_url,
            workbook=result.workbook,
        )

    def preview_source_path(self, *, user_id: str, uuid: str, path: str) -> Path:
        return self._call(
            self.fs_service.preview_source_path,
            user_id=user_id,
            uuid=uuid,
            path=path,
        )

    def preview_source_media_type(self, path: Path) -> str:
        return self.fs_service.preview_source_media_type(path)

    def output_file_path(
        self,
        *,
        user_id: str,
        uuid: str,
        job_id: str,
        filename: str,
    ) -> Path:
        return self._call(
            self.fs_service.output_file_path,
            user_id=user_id,
            uuid=uuid,
            job_id=job_id,
            filename=filename,
        )

    def output_bundle_path(self, *, user_id: str, uuid: str, job_id: str) -> Path:
        return self._call(
            self.fs_service.output_bundle_path,
            user_id=user_id,
            uuid=uuid,
            job_id=job_id,
        )

    def create_file(
        self,
        *,
        user_id: str,
        uuid: str,
        path: str,
        content: str,
    ) -> FsMutationResponse:
        result = self._call(
            self.fs_service.create_file,
            user_id=user_id,
            uuid=uuid,
            path=path,
            content=content,
        )
        return FsMutationResponse(path=result.path)

    def delete_file(self, *, user_id: str, uuid: str, path: str) -> FsMutationResponse:
        result = self._call(
            self.fs_service.delete_file,
            user_id=user_id,
            uuid=uuid,
            path=path,
        )
        return FsMutationResponse(path=result.path)

    def move_path(
        self,
        *,
        user_id: str,
        uuid: str,
        path: str,
        destination_path: str,
    ) -> FsMutationResponse:
        result = self._call(
            self.fs_service.move_path,
            user_id=user_id,
            uuid=uuid,
            path=path,
            destination_path=destination_path,
        )
        return FsMutationResponse(path=result.path)

    def rename_path(
        self,
        *,
        user_id: str,
        uuid: str,
        path: str,
        name: str,
    ) -> FsMutationResponse:
        result = self._call(
            self.fs_service.rename_path,
            user_id=user_id,
            uuid=uuid,
            path=path,
            name=name,
        )
        return FsMutationResponse(path=result.path)

    def _call(self, method, **kwargs):
        try:
            return method(**kwargs)
        except WorkspaceFsError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    def _preview_source_url(self, *, user_id: str, uuid: str, path: str) -> str:
        return f"/api/fs/preview/source?{urlencode({'user_id': user_id, 'uuid': uuid, 'path': path})}"

    def _list_item(self, item: FsListItemData) -> FsListItem:
        return FsListItem(
            name=item.name,
            path=item.path,
            type=item.type,
            size=item.size,
            modified_at=item.modified_at,
        )
