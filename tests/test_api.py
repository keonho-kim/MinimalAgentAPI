import asyncio
import importlib

from fastapi import FastAPI
from fastapi.testclient import TestClient

from minial_agent.api.endpoints.router import router
from minial_agent.api.endpoints.schema import ChatRequest
from minial_agent.api.endpoints.service import ChatService
from minial_agent.common.queue import InMemoryQueue

router_module = importlib.import_module("minial_agent.api.endpoints.router")


class FakeRouteService:
    def enqueue_chat(self, request: ChatRequest) -> str:
        assert request.user_id == "user"
        return "stream-id"

    async def stream_events(self, stream_id: str):
        assert stream_id == "stream-id"
        yield "event: done\ndata: {}\n\n"


def test_chat_post_returns_stream_id(monkeypatch) -> None:
    monkeypatch.setattr(router_module, "chat_service", FakeRouteService())
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.post(
        "/chat",
        json={
            "user_id": "user",
            "uuid": "session",
            "message": "hello",
            "chat_history": [],
        },
    )

    assert response.status_code == 200
    assert response.json() == {"stream_id": "stream-id"}


def test_chat_stream_returns_sse(monkeypatch) -> None:
    monkeypatch.setattr(router_module, "chat_service", FakeRouteService())
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    with client.stream("GET", "/chat/stream/stream-id") as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: done" in body


class FakeAgent:
    async def astream_events(self, *_args, **_kwargs):
        yield {"event": "on_chat_model_stream", "data": {"chunk": "hello"}}


class FakeErrorAgent:
    async def astream_events(self, *_args, **_kwargs):
        raise RuntimeError("boom")
        yield


class FakeRegistry:
    def __init__(self, agent) -> None:
        self.agent = agent

    def get_agent(self, user_id: str, uuid: str):
        assert user_id == "user"
        assert uuid == "session"
        return self.agent


def test_chat_service_streams_agent_events() -> None:
    async def run() -> None:
        service = ChatService(
            registry=FakeRegistry(FakeAgent()),
            queue=InMemoryQueue(),
        )
        request = ChatRequest(
            user_id="user",
            uuid="session",
            message="hello",
            chat_history=[],
        )

        await service._run_agent(stream_id="stream-id", request=request)
        stream = service.stream_events("stream-id")

        first = await anext(stream)
        second = await anext(stream)

        assert "event: langgraph" in first
        assert "on_chat_model_stream" in first
        assert "event: done" in second

    asyncio.run(run())


def test_chat_service_streams_error_events() -> None:
    async def run() -> None:
        service = ChatService(
            registry=FakeRegistry(FakeErrorAgent()),
            queue=InMemoryQueue(),
        )
        request = ChatRequest(
            user_id="user",
            uuid="session",
            message="hello",
            chat_history=[],
        )

        await service._run_agent(stream_id="stream-id", request=request)
        stream = service.stream_events("stream-id")

        event = await anext(stream)

        assert "event: error" in event
        assert "boom" in event

    asyncio.run(run())
