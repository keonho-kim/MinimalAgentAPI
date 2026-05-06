from fastapi import APIRouter

from minial_agent.api.session.schema import (
    SessionTitleRequest,
    SessionTitleResponse,
)
from minial_agent.api.session.service import session_service


router = APIRouter(prefix="/api/session")


@router.post("/title", response_model=SessionTitleResponse)
def create_session_title(request: SessionTitleRequest) -> SessionTitleResponse:
    title = session_service.create_title(
        user_id=request.user_id,
        uuid=request.uuid,
        message=request.message,
    )
    return SessionTitleResponse(title=title)
