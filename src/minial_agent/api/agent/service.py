import asyncio
import json
from typing import Any
from uuid import uuid4

from fastapi.encoders import jsonable_encoder
from langchain_core.load.dump import dumps as langchain_dumps

from minial_agent.agents.core.agent_registry import AgentRegistry
from minial_agent.common.locks import WorkspaceLockManager, workspace_lock_manager
from minial_agent.common.queue import InMemoryQueue
from minial_agent.integrations.upload import ensure_upload_workspace, get_workspace_root

from .events import StreamEventNormalizer
from .schema import ChatRequest


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
                messages.append({"role": "user", "content": request.message})

                config = {
                    "configurable": {
                        "thread_id": f"{request.user_id}:{request.uuid}",
                    }
                }

                normalizer = self._get_normalizer(
                    stream_id,
                    workspace_root=self._get_workspace_files_root(request),
                )

                async for event in agent.astream_events(
                    {"messages": messages},
                    config=config,
                    version="v2",
                ):
                    for ui_event in normalizer.normalize(event):
                        await self.queue.rpush(
                            queue_key,
                            {
                                "event": "agent_ui",
                                "data": ui_event,
                            },
                        )

            await self.queue.rpush(queue_key, {"event": "done", "data": {}})
        except Exception as exc:
            await self.queue.rpush(
                queue_key,
                {
                    "event": "error",
                    "data": {"message": str(exc)},
                },
            )
        finally:
            self._normalizers.pop(stream_id, None)

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


chat_service = ChatService()
