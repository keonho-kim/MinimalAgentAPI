from pathlib import Path

from minial_agent.integrations.fs import listing, mutations, outputs, pptx, preview
from minial_agent.integrations.fs.models import FsList, FsMutation, FsPreview, FsSearch
from minial_agent.integrations.pptx.model import (
    PptxDeck,
    PptxExportResponse,
    PptxOperation,
    PptxOperationResponse,
    PptxSearchResponse,
)


class WorkspaceFsService:
    def list_files(self, *, user_id: str, uuid: str, path: str = "/") -> FsList:
        return listing.list_files(user_id=user_id, uuid=uuid, path=path)

    def search_files(
        self,
        *,
        user_id: str,
        uuid: str,
        query: str,
        limit: int = 10,
    ) -> FsSearch:
        return listing.search_files(
            user_id=user_id,
            uuid=uuid,
            query=query,
            limit=limit,
        )

    def preview_file(self, *, user_id: str, uuid: str, path: str) -> FsPreview:
        return preview.preview_file(user_id=user_id, uuid=uuid, path=path)

    def preview_source_path(self, *, user_id: str, uuid: str, path: str) -> Path:
        return preview.preview_source_path(user_id=user_id, uuid=uuid, path=path)

    def preview_source_media_type(self, path: Path) -> str:
        return preview.preview_source_media_type(path)

    def output_file_path(
        self,
        *,
        user_id: str,
        uuid: str,
        job_id: str,
        filename: str,
    ) -> Path:
        return outputs.output_file_path(
            user_id=user_id,
            uuid=uuid,
            job_id=job_id,
            filename=filename,
        )

    def output_bundle_path(self, *, user_id: str, uuid: str, job_id: str) -> Path:
        return outputs.output_bundle_path(user_id=user_id, uuid=uuid, job_id=job_id)

    def create_file(
        self,
        *,
        user_id: str,
        uuid: str,
        path: str,
        content: str,
    ) -> FsMutation:
        return mutations.create_file(
            user_id=user_id,
            uuid=uuid,
            path=path,
            content=content,
        )

    def delete_file(self, *, user_id: str, uuid: str, path: str) -> FsMutation:
        return mutations.delete_file(user_id=user_id, uuid=uuid, path=path)

    def move_path(
        self,
        *,
        user_id: str,
        uuid: str,
        path: str,
        destination_path: str,
    ) -> FsMutation:
        return mutations.move_path(
            user_id=user_id,
            uuid=uuid,
            path=path,
            destination_path=destination_path,
        )

    def rename_path(
        self,
        *,
        user_id: str,
        uuid: str,
        path: str,
        name: str,
    ) -> FsMutation:
        return mutations.rename_path(
            user_id=user_id,
            uuid=uuid,
            path=path,
            name=name,
        )

    def update_pptx_text_shape(
        self,
        *,
        user_id: str,
        uuid: str,
        path: str,
        slide_number: int,
        shape_id: int,
        text: str | None,
        bounds: dict[str, int] | None,
    ) -> FsMutation:
        return mutations.update_pptx_text_shape(
            user_id=user_id,
            uuid=uuid,
            path=path,
            slide_number=slide_number,
            shape_id=shape_id,
            text=text,
            bounds=bounds,
        )

    def pptx_deck(self, *, user_id: str, uuid: str, path: str) -> tuple[FsMutation, PptxDeck]:
        return pptx.pptx_deck(user_id=user_id, uuid=uuid, path=path)

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
        return pptx.pptx_operations(
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
        return pptx.pptx_search(
            user_id=user_id,
            uuid=uuid,
            path=path,
            query=query,
            limit=limit,
        )

    def pptx_export_pdf(self, *, user_id: str, uuid: str, path: str) -> PptxExportResponse:
        return pptx.pptx_export_pdf(user_id=user_id, uuid=uuid, path=path)

    def pptx_export_file(self, *, user_id: str, uuid: str, path: str) -> PptxExportResponse:
        return pptx.pptx_export_file(user_id=user_id, uuid=uuid, path=path)


workspace_fs_service = WorkspaceFsService()
