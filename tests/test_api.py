import asyncio
import importlib
import socket
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from langgraph.types import Command, Interrupt

from minial_agent.api.agent.router import router
from minial_agent.api.agent.schema import ChatRequest, HitlResumeRequest, HitlResumeResponse
from minial_agent.api.agent.events import StreamEventNormalizer
from minial_agent.api.agent.hitl import extract_hitl_payload
from minial_agent.api.agent.service import ChatService
from minial_agent.common.queue import InMemoryQueue
from minial_agent.constants.user_request import USER_REQUEST

router_module = importlib.import_module("minial_agent.api.agent.router")


class FakeRouteService:
    def enqueue_chat(self, request: ChatRequest) -> str:
        assert request.user_id == "user"
        return "stream-id"

    async def stream_events(self, stream_id: str):
        assert stream_id == "stream-id"
        yield "event: done\ndata: {}\n\n"

    async def resume_hitl(
        self,
        *,
        stream_id: str,
        request: HitlResumeRequest,
    ) -> HitlResumeResponse:
        assert stream_id == "stream-id"
        assert request.decisions[0].type == "approve"
        return HitlResumeResponse(stream_id=stream_id, status="accepted")


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


def test_chat_hitl_resume_returns_status(monkeypatch) -> None:
    monkeypatch.setattr(router_module, "chat_service", FakeRouteService())
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.post(
        "/chat/hitl/stream-id",
        json={"decisions": [{"type": "approve"}]},
    )

    assert response.status_code == 200
    assert response.json() == {"stream_id": "stream-id", "status": "accepted"}


class FakeAgent:
    def __init__(self) -> None:
        self.inputs = []

    async def astream_events(self, input_value, *_args, **_kwargs):
        self.inputs.append(input_value)
        yield _message_stream_event(AIMessageChunk(content="hello"))


class FakeMessageObjectAgent:
    async def astream_events(self, *_args, **_kwargs):
        yield _message_stream_event(AIMessageChunk(content="hello"))


class FakeThinkAgent:
    async def astream_events(self, *_args, **_kwargs):
        yield _message_stream_event(
            {
                "reasoning_content": "I should answer in Korean.",
                "content": "요청하신 작업을 완료했습니다.",
            }
        )


class FakeErrorAgent:
    async def astream_events(self, *_args, **_kwargs):
        raise RuntimeError("boom")
        yield


class FakeHitlAgent:
    def __init__(self) -> None:
        self.inputs = []

    async def astream_events(self, input_value, *_args, **_kwargs):
        self.inputs.append(input_value)
        if isinstance(input_value, Command):
            yield _message_stream_event(AIMessageChunk(content="approved"))
            return
        yield {
            "event": "on_chain_stream",
            "name": "LangGraph",
            "run_id": "graph-run",
            "parent_ids": [],
            "data": {
                "chunk": {
                    "__interrupt__": [
                        {
                            "id": "interrupt-1",
                            "value": {
                                "action_requests": [
                                    {
                                        "name": "write_file",
                                        "args": {
                                            "file_path": "/draft.txt",
                                            "content": "hello",
                                        },
                                        "description": "Approve write",
                                    }
                                ],
                                "review_configs": [
                                    {
                                        "action_name": "write_file",
                                        "allowed_decisions": [
                                            "approve",
                                            "edit",
                                            "reject",
                                        ],
                                    }
                                ],
                            },
                        }
                    ]
                }
            },
        }


def _message_stream_event(chunk):
    return {
        "event": "on_chat_model_stream",
        "name": "model",
        "run_id": "model-run",
        "parent_ids": [],
        "data": {"chunk": chunk},
    }


def _text_event(kind: str, run_id: str, source_event: str, text: str):
    return {
        "kind": kind,
        "id": run_id,
        "sourceEvent": source_event,
        "name": None,
        "runId": run_id,
        "parentIds": [],
        "text": text,
    }


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
        agent = FakeAgent()
        service = ChatService(
            registry=FakeRegistry(agent),
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
        assert agent.inputs[0]["messages"][-1] == {
            "role": "user",
            "content": USER_REQUEST.format(user_query="hello"),
        }

    asyncio.run(run())


def test_chat_service_does_not_synthesize_workspace_skill_event(
    tmp_path,
    monkeypatch,
) -> None:
    skill_dir = tmp_path / "user" / ".agents" / "skills" / "writing-guide"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: writing-guide
description: Use this writing guide for writing requests.
---

# Writing Guide
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))

    async def run() -> None:
        agent = FakeAgent()
        service = ChatService(
            registry=FakeRegistry(agent),
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

        queued = await anext(stream)
        answer_event = await anext(stream)
        done_event = await anext(stream)

        assert "event: queued" in queued
        assert '"kind": "assistant_delta"' in answer_event
        assert "event: done" in done_event

    asyncio.run(run())


def test_chat_service_wraps_only_latest_user_message() -> None:
    async def run() -> None:
        agent = FakeAgent()
        service = ChatService(
            registry=FakeRegistry(agent),
            queue=InMemoryQueue(),
        )
        request = ChatRequest(
            user_id="user",
            uuid="session",
            message="latest question",
            chat_history=[
                {"role": "user", "content": "previous question"},
                {"role": "assistant", "content": "previous answer"},
            ],
        )

        await service._run_agent(stream_id="stream-id", request=request)

        assert agent.inputs[0]["messages"] == [
            {"role": "user", "content": "previous question"},
            {"role": "assistant", "content": "previous answer"},
            {
                "role": "user",
                "content": USER_REQUEST.format(user_query="latest question"),
            },
        ]

    asyncio.run(run())


def test_chat_service_streams_hitl_request_and_resumes() -> None:
    async def run() -> None:
        agent = FakeHitlAgent()
        service = ChatService(
            registry=FakeRegistry(agent),
            queue=InMemoryQueue(),
            lock_manager=FakeLockManager(),
        )
        request = ChatRequest(
            user_id="user",
            uuid="session",
            message="write a file",
            chat_history=[],
        )

        await service._run_agent(stream_id="stream-id", request=request)
        queue_key = service._queue_key("stream-id")
        queued = await service.queue.lpop(queue_key, timeout=0.1)
        hitl = await service.queue.lpop(queue_key, timeout=0.1)
        assert queued["event"] == "queued"
        assert hitl["event"] == "hitl_request"
        assert hitl["data"]["actions"][0]["name"] == "write_file"
        assert hitl["data"]["actions"][0]["args"]["file_path"] == "/draft.txt"

        response = await service.resume_hitl(
            stream_id="stream-id",
            request=HitlResumeRequest(decisions=[{"type": "approve"}]),
        )
        assert response.status == "accepted"

        events = []
        for _ in range(4):
            item = await service.queue.lpop(queue_key, timeout=1)
            if item is not None:
                events.append(item)
            if item and item["event"] == "done":
                break

        assert [event["event"] for event in events] == [
            "hitl_resumed",
            "agent_ui",
            "done",
        ]
        assert isinstance(agent.inputs[1], Command)

    asyncio.run(run())


def test_chat_service_hitl_extraction_ignores_nonserializable_event_objects() -> None:
    raw_socket = socket.socket()
    try:
        payload = extract_hitl_payload(
            stream_id="stream-id",
            event={
                "event": "on_chain_stream",
                "metadata": {"client_socket": raw_socket},
                "data": {"runtime": raw_socket},
            },
        )
    finally:
        raw_socket.close()

    assert payload is None


def test_chat_service_extracts_langgraph_v2_interrupt_objects() -> None:
    payload = extract_hitl_payload(
        stream_id="stream-id",
        event={
            "type": "values",
            "interrupts": [
                Interrupt(
                    value={
                        "action_requests": [
                            {
                                "name": "write_file",
                                "args": {"file_path": "/draft.txt"},
                                "description": "Approve write",
                            }
                        ],
                        "review_configs": [
                            {
                                "allowed_decisions": ["approve", "edit", "reject"],
                            }
                        ],
                    },
                    id="interrupt-1",
                )
            ],
        },
    )

    assert payload == {
        "stream_id": "stream-id",
        "actions": [
            {
                "name": "write_file",
                "args": {"file_path": "/draft.txt"},
                "description": "Approve write",
                "allowed_decisions": ["approve", "edit", "reject"],
            }
        ],
    }


def test_chat_service_rejects_missing_hitl_stream() -> None:
    async def run() -> None:
        service = ChatService(queue=InMemoryQueue())

        with pytest.raises(HTTPException) as exc_info:
            await service.resume_hitl(
                stream_id="missing",
                request=HitlResumeRequest(decisions=[{"type": "approve"}]),
            )

        assert exc_info.value.status_code == 404

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
    assert stream_events[0] == _text_event(
        "assistant_delta",
        "model-run",
        "on_chat_model_stream",
        "hello",
    )

    end_events = StreamEventNormalizer().normalize(
        {
            "event": "on_chat_model_end",
            "run_id": "model-run",
            "data": {"output": AIMessage(content="final answer")},
        }
    )
    assert end_events[0]["kind"] == "activity"
    assert end_events[0]["label"] == "응답 생성"
    assert end_events[0]["message"] == "AGENT가 답변을 정리합니다."
    assert end_events[1] == _text_event(
        "assistant_delta",
        "model-run",
        "on_chat_model_end",
        "final answer",
    )


def test_stream_event_normalizer_adds_model_start_activity() -> None:
    events = StreamEventNormalizer().normalize(
        {
            "event": "on_chat_model_start",
            "name": "ChatModel",
            "run_id": "model-run",
            "parent_ids": [],
            "metadata": {"ls_model_name": "local-model"},
            "data": {"input": {}},
        }
    )

    assert events == [
        {
            "kind": "activity",
            "type": "model",
            "id": "model-run",
            "sourceEvent": "on_chat_model_start",
            "runId": "model-run",
            "parentIds": [],
            "name": "ChatModel",
            "label": "응답 생성",
            "message": "AGENT가 요청을 분석합니다.",
            "status": "running",
            "details": {
                "description": "모델 응답을 생성하는 단계입니다.",
                "node": None,
                "model": "local-model",
            },
        }
    ]


def test_stream_event_normalizer_converts_custom_workflow_event() -> None:
    events = StreamEventNormalizer().normalize(
        {
            "event": "on_custom_event",
            "name": "office_workflow",
            "run_id": "custom-run",
            "parent_ids": ["tool-run"],
            "data": {
                "name": "docx_read_scan",
                "label": "DOCX 읽기",
                "message": "DOCX 페이지 4개를 스캔합니다.",
                "status": "running",
                "details": {"path": "report.docx", "description": "4 pages"},
            },
        }
    )

    assert events[0]["kind"] == "activity"
    assert events[0]["type"] == "workflow"
    assert events[0]["label"] == "DOCX 읽기"
    assert events[0]["message"] == "DOCX 페이지 4개를 스캔합니다."
    assert events[0]["details"]["description"] == "4 pages"


def test_stream_event_normalizer_filters_generic_chain_events() -> None:
    normalizer = StreamEventNormalizer()

    hidden = normalizer.normalize(
        {
            "event": "on_chain_start",
            "name": "LangGraph",
            "run_id": "graph-run",
            "data": {"input": {}},
        }
    )
    visible = normalizer.normalize(
        {
            "event": "on_chain_start",
            "name": "task",
            "run_id": "task-run",
            "data": {"input": {"description": "office work"}},
        }
    )

    assert hidden == []
    assert visible[0]["kind"] == "activity"
    assert visible[0]["type"] == "subagent"
    assert visible[0]["label"] == "서브에이전트 위임"
    assert visible[0]["details"]["delegationRunId"] == "task-run"


def test_stream_event_normalizer_maps_agent_chain_to_delegation_step() -> None:
    normalizer = StreamEventNormalizer()

    normalizer.normalize(
        {
            "event": "on_chain_start",
            "name": "task",
            "run_id": "task-run",
            "data": {"input": {"description": "office work"}},
        }
    )
    events = normalizer.normalize(
        {
            "event": "on_chain_start",
            "name": "editor_docx",
            "run_id": "docx-agent-run",
            "parent_ids": ["graph-run", "task-run"],
            "data": {"input": {"file_id": "file_001"}},
        }
    )

    assert events[0]["kind"] == "activity"
    assert events[0]["type"] == "agent_step"
    assert events[0]["label"] == "DOCX 에이전트"
    assert events[0]["details"]["delegationRunId"] == "task-run"


def test_stream_event_normalizer_hides_office_worker_chain_wrappers() -> None:
    events = StreamEventNormalizer().normalize(
        {
            "event": "on_chain_start",
            "name": "read_pdf_file",
            "run_id": "answer-chain-run",
            "data": {"input": {"file_id": "file_001"}},
        }
    )

    assert events == []


def test_stream_event_normalizer_extracts_text_and_tool_calls_from_message_object() -> (
    None
):
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
    assert "input" not in events[1]
    assert events[1]["details"]["path"] == "/README.md"


def test_stream_event_normalizer_preserves_model_text_without_selector_filtering() -> None:
    normalizer = StreamEventNormalizer()

    events = normalizer.normalize(
        {
            "event": "on_chat_model_stream",
            "run_id": "answer-run",
            "data": {
                "chunk": '[{"tools": []}]현재 폴더가 비어 있어 README.md 내용을 정할 수 없습니다.'
            },
        }
    )

    assert events[0]["kind"] == "assistant_delta"
    assert events[0]["text"] == (
        '[{"tools": []}]현재 폴더가 비어 있어 README.md 내용을 정할 수 없습니다.'
    )


def test_stream_event_normalizer_preserves_stream_chunk_spacing() -> None:
    normalizer = StreamEventNormalizer()
    chunks = ["이미 ", "README.md", " 파일에 ", "매우 ", "상세하고 "]

    events = [
        event
        for chunk in chunks
        for event in normalizer.normalize(
            {
                "event": "on_chat_model_stream",
                "run_id": "answer-run",
                "data": {"chunk": chunk},
            }
        )
    ]

    assert "".join(event["text"] for event in events) == "".join(chunks)


def test_stream_event_normalizer_preserves_whitespace_only_text_chunk() -> None:
    normalizer = StreamEventNormalizer()

    events = normalizer.normalize(
        {
            "event": "on_chat_model_stream",
            "run_id": "answer-run",
            "data": {"chunk": " "},
        }
    )

    assert events[0] == _text_event(
        "assistant_delta",
        "answer-run",
        "on_chat_model_stream",
        " ",
    )


def test_stream_event_normalizer_streams_root_model_with_nested_parent_ids() -> None:
    normalizer = StreamEventNormalizer()

    events = normalizer.normalize(
        {
            "event": "on_chat_model_stream",
            "name": "ChatOpenAI",
            "run_id": "root-run",
            "parent_ids": ["graph-run", "model-chain-run"],
            "metadata": {
                "langgraph_node": "model",
                "langgraph_checkpoint_ns": "model:root-checkpoint",
            },
            "data": {"chunk": "최종 답변입니다."},
        }
    )

    assert events == [
        {
            "kind": "assistant_delta",
            "id": "root-run",
            "sourceEvent": "on_chat_model_stream",
            "name": "ChatOpenAI",
            "runId": "root-run",
            "parentIds": ["graph-run", "model-chain-run"],
            "text": "최종 답변입니다.",
        }
    ]


def test_stream_event_normalizer_keeps_nested_model_text_out_of_answer() -> None:
    normalizer = StreamEventNormalizer()

    stream_events = normalizer.normalize(
        {
            "event": "on_chat_model_stream",
            "name": "model",
            "run_id": "nested-run",
            "parent_ids": ["graph", "editor_docx"],
            "metadata": {
                "langgraph_node": "model",
                "langgraph_checkpoint_ns": "tools:agent-run|model:nested-checkpoint",
            },
            "data": {"chunk": "중간 요약입니다."},
        }
    )
    end_events = normalizer.normalize(
        {
            "event": "on_chat_model_end",
            "name": "model",
            "run_id": "nested-run",
            "parent_ids": ["graph", "editor_docx"],
            "metadata": {
                "langgraph_node": "model",
                "langgraph_checkpoint_ns": "tools:agent-run|model:nested-checkpoint",
            },
            "data": {"output": "ignored duplicate"},
        }
    )

    assert stream_events == []
    assert end_events == []


def test_stream_event_normalizer_ignores_incomplete_tool_call_chunks() -> None:
    events = StreamEventNormalizer().normalize(
        {
            "event": "on_chat_model_stream",
            "run_id": "model-run",
            "data": {
                "chunk": AIMessageChunk(
                    content="",
                    tool_call_chunks=[
                        {
                            "name": None,
                            "args": '"file_path"',
                            "id": None,
                            "index": 0,
                        }
                    ],
                )
            },
        }
    )

    assert events == []


def test_stream_event_normalizer_emits_tool_intent_once_per_call() -> None:
    normalizer = StreamEventNormalizer()
    raw = {
        "event": "on_chat_model_stream",
        "run_id": "model-run",
        "data": {
            "chunk": AIMessageChunk(
                content="",
                tool_call_chunks=[
                        {
                            "name": "read_pdf_file",
                            "args": '{"file_path":"/report.pdf"}',
                            "id": "call_1",
                        "index": 0,
                    }
                ],
            )
        },
    }

    first = normalizer.normalize(raw)
    second = normalizer.normalize(raw)

    assert len(first) == 1
    assert first[0]["name"] == "read_pdf_file"
    assert second == []


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


def test_stream_event_normalizer_preserves_tool_input_for_end_events() -> None:
    normalizer = StreamEventNormalizer()

    normalizer.normalize(
        {
            "event": "on_tool_start",
            "name": "ls",
            "run_id": "tool-run",
            "data": {"input": {"path": "/.agents"}},
        }
    )
    events = normalizer.normalize(
        {
            "event": "on_tool_end",
            "name": "ls",
            "run_id": "tool-run",
            "data": {"output": '["/.agents/skills/"]'},
        }
    )

    assert events[0]["details"]["path"] == "/.agents"
    assert "result" not in events[0]["details"]


def test_stream_event_normalizer_marks_skill_file_reads() -> None:
    normalizer = StreamEventNormalizer()

    start_events = normalizer.normalize(
        {
            "event": "on_tool_start",
            "name": "read_file",
            "run_id": "skill-read-run",
            "data": {
                "input": {"file_path": "/.agents/skills/writing-guide/SKILL.md"}
            },
        }
    )
    end_events = normalizer.normalize(
        {
            "event": "on_tool_end",
            "name": "read_file",
            "run_id": "skill-read-run",
            "data": {"output": "skill contents"},
        }
    )

    assert start_events[0]["label"] == "스킬 읽기"
    assert start_events[0]["message"] == "AGENT가 writing-guide 스킬을 읽습니다."
    assert start_events[0]["details"]["skillName"] == "writing-guide"
    assert end_events[0]["label"] == "스킬 읽기"
    assert end_events[0]["message"] == "AGENT가 writing-guide 스킬을 읽었습니다."
    assert end_events[0]["details"]["skillName"] == "writing-guide"


def test_stream_event_normalizer_keeps_regular_file_reads() -> None:
    events = StreamEventNormalizer().normalize(
        {
            "event": "on_tool_start",
            "name": "read_file",
            "run_id": "read-run",
            "data": {"input": {"file_path": "/report.md"}},
        }
    )

    assert events[0]["label"] == "파일 읽기"
    assert events[0]["message"] == "AGENT가 파일 읽기를 시작합니다."
    assert "skillName" not in events[0]["details"]


def test_stream_event_normalizer_maps_middleware_display_names() -> None:
    events = StreamEventNormalizer().normalize(
        {
            "event": "on_chain_end",
            "name": "PatchToolCallsMiddleware.before_agent",
            "run_id": "middleware-run",
            "data": {"output": {}},
        }
    )

    assert events == []


def test_stream_event_normalizer_maps_office_read_guard_middleware_display() -> None:
    events = StreamEventNormalizer().normalize(
        {
            "event": "on_chain_start",
            "name": "OfficeBinaryReadGuardMiddleware.before_agent",
            "run_id": "office-read-guard-run",
            "data": {"input": {}},
        }
    )

    assert events[0]["type"] == "middleware"
    assert events[0]["label"] == "문서 읽기 보호"
    assert events[0]["message"] == "AGENT가 문서 읽기 방식을 확인합니다."


def test_stream_event_normalizer_maps_skills_middleware_metadata() -> None:
    events = StreamEventNormalizer().normalize(
        {
            "event": "on_chain_end",
            "name": "SkillsMiddleware.before_agent",
            "run_id": "skills-run",
            "data": {
                "output": {
                    "skills_metadata": [
                        {
                            "name": "writing-guide",
                            "description": "Use this guide for writing requests.",
                            "path": "/.agents/skills/writing-guide/SKILL.md",
                        }
                    ]
                }
            },
        }
    )

    assert events == []


def test_stream_event_normalizer_hides_unknown_middleware_names() -> None:
    events = StreamEventNormalizer().normalize(
        {
            "event": "on_chain_end",
            "name": "SomeNewMiddleware.before_agent",
            "run_id": "middleware-run",
            "data": {"output": {}},
        }
    )

    assert events == []


def test_stream_event_normalizer_does_not_parse_raw_tool_message_repr() -> None:
    events = StreamEventNormalizer().normalize(
        {
            "event": "on_tool_end",
            "name": "write_file",
            "run_id": "tool-run",
            "data": {
                "output": (
                    "content='Cannot write to /2026-05-06_diary.txt because it "
                    "already exists.' name='write_file' "
                    "tool_call_id='chatcmpl-tool-1'"
                )
            },
        }
    )

    assert "result" not in events[0]["details"]


def test_stream_event_normalizer_summarizes_tool_message_artifact() -> None:
    events = StreamEventNormalizer().normalize(
        {
            "event": "on_tool_end",
            "name": "read_pdf_file",
            "run_id": "tool-run",
            "data": {
                "output": ToolMessage(
                    content="raw content should not win",
                    tool_call_id="call-1",
                    artifact={
                        "filename": "report.pdf",
                        "page_count": 7,
                        "evidence": {"page_2": "matched evidence"},
                        "scanned_pages": 5,
                        "is_sufficient": True,
                    },
                )
            },
        }
    )

    assert events[0]["details"]["filename"] == "report.pdf"
    assert events[0]["details"]["pageCount"] == 7
    assert events[0]["details"]["evidence"] == {"page_2": "matched evidence"}
    assert events[0]["details"]["scannedPages"] == 5
    assert events[0]["details"]["isSufficient"] is True
    assert "result" not in events[0]["details"]


def test_stream_event_normalizer_summarizes_edit_agent_command_without_raw_messages() -> None:
    events = StreamEventNormalizer().normalize(
        {
            "event": "on_chain_end",
            "name": "editor_docx",
            "run_id": "agent-run",
            "data": {
                "output": Command(
                    update={
                        "messages": [AIMessage(content="final answer")],
                        "file_id": "file_001",
                        "filename": "report.pdf",
                        "page_count": 3,
                    },
                    goto="editor_docx",
                )
            },
        }
    )

    assert events[0]["type"] == "agent_step"
    assert events[0]["label"] == "DOCX 에이전트"
    assert events[0]["message"] == "AGENT가 DOCX 작업을 완료했습니다."
    assert events[0]["details"]["fileId"] == "file_001"
    assert events[0]["details"]["filename"] == "report.pdf"
    assert events[0]["details"]["pageCount"] == 3
    assert events[0]["details"]["next"] == "editor_docx"
    assert "messages" not in events[0]["details"]
    assert "result" not in events[0]["details"]


def test_stream_event_normalizer_maps_edit_agent_names() -> None:
    events = StreamEventNormalizer().normalize(
        {
            "event": "on_chain_start",
            "name": "editor_xlsx",
            "run_id": "office-run",
            "data": {"input": {"name": "editor_xlsx", "file_id": "file_001"}},
        }
    )

    assert events[0]["type"] == "agent_step"
    assert events[0]["label"] == "XLSX 에이전트"
    assert events[0]["message"] == "AGENT가 XLSX 작업을 시작합니다."
    assert events[0]["details"]["agentName"] == "editor_xlsx"


def test_stream_event_normalizer_maps_office_worker_tool_names() -> None:
    normalizer = StreamEventNormalizer()

    today_events = normalizer.normalize(
        {
            "event": "on_tool_start",
            "name": "get_today",
            "run_id": "today-run",
            "data": {"input": {}},
        }
    )
    read_events = normalizer.normalize(
        {
            "event": "on_tool_start",
            "name": "read_xlsx_file",
            "run_id": "xlsx-read-run",
            "data": {"input": {"file_id": "file_001"}},
        }
    )
    edit_events = normalizer.normalize(
        {
            "event": "on_tool_start",
            "name": "edit_pptx",
            "run_id": "pptx-edit-run",
            "data": {"input": {"file_id": "file_002"}},
        }
    )

    assert today_events[0]["label"] == "오늘 날짜 확인"
    assert today_events[0]["message"] == "AGENT가 오늘 날짜를 확인합니다."
    assert "get_today" not in today_events[0]["message"]
    assert read_events[0]["label"] == "XLSX 읽기"
    assert read_events[0]["message"] == "AGENT가 XLSX 읽기 작업을 시작합니다."
    assert edit_events[0]["label"] == "PPTX 수정"
    assert edit_events[0]["message"] == "AGENT가 PPTX 수정 작업을 시작합니다."
    assert "read_xlsx_file" not in read_events[0]["message"]
    assert "edit_pptx" not in edit_events[0]["message"]


def test_stream_event_normalizer_keeps_unknown_tool_display_fallback() -> None:
    events = StreamEventNormalizer().normalize(
        {
            "event": "on_tool_start",
            "name": "unknown_tool",
            "run_id": "unknown-tool-run",
            "data": {"input": {}},
        }
    )

    assert events[0]["label"] == "unknown_tool"
    assert events[0]["message"] == "AGENT가 unknown_tool 작업을 시작합니다."


def test_stream_event_normalizer_marks_write_file_parent_directory_creation(
    tmp_path,
) -> None:
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
    assert (
        start_events[0]["message"]
        == "AGENT가 필요한 폴더를 만들고 파일 작성을 시작합니다."
    )
    assert start_events[0]["details"]["createsParentDirectory"] is True
    assert start_events[0]["details"]["parentPath"] == "/code"

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
    assert (
        end_events[0]["message"]
        == "AGENT가 필요한 폴더를 만들고 파일 작성을 완료했습니다."
    )
    assert end_events[0]["details"]["parentPath"] == "/code"
    assert end_events[0]["details"]["parentDirectoryCreated"] is True


def test_stream_event_normalizer_does_not_mark_root_or_existing_write_parent(
    tmp_path,
) -> None:
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
    assert "createsParentDirectory" not in root_file_events[0]["details"]
    assert existing_parent_events[0]["message"] == "AGENT가 파일 작성을 시작합니다."
    assert "createsParentDirectory" not in existing_parent_events[0]["details"]


def test_stream_event_normalizer_ignores_write_file_paths_outside_workspace(
    tmp_path,
) -> None:
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
    assert "createsParentDirectory" not in events[0]["details"]


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

    assert first_events[0] == _text_event(
        "assistant_delta",
        "model-run",
        "on_chat_model_stream",
        "I will now formulate the final response",
    )
    assert second_events[0] == _text_event(
        "assistant_delta",
        "model-run",
        "on_chat_model_stream",
        ". 전문 답변입니다.",
    )


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
        _text_event(
            "think_delta",
            "model-run",
            "on_chat_model_stream",
            "I should be concise.",
        ),
        _text_event(
            "assistant_delta",
            "model-run",
            "on_chat_model_stream",
            "간단히 답변하겠습니다.",
        ),
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
