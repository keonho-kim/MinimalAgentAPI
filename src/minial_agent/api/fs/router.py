from fastapi import APIRouter

from minial_agent.api.fs.routers.files import router as files_router
from minial_agent.api.fs.routers.outputs import router as outputs_router
from minial_agent.api.fs.routers.preview import router as preview_router
from minial_agent.api.fs.routers.pptx import router as pptx_router

router = APIRouter(prefix="/api/fs")
router.include_router(files_router)
router.include_router(preview_router)
router.include_router(pptx_router)
router.include_router(outputs_router)
