import asyncio

from minial_agent.common.queue import InMemoryQueue


def test_in_memory_queue_fifo() -> None:
    async def run() -> None:
        queue = InMemoryQueue()

        await queue.rpush("test", "first")
        await queue.rpush("test", "second")

        assert await queue.lpop("test") == "first"
        assert await queue.lpop("test") == "second"

    asyncio.run(run())


def test_in_memory_queue_timeout() -> None:
    async def run() -> None:
        queue = InMemoryQueue()

        assert await queue.lpop("missing", timeout=0.01) is None

    asyncio.run(run())


def test_in_memory_queue_backpressure() -> None:
    async def run() -> None:
        queue = InMemoryQueue(max_size=1)

        await queue.rpush("test", "first")
        blocked_push = asyncio.create_task(queue.rpush("test", "second"))
        await asyncio.sleep(0)

        assert not blocked_push.done()
        assert await queue.lpop("test") == "first"

        await asyncio.wait_for(blocked_push, timeout=0.1)
        assert await queue.lpop("test") == "second"

    asyncio.run(run())
