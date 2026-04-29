import asyncio
from collections import defaultdict, deque
from typing import Any


class InMemoryQueue:
    def __init__(self, max_size: int = 1024) -> None:
        self.max_size = max_size
        self._queues: defaultdict[str, deque[Any]] = defaultdict(deque)
        self._condition = asyncio.Condition()

    async def rpush(self, queue_key: str, item: Any) -> None:
        async with self._condition:
            await self._condition.wait_for(
                lambda: len(self._queues[queue_key]) < self.max_size
            )
            self._queues[queue_key].append(item)
            self._condition.notify_all()

    async def lpop(self, queue_key: str, timeout: float | None = None) -> Any | None:
        async with self._condition:
            try:
                await asyncio.wait_for(
                    self._condition.wait_for(lambda: len(self._queues[queue_key]) > 0),
                    timeout=timeout,
                )
            except TimeoutError:
                if not self._queues[queue_key]:
                    self._queues.pop(queue_key, None)
                return None

            item = self._queues[queue_key].popleft()

            if not self._queues[queue_key]:
                self._queues.pop(queue_key, None)

            self._condition.notify_all()
            return item

    async def delete(self, queue_key: str) -> None:
        async with self._condition:
            self._queues.pop(queue_key, None)
            self._condition.notify_all()
