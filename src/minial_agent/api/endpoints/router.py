from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from .schema import ChatRequest, ChatResponse
from .service import chat_service


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
