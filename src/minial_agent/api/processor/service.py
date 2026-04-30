from fastapi import UploadFile

from minial_agent.integrations.upload import UploadPipeline
from minial_agent.integrations.upload.registry import UploadRegistry
from minial_agent.integrations.upload.workspace import (
    ensure_upload_workspace,
    get_workspace_root,
)

from .schema import FileListItem, FileListResponse, UploadedFileResponse, UploadResponse


class ProcessorService:
    def __init__(self, upload_pipeline: UploadPipeline | None = None) -> None:
        self.upload_pipeline = upload_pipeline or UploadPipeline()

    async def upload_files(
        self,
        *,
        user_id: str,
        uuid: str,
        files: list[UploadFile],
    ) -> UploadResponse:
        uploaded_files = await self.upload_pipeline.upload_files(
            user_id=user_id,
            uuid=uuid,
            files=files,
        )
        return UploadResponse(
            uploaded_files=[
                UploadedFileResponse(
                    file_id=file.file_id,
                    filename=file.filename,
                    file_type=file.file_type,
                    status=file.status,
                    error=file.error,
                )
                for file in uploaded_files
            ]
        )

    def list_files(self, *, user_id: str, uuid: str) -> FileListResponse:
        workspace = ensure_upload_workspace(get_workspace_root(user_id, uuid))
        registry = UploadRegistry(workspace.registry_path)
        return FileListResponse(
            files=[
                FileListItem(
                    file_id=str(entry.get("file_id", "")),
                    filename=str(entry.get("visible_name", "")),
                    file_type=str(entry.get("file_type", "")),
                    status=str(entry.get("status", "")),
                    error=entry.get("error"),
                )
                for entry in registry.list_files()
            ]
        )


processor_service = ProcessorService()
