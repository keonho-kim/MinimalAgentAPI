import threading
import time

import pytest

from minial_agent.common.vlm import vlm_max_concurrency, vlm_slot


def test_vlm_max_concurrency_reads_env(monkeypatch) -> None:
    monkeypatch.setenv("VLM_MAX_CONCURRENCY", "3")

    assert vlm_max_concurrency() == 3


@pytest.mark.parametrize("value", ["0", "-1", "bad"])
def test_vlm_max_concurrency_rejects_invalid_env(monkeypatch, value: str) -> None:
    monkeypatch.setenv("VLM_MAX_CONCURRENCY", value)

    with pytest.raises(ValueError, match="VLM_MAX_CONCURRENCY"):
        vlm_max_concurrency()


def test_vlm_slot_limits_parallel_access(monkeypatch) -> None:
    monkeypatch.setenv("VLM_MAX_CONCURRENCY", "1")
    entered: list[int] = []

    def run(index: int) -> None:
        with vlm_slot():
            entered.append(index)
            time.sleep(0.02)

    first = threading.Thread(target=run, args=(1,))
    second = threading.Thread(target=run, args=(2,))
    first.start()
    time.sleep(0.005)
    second.start()
    time.sleep(0.005)

    assert entered == [1]

    first.join()
    second.join()
    assert entered == [1, 2]
