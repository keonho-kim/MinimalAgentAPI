from pathlib import Path

from minial_agent.integrations.fs import listing, mutations, outputs, preview
from minial_agent.integrations.fs.models import FsList, FsMutation, FsPreview, FsSearch


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


workspace_fs_service = WorkspaceFsService()
