import asyncio
import json
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from langchain_core.load.dump import dumps as langchain_dumps
from langgraph.types import Command, Interrupt

from minial_agent.agents.core.agent_registry import AgentRegistry
from minial_agent.common.locks import WorkspaceLockManager, workspace_lock_manager
from minial_agent.common.queue import InMemoryQueue
from minial_agent.constants.user_request import USER_REQUEST
from minial_agent.integrations.upload import ensure_upload_workspace, get_workspace_root

from minial_agent.api.agent.events import StreamEventNormalizer
from minial_agent.api.agent.schema import ChatRequest, HitlResumeRequest, HitlResumeResponse


@dataclass(frozen=True)
class PendingHitl:
    stream_id: str
    user_id: str
    uuid: str
    thread_id: str
    request: ChatRequest
    payload: dict[str, Any]


class ChatService:
    def __init__(
        self,
        registry: AgentRegistry | None = None,
        queue: InMemoryQueue | None = None,
        lock_manager: WorkspaceLockManager | None = None,
    ) -> None:
        self.registry = registry or AgentRegistry()
        self.queue = queue or InMemoryQueue()
        self.lock_manager = lock_manager or workspace_lock_manager
        self._normalizers: dict[str, StreamEventNormalizer] = {}
        self._pending_hitl: dict[str, PendingHitl] = {}

    def enqueue_chat(self, request: ChatRequest) -> str:
        stream_id = str(uuid4())
        asyncio.create_task(self._run_agent(stream_id=stream_id, request=request))
        return stream_id

    async def stream_events(self, stream_id: str):
        queue_key = self._queue_key(stream_id)

        while True:
            item = await self.queue.lpop(queue_key, timeout=15)

            if item is None:
                yield ": keep-alive\n\n"
                continue

            event_name = item["event"]
            data = self._json_dumps(item["data"])
            yield f"event: {event_name}\ndata: {data}\n\n"

            if event_name in {"done", "error"}:
                await self.queue.delete(queue_key)
                break

    async def _run_agent(self, stream_id: str, request: ChatRequest) -> None:
        queue_key = self._queue_key(stream_id)

        try:
            await self.queue.rpush(
                queue_key,
                {
                    "event": "queued",
                    "data": {"workspace_key": request.user_id},
                },
            )

            async with self.lock_manager.lock(request.user_id):
                agent = self.registry.get_agent(
                    user_id=request.user_id,
                    uuid=request.uuid,
                )

                messages = [message.model_dump() for message in request.chat_history]
                messages.append(
                    {
                        "role": "user",
                        "content": USER_REQUEST.format(user_query=request.message),
                    }
                )

                config = {
                    "configurable": {
                        "thread_id": f"{request.user_id}:{request.uuid}",
                    }
                }

                normalizer = self._get_normalizer(
                    stream_id,
                    workspace_root=self._get_workspace_files_root(request),
                )

                interrupted = await self._stream_agent_events(
                    stream_id=stream_id,
                    agent=agent,
                    input_value={"messages": messages},
                    config=config,
                    normalizer=normalizer,
                    request=request,
                )

            if not interrupted:
                self._normalizers.pop(stream_id, None)
                await self.queue.rpush(queue_key, {"event": "done", "data": {}})
        except Exception as exc:
            await self.queue.rpush(
                queue_key,
                {
                    "event": "error",
                    "data": {"message": str(exc)},
                },
            )
            self._pending_hitl.pop(stream_id, None)
            self._normalizers.pop(stream_id, None)

    async def resume_hitl(
        self,
        *,
        stream_id: str,
        request: HitlResumeRequest,
    ) -> HitlResumeResponse:
        pending = self._pending_hitl.get(stream_id)
        if pending is None:
            raise HTTPException(status_code=404, detail="Pending HITL request not found.")

        asyncio.create_task(
            self._resume_agent(
                pending=pending,
                decisions=[
                    decision.model_dump(exclude_none=True)
                    for decision in request.decisions
                ],
            )
        )
        return HitlResumeResponse(stream_id=stream_id, status="accepted")

    async def _resume_agent(
        self,
        *,
        pending: PendingHitl,
        decisions: list[dict[str, Any]],
    ) -> None:
        queue_key = self._queue_key(pending.stream_id)
        try:
            await self.queue.rpush(
                queue_key,
                {
                    "event": "hitl_resumed",
                    "data": {"stream_id": pending.stream_id, "status": "accepted"},
                },
            )
            async with self.lock_manager.lock(pending.user_id):
                agent = self.registry.get_agent(
                    user_id=pending.user_id,
                    uuid=pending.uuid,
                )
                config = {
                    "configurable": {
                        "thread_id": pending.thread_id,
                    }
                }
                normalizer = self._get_normalizer(
                    pending.stream_id,
                    workspace_root=self._get_workspace_files_root(pending.request),
                )
                interrupted = await self._stream_agent_events(
                    stream_id=pending.stream_id,
                    agent=agent,
                    input_value=Command(resume={"decisions": decisions}),
                    config=config,
                    normalizer=normalizer,
                    request=pending.request,
                )

            if not interrupted:
                self._pending_hitl.pop(pending.stream_id, None)
                self._normalizers.pop(pending.stream_id, None)
                await self.queue.rpush(queue_key, {"event": "done", "data": {}})
        except Exception as exc:
            self._pending_hitl.pop(pending.stream_id, None)
            self._normalizers.pop(pending.stream_id, None)
            await self.queue.rpush(
                queue_key,
                {
                    "event": "error",
                    "data": {"message": str(exc)},
                },
            )

    def _json_dumps(self, data: Any) -> str:
        try:
            encoded = jsonable_encoder(data)
            return json.dumps(encoded, ensure_ascii=False)
        except Exception:
            return langchain_dumps(data, ensure_ascii=False)

    def _queue_key(self, stream_id: str) -> str:
        return f"chat:{stream_id}"

    def _get_normalizer(
        self,
        stream_id: str,
        workspace_root: str | None = None,
    ) -> StreamEventNormalizer:
        if stream_id not in self._normalizers:
            self._normalizers[stream_id] = StreamEventNormalizer(
                workspace_root=workspace_root,
            )

        return self._normalizers[stream_id]

    def _get_workspace_files_root(self, request: ChatRequest) -> str:
        workspace_root = get_workspace_root(request.user_id, request.uuid)
        workspace = ensure_upload_workspace(workspace_root)
        return str(workspace.files_dir)

    async def _stream_agent_events(
        self,
        *,
        stream_id: str,
        agent: Any,
        input_value: Any,
        config: dict[str, Any],
        normalizer: StreamEventNormalizer,
        request: ChatRequest,
    ) -> bool:
        queue_key = self._queue_key(stream_id)
        saw_stream_item = False
        async for event in agent.astream_events(
            input_value,
            config=config,
            version="v2",
        ):
            saw_stream_item = True
            hitl_payload = self._extract_hitl_payload(
                stream_id=stream_id,
                event=event,
            )
            if hitl_payload:
                self._pending_hitl[stream_id] = PendingHitl(
                    stream_id=stream_id,
                    user_id=request.user_id,
                    uuid=request.uuid,
                    thread_id=config["configurable"]["thread_id"],
                    request=request,
                    payload=hitl_payload,
                )
                await self.queue.rpush(
                    queue_key,
                    {
                        "event": "hitl_request",
                        "data": hitl_payload,
                    },
                )
                return True

            for ui_event in normalizer.normalize(event):
                await self.queue.rpush(
                    queue_key,
                    {
                        "event": "agent_ui",
                        "data": ui_event,
                    },
                )
        if not saw_stream_item:
            raise RuntimeError("Agent stream ended without output.")
        return False

    def _extract_hitl_payload(
        self,
        *,
        stream_id: str,
        event: Any,
    ) -> dict[str, Any] | None:
        interrupts = _event_interrupts(event)
        if not interrupts:
            return None

        interrupt = interrupts[0]
        value = _interrupt_value(interrupt)
        if not isinstance(value, dict):
            return None

        actions = _list_value(value.get("action_requests"))
        review_configs = _list_value(value.get("review_configs"))
        normalized_actions = []
        for index, action in enumerate(actions):
            if not isinstance(action, dict):
                continue
            config = review_configs[index] if index < len(review_configs) else {}
            config = config if isinstance(config, dict) else {}
            normalized_actions.append(
                {
                    "name": action.get("name"),
                    "args": action.get("args") or {},
                    "description": action.get("description"),
                    "allowed_decisions": config.get("allowed_decisions") or [],
                }
            )
        return {
            "stream_id": stream_id,
            "actions": normalized_actions,
        }


def _event_interrupts(event: Any) -> list[Any]:
    if not isinstance(event, dict):
        return []

    interrupts = _coerce_interrupts(event.get("interrupts"))
    data = event.get("data")
    if isinstance(data, dict):
        interrupts.extend(_find_interrupts(data))
    return interrupts


def _find_interrupts(value: Any) -> list[Any]:
    if isinstance(value, dict):
        interrupts = value.get("__interrupt__")
        found = _coerce_interrupts(interrupts)
        if found:
            return found
        for child in value.values():
            child_found = _find_interrupts(child)
            if child_found:
                return child_found
    elif isinstance(value, (list, tuple)):
        for child in value:
            found = _find_interrupts(child)
            if found:
                return found
    return []


def _coerce_interrupts(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list | tuple):
        return list(value)
    return [value]


def _interrupt_value(interrupt: Any) -> Any:
    if isinstance(interrupt, Interrupt):
        return interrupt.value
    if isinstance(interrupt, dict):
        return interrupt.get("value")
    return None


def _list_value(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list | tuple) else []


chat_service = ChatService()
