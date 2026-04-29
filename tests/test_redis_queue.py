import asyncio
from collections import defaultdict, deque

from minial_agent.common.queue import RedisQueue


class FakeRedis:
    def __init__(self) -> None:
        self.queues = defaultdict(deque)

    async def rpush(self, key: str, item: bytes) -> None:
        self.queues[key].append(item)

    async def lpop(self, key: str):
        if not self.queues[key]:
            return None
        return self.queues[key].popleft()

    async def blpop(self, key: str, timeout: float):
        item = await self.lpop(key)
        if item is None:
            return None
        return key, item

    async def delete(self, key: str) -> None:
        self.queues.pop(key, None)


def test_redis_queue_round_trips_python_objects() -> None:
    async def run() -> None:
        redis = FakeRedis()
        queue = RedisQueue(redis_client=redis)

        await queue.rpush("test", {"event": "done", "data": {}})

        assert await queue.lpop("test") == {"event": "done", "data": {}}

    asyncio.run(run())
