from minial_agent.api.fs.services import FsApiService, PptxApiService


fs_service = FsApiService()
pptx_service = PptxApiService()

__all__ = ["fs_service", "pptx_service"]
