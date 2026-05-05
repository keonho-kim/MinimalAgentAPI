from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from minial_agent.api.agent.schema import (
    ChatRequest,
    ChatResponse,
    HitlResumeRequest,
    HitlResumeResponse,
)
from minial_agent.api.agent.service import chat_service


router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    stream_id = chat_service.enqueue_chat(request)
    return ChatResponse(stream_id=stream_id)


@router.get("/chat/stream/{stream_id}")
async def stream_chat(stream_id: str) -> StreamingResponse:
    return StreamingResponse(
        chat_service.stream_events(stream_id),
        media_type="text/event-stream",
    )


@router.post("/chat/hitl/{stream_id}", response_model=HitlResumeResponse)
async def resume_hitl(
    stream_id: str,
    request: HitlResumeRequest,
) -> HitlResumeResponse:
    return await chat_service.resume_hitl(stream_id=stream_id, request=request)
