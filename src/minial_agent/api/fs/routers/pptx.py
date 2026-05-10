from fastapi import APIRouter

from minial_agent.api.fs.dependencies import pptx_service
from minial_agent.api.fs.schemas import (
    PptxDeckResponse,
    PptxExportRequest,
    PptxExportResponse,
    PptxOperationRequest,
    PptxOperationResponse,
    PptxSearchResponse,
)


router = APIRouter(prefix="/pptx")


@router.get("/deck", response_model=PptxDeckResponse)
async def get_pptx_deck(user_id: str, uuid: str, path: str) -> PptxDeckResponse:
    return pptx_service.pptx_deck(user_id=user_id, uuid=uuid, path=path)


@router.post("/operations", response_model=PptxOperationResponse)
async def apply_pptx_operations(
    request: PptxOperationRequest,
) -> PptxOperationResponse:
    return pptx_service.pptx_operations(
        user_id=request.user_id,
        uuid=request.uuid,
        path=request.path,
        origin=request.origin,
        expected_revision=request.expected_revision,
        operations=request.operations,
    )


@router.get("/search", response_model=PptxSearchResponse)
async def search_pptx(user_id: str, uuid: str, path: str, q: str, limit: int = 10):
    return pptx_service.pptx_search(
        user_id=user_id,
        uuid=uuid,
        path=path,
        query=q,
        limit=limit,
    )


@router.post("/export/pdf", response_model=PptxExportResponse)
async def export_pptx_pdf(request: PptxExportRequest) -> PptxExportResponse:
    return pptx_service.pptx_export_pdf(
        user_id=request.user_id,
        uuid=request.uuid,
        path=request.path,
    )


@router.post("/export/pptx", response_model=PptxExportResponse)
async def export_pptx_file(request: PptxExportRequest) -> PptxExportResponse:
    return pptx_service.pptx_export_file(
        user_id=request.user_id,
        uuid=request.uuid,
        path=request.path,
    )
