import asyncio
import importlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, AIMessageChunk

from minial_agent.api.agent.router import router
from minial_agent.api.agent.schema import ChatRequest
from minial_agent.api.agent.events import StreamEventNormalizer
from minial_agent.api.agent.service import ChatService
from minial_agent.common.queue import InMemoryQueue

router_module = importlib.import_module("minial_agent.api.agent.router")


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


class FakeMessageObjectAgent:
    async def astream_events(self, *_args, **_kwargs):
        yield {
            "event": "on_chat_model_stream",
            "run_id": "model-run",
            "data": {"chunk": AIMessageChunk(content="hello")},
        }


class FakeThinkAgent:
    async def astream_events(self, *_args, **_kwargs):
        yield {
            "event": "on_chat_model_stream",
            "run_id": "model-run",
            "data": {
                "chunk": {
                    "reasoning_content": "I should answer in Korean.",
                    "content": "요청하신 작업을 완료했습니다.",
                }
            },
        }


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


class FakeLockManager:
    def __init__(self) -> None:
        self.keys: list[str] = []

    @asynccontextmanager
    async def lock(self, workspace_key: str):
        self.keys.append(workspace_key)
        yield


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
        third = await anext(stream)

        assert "event: queued" in first
        assert "event: agent_ui" in second
        assert '"kind": "assistant_delta"' in second
        assert '"text": "hello"' in second
        assert "event: done" in third

    asyncio.run(run())


def test_stream_event_normalizer_extracts_langchain_message_objects() -> None:
    normalizer = StreamEventNormalizer()

    stream_events = normalizer.normalize(
        {
            "event": "on_chat_model_stream",
            "run_id": "model-run",
            "data": {"chunk": AIMessageChunk(content="hello")},
        }
    )
    assert stream_events == [
        {
            "kind": "assistant_delta",
            "id": "model-run",
            "parentIds": [],
            "text": "hello",
        }
    ]

    end_events = StreamEventNormalizer().normalize(
        {
            "event": "on_chat_model_end",
            "run_id": "model-run",
            "data": {"output": AIMessage(content="final answer")},
        }
    )
    assert end_events == [
        {
            "kind": "assistant_delta",
            "id": "model-run",
            "parentIds": [],
            "text": "final answer",
        }
    ]


def test_stream_event_normalizer_extracts_text_and_tool_calls_from_message_object() -> None:
    normalizer = StreamEventNormalizer()
    events = normalizer.normalize(
        {
            "event": "on_chat_model_stream",
            "run_id": "model-run",
            "data": {
                "chunk": AIMessageChunk(
                    content="done",
                    tool_call_chunks=[
                        {
                            "name": "write_file",
                            "args": '{"file_path":"/README.md"}',
                            "id": "call_1",
                            "index": 0,
                        }
                    ],
                )
            },
        }
    )

    assert [event["kind"] for event in events] == ["assistant_delta", "activity"]
    assert events[0]["text"] == "done"
    assert events[1]["name"] == "write_file"
    assert events[1]["label"] == "파일 작성"
    assert events[1]["message"] == "AGENT가 파일 작성을 준비합니다."
    assert events[1]["input"] == {"file_path": "/README.md"}


def test_stream_event_normalizer_uses_server_tool_display_messages() -> None:
    normalizer = StreamEventNormalizer()

    events = normalizer.normalize(
        {
            "event": "on_tool_start",
            "name": "write_file",
            "run_id": "tool-run",
            "data": {"input": {"file_path": "/README.md"}},
        }
    )

    assert events[0]["kind"] == "activity"
    assert events[0]["status"] == "running"
    assert events[0]["label"] == "파일 작성"
    assert events[0]["message"] == "AGENT가 파일 작성을 시작합니다."


def test_stream_event_normalizer_marks_write_file_parent_directory_creation(tmp_path) -> None:
    normalizer = StreamEventNormalizer(workspace_root=tmp_path)

    start_events = normalizer.normalize(
        {
            "event": "on_tool_start",
            "name": "write_file",
            "run_id": "tool-run",
            "data": {"input": {"file_path": "/code/ensemble_tree.py"}},
        }
    )

    assert start_events[0]["kind"] == "activity"
    assert start_events[0]["status"] == "running"
    assert start_events[0]["message"] == "AGENT가 필요한 폴더를 만들고 파일 작성을 시작합니다."
    assert start_events[0]["summary"]["createsParentDirectory"] is True
    assert start_events[0]["summary"]["parentPath"] == "/code"

    (tmp_path / "code").mkdir()
    end_events = normalizer.normalize(
        {
            "event": "on_tool_end",
            "name": "write_file",
            "run_id": "tool-run",
            "data": {"output": {"path": "/code/ensemble_tree.py"}},
        }
    )

    assert end_events[0]["status"] == "completed"
    assert end_events[0]["message"] == "AGENT가 필요한 폴더를 만들고 파일 작성을 완료했습니다."
    assert end_events[0]["summary"]["parentPath"] == "/code"
    assert end_events[0]["summary"]["parentDirectoryCreated"] is True


def test_stream_event_normalizer_does_not_mark_root_or_existing_write_parent(tmp_path) -> None:
    (tmp_path / "code").mkdir()
    normalizer = StreamEventNormalizer(workspace_root=tmp_path)

    root_file_events = normalizer.normalize(
        {
            "event": "on_tool_start",
            "name": "write_file",
            "run_id": "root-tool-run",
            "data": {"input": {"file_path": "/README.md"}},
        }
    )
    existing_parent_events = normalizer.normalize(
        {
            "event": "on_tool_start",
            "name": "write_file",
            "run_id": "existing-tool-run",
            "data": {"input": {"file_path": "/code/ensemble_tree.py"}},
        }
    )

    assert root_file_events[0]["message"] == "AGENT가 파일 작성을 시작합니다."
    assert "createsParentDirectory" not in root_file_events[0]["summary"]
    assert existing_parent_events[0]["message"] == "AGENT가 파일 작성을 시작합니다."
    assert "createsParentDirectory" not in existing_parent_events[0]["summary"]


def test_stream_event_normalizer_ignores_write_file_paths_outside_workspace(tmp_path) -> None:
    normalizer = StreamEventNormalizer(workspace_root=tmp_path)

    events = normalizer.normalize(
        {
            "event": "on_tool_start",
            "name": "write_file",
            "run_id": "tool-run",
            "data": {"input": {"file_path": "/../outside.txt"}},
        }
    )

    assert events[0]["message"] == "AGENT가 파일 작성을 시작합니다."
    assert "createsParentDirectory" not in events[0]["summary"]


def test_chat_service_streams_langchain_message_object_events() -> None:
    async def run() -> None:
        service = ChatService(
            registry=FakeRegistry(FakeMessageObjectAgent()),
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
        third = await anext(stream)

        assert "event: queued" in first
        assert "event: agent_ui" in second
        assert '"kind": "assistant_delta"' in second
        assert '"text": "hello"' in second
        assert "event: done" in third

    asyncio.run(run())


def test_chat_service_streams_think_and_answer_events() -> None:
    async def run() -> None:
        service = ChatService(
            registry=FakeRegistry(FakeThinkAgent()),
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
        think_event = await anext(stream)
        answer_event = await anext(stream)
        done_event = await anext(stream)

        assert "event: queued" in first
        assert "event: agent_ui" in think_event
        assert '"kind": "think_delta"' in think_event
        assert "I should answer in Korean." in think_event
        assert "event: agent_ui" in answer_event
        assert '"kind": "assistant_delta"' in answer_event
        assert "요청하신 작업을 완료했습니다." in answer_event
        assert "event: done" in done_event

    asyncio.run(run())


def test_stream_event_normalizer_does_not_guess_think_from_text() -> None:
    normalizer = StreamEventNormalizer()

    first_events = normalizer.normalize(
        {
            "event": "on_chat_model_stream",
            "run_id": "model-run",
            "data": {"chunk": "I will now formulate the final response"},
        }
    )
    second_events = normalizer.normalize(
        {
            "event": "on_chat_model_stream",
            "run_id": "model-run",
            "data": {"chunk": ". 전문 답변입니다."},
        }
    )

    assert first_events == [
        {
            "kind": "assistant_delta",
            "id": "model-run",
            "parentIds": [],
            "text": "I will now formulate the final response",
        }
    ]
    assert second_events == [
        {
            "kind": "assistant_delta",
            "id": "model-run",
            "parentIds": [],
            "text": ". 전문 답변입니다.",
        },
    ]


def test_stream_event_normalizer_extracts_structured_reasoning_only() -> None:
    normalizer = StreamEventNormalizer()

    events = normalizer.normalize(
        {
            "event": "on_chat_model_stream",
            "run_id": "model-run",
            "data": {
                "chunk": {
                    "reasoning_content": "I should be concise.",
                    "content": "간단히 답변하겠습니다.",
                }
            },
        }
    )

    assert events == [
        {
            "kind": "think_delta",
            "id": "model-run",
            "parentIds": [],
            "text": "I should be concise.",
        },
        {
            "kind": "assistant_delta",
            "id": "model-run",
            "parentIds": [],
            "text": "간단히 답변하겠습니다.",
        },
    ]


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
        error_event = await anext(stream)

        assert "event: queued" in event
        assert "event: error" in error_event
        assert "boom" in error_event

    asyncio.run(run())


def test_chat_service_locks_by_user_id() -> None:
    async def run() -> None:
        lock_manager = FakeLockManager()
        service = ChatService(
            registry=FakeRegistry(FakeAgent()),
            queue=InMemoryQueue(),
            lock_manager=lock_manager,
        )
        request = ChatRequest(
            user_id="user",
            uuid="session",
            message="hello",
            chat_history=[],
        )

        await service._run_agent(stream_id="stream-id", request=request)

        assert lock_manager.keys == ["user"]

    asyncio.run(run())
