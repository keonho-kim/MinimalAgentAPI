import asyncio
import json
from typing import Any
from uuid import uuid4

from fastapi.encoders import jsonable_encoder
from langchain_core.load.dump import dumps as langchain_dumps

from minial_agent.agents.core.agent_registry import AgentRegistry
from minial_agent.common.queue import InMemoryQueue

from .schema import ChatRequest


class ChatService:
    def __init__(
        self,
        registry: AgentRegistry | None = None,
        queue: InMemoryQueue | None = None,
    ) -> None:
        self.registry = registry or AgentRegistry()
        self.queue = queue or InMemoryQueue()

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

            async for event in agent.astream_events(
                {"messages": messages},
                config=config,
                version="v2",
            ):
                await self.queue.rpush(
                    queue_key,
                    {
                        "event": "langgraph",
                        "data": event,
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

    def _json_dumps(self, data: Any) -> str:
        try:
            encoded = jsonable_encoder(data)
            return json.dumps(encoded, ensure_ascii=False)
        except Exception:
            return langchain_dumps(data, ensure_ascii=False)

    def _queue_key(self, stream_id: str) -> str:
        return f"chat:{stream_id}"


chat_service = ChatService()
