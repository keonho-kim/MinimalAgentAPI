from fastapi import UploadFile

from minial_agent.integrations.upload import UploadPipeline

from minial_agent.api.processor.schema import UploadedFileResponse, UploadResponse


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


processor_service = ProcessorService()
