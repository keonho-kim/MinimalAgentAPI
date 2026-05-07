from fastapi import APIRouter
from fastapi.responses import FileResponse

from minial_agent.api.fs.service import fs_service


router = APIRouter()


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
