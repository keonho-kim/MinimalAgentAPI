from pathlib import Path
from urllib.parse import urlencode

from fastapi import HTTPException

from minial_agent.api.fs.schemas import (
    PptxDeckResponse,
    PptxExportResponse,
    PptxOperation,
    PptxOperationResponse,
    PptxSearchResponse,
)
from minial_agent.integrations.fs import WorkspaceFsError, WorkspaceFsService
from minial_agent.integrations.fs import workspace_fs_service as default_fs_service


class PptxApiService:
    def __init__(self, fs_service: WorkspaceFsService | None = None) -> None:
        self.fs_service = fs_service or default_fs_service

    def pptx_deck(self, *, user_id: str, uuid: str, path: str) -> PptxDeckResponse:
        result, deck = self._call(
            self.fs_service.pptx_deck,
            user_id=user_id,
            uuid=uuid,
            path=path,
        )
        return PptxDeckResponse(
            path=result.path,
            filename=Path(result.path).name,
            source_url=self._preview_source_url(user_id=user_id, uuid=uuid, path=result.path),
            deck=deck,
        )

    def pptx_operations(
        self,
        *,
        user_id: str,
        uuid: str,
        path: str,
        origin: str,
        expected_revision: int,
        operations: list[PptxOperation],
    ) -> PptxOperationResponse:
        return self._call(
            self.fs_service.pptx_operations,
            user_id=user_id,
            uuid=uuid,
            path=path,
            origin=origin,
            expected_revision=expected_revision,
            operations=operations,
        )

    def pptx_search(
        self,
        *,
        user_id: str,
        uuid: str,
        path: str,
        query: str,
        limit: int,
    ) -> PptxSearchResponse:
        return self._call(
            self.fs_service.pptx_search,
            user_id=user_id,
            uuid=uuid,
            path=path,
            query=query,
            limit=limit,
        )

    def pptx_export_pdf(self, *, user_id: str, uuid: str, path: str) -> PptxExportResponse:
        return self._call(
            self.fs_service.pptx_export_pdf,
            user_id=user_id,
            uuid=uuid,
            path=path,
        )

    def pptx_export_file(self, *, user_id: str, uuid: str, path: str) -> PptxExportResponse:
        return self._call(
            self.fs_service.pptx_export_file,
            user_id=user_id,
            uuid=uuid,
            path=path,
        )

    def _call(self, method, **kwargs):
        try:
            return method(**kwargs)
        except WorkspaceFsError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    def _preview_source_url(self, *, user_id: str, uuid: str, path: str) -> str:
        return f"/api/fs/preview/source?{urlencode({'user_id': user_id, 'uuid': uuid, 'path': path})}"
