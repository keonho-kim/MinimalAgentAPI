import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator


class WorkspaceLockManager:
    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}
        self._guard = asyncio.Lock()

    @asynccontextmanager
    async def lock(self, workspace_key: str) -> AsyncIterator[None]:
        lock = await self._get_lock(workspace_key)
        async with lock:
            yield

    async def _get_lock(self, workspace_key: str) -> asyncio.Lock:
        async with self._guard:
            lock = self._locks.get(workspace_key)
            if lock is None:
                lock = asyncio.Lock()
                self._locks[workspace_key] = lock
            return lock


workspace_lock_manager = WorkspaceLockManager()
