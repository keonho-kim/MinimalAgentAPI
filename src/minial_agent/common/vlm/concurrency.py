import os
import threading
from contextlib import contextmanager
from typing import Iterator


DEFAULT_VLM_MAX_CONCURRENCY = 20

_lock = threading.Lock()
_semaphore: tuple[int, threading.BoundedSemaphore] | None = None


def vlm_max_concurrency() -> int:
    raw_value = os.getenv("VLM_MAX_CONCURRENCY", str(DEFAULT_VLM_MAX_CONCURRENCY))
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError("VLM_MAX_CONCURRENCY must be a positive integer.") from exc
    if value < 1:
        raise ValueError("VLM_MAX_CONCURRENCY must be a positive integer.")
    return value


@contextmanager
def vlm_slot() -> Iterator[None]:
    semaphore = _current_semaphore()
    semaphore.acquire()
    try:
        yield
    finally:
        semaphore.release()


def _current_semaphore() -> threading.BoundedSemaphore:
    limit = vlm_max_concurrency()
    global _semaphore
    with _lock:
        if _semaphore is None or _semaphore[0] != limit:
            _semaphore = (limit, threading.BoundedSemaphore(limit))
        return _semaphore[1]
