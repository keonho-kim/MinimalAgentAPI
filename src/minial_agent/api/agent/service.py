import asyncio
import json
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from langchain_core.load.dump import dumps as langchain_dumps
from langgraph.types import Command

from minial_agent.agents.core.agent_registry import AgentRegistry
from minial_agent.common.locks import WorkspaceLockManager, workspace_lock_manager
from minial_agent.common.queue import InMemoryQueue
from minial_agent.constants.user_request import USER_REQUEST
from minial_agent.integrations.upload import ensure_upload_workspace, get_workspace_root

from minial_agent.api.agent.events import StreamEventNormalizer
from minial_agent.api.agent.hitl import PendingHitl, extract_hitl_payload
from minial_agent.api.agent.schema import ChatRequest, HitlResumeRequest, HitlResumeResponse


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
        self._auto_approval_scopes: dict[str, set[str]] = {}

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

        decisions = [
            decision.model_dump(exclude_none=True)
            for decision in request.decisions
        ]
        self._record_auto_approval(
            pending=pending,
            decisions=decisions,
            approval_scope=request.approval_scope,
        )

        asyncio.create_task(
            self._resume_agent(
                pending=pending,
                decisions=decisions,
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
            hitl_payload = extract_hitl_payload(
                stream_id=stream_id,
                event=event,
            )
            if hitl_payload:
                if self._is_auto_approved(request=request, hitl_payload=hitl_payload):
                    decisions = [
                        {"type": "approve"}
                        for _action in hitl_payload.get("actions", [])
                    ]
                    await self.queue.rpush(
                        queue_key,
                        {
                            "event": "hitl_resumed",
                            "data": {
                                "stream_id": stream_id,
                                "status": "auto_approved",
                                "approval_scope": hitl_payload.get("approval_scope"),
                            },
                        },
                    )
                    return await self._stream_agent_events(
                        stream_id=stream_id,
                        agent=agent,
                        input_value=Command(resume={"decisions": decisions}),
                        config=config,
                        normalizer=normalizer,
                        request=request,
                    )
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

    def _record_auto_approval(
        self,
        *,
        pending: PendingHitl,
        decisions: list[dict[str, Any]],
        approval_scope: str,
    ) -> None:
        if approval_scope == "once":
            return
        if not decisions or any(decision.get("type") != "approve" for decision in decisions):
            return

        scope = "core" if approval_scope == "core" else pending.payload.get("approval_scope")
        if not isinstance(scope, str) or not scope:
            return

        self._auto_approval_scopes.setdefault(
            self._approval_key(pending.user_id, pending.uuid),
            set(),
        ).add(scope)

    def _is_auto_approved(
        self,
        *,
        request: ChatRequest,
        hitl_payload: dict[str, Any],
    ) -> bool:
        scopes = self._auto_approval_scopes.get(
            self._approval_key(request.user_id, request.uuid),
            set(),
        )
        if "core" in scopes:
            return True

        scope = hitl_payload.get("approval_scope")
        return isinstance(scope, str) and scope in scopes

    def _approval_key(self, user_id: str, uuid: str) -> str:
        return f"{user_id}:{uuid}"

chat_service = ChatService()
