import pickle
from typing import Any


class RedisQueue:
    def __init__(self, redis_client: Any, key_prefix: str = "minial-agent") -> None:
        self.redis_client = redis_client
        self.key_prefix = key_prefix

    async def rpush(self, queue_key: str, item: Any) -> None:
        await self.redis_client.rpush(self._key(queue_key), pickle.dumps(item))

    async def lpop(self, queue_key: str, timeout: float | None = None) -> Any | None:
        key = self._key(queue_key)

        if timeout is None:
            item = await self.redis_client.lpop(key)
            return pickle.loads(item) if item is not None else None

        result = await self.redis_client.blpop(key, timeout=timeout)
        if result is None:
            return None

        _, item = result
        return pickle.loads(item)

    async def delete(self, queue_key: str) -> None:
        await self.redis_client.delete(self._key(queue_key))

    def _key(self, queue_key: str) -> str:
        return f"{self.key_prefix}:{queue_key}"
