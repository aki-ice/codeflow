import asyncio
import contextlib

import pytest
from codeflow_common.breaker import CircuitBreaker
from codeflow_common.idempotency import with_idempotency
from codeflow_common.retry import async_retry


async def test_retry_eventually_succeeds():
    calls = {"n": 0}

    @async_retry(attempts=3, base_delay=0.01, exceptions=(RuntimeError,))
    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("transient")
        return "ok"

    assert await flaky() == "ok"
    assert calls["n"] == 3


async def test_retry_exhausts():
    @async_retry(attempts=2, base_delay=0.01, exceptions=(RuntimeError,))
    async def always_fail():
        raise RuntimeError("down")

    import pytest

    with pytest.raises(RuntimeError):
        await always_fail()


async def test_breaker_opens_after_threshold():
    breaker = CircuitBreaker("test-svc", failure_threshold=2, recovery_timeout=0.05)

    async def fail():
        raise RuntimeError("x")

    for _ in range(2):
        with contextlib.suppress(RuntimeError):
            await breaker.call(fail)
    assert breaker.state == "open"

    # open: fail fast
    with pytest.raises(Exception) as exc_info:  # noqa: B017
        await breaker.call(fail)
    assert not isinstance(exc_info.value, asyncio.CancelledError)

    # 恢复窗口后 half-open，成功则闭合
    await asyncio.sleep(0.06)
    assert breaker.state == "half-open"
    assert await breaker.call(lambda: _ok()) == "ok"
    assert breaker.state == "closed"


async def _ok():
    return "ok"


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None):
        self.store[key] = value


async def test_idempotency_replays_same_response():
    from codeflow_common.redis import Cache

    cache = Cache(FakeRedis())
    calls = {"n": 0}

    async def execute():
        calls["n"] += 1
        return {"id": 42, "name": "demo"}

    r1 = await with_idempotency(cache, "key-1", execute)
    r2 = await with_idempotency(cache, "key-1", execute)
    assert r1.replayed is False
    assert r2.replayed is True
    assert r2.response == {"id": 42, "name": "demo"}
    assert calls["n"] == 1


async def test_idempotency_no_key_executes_directly():
    from codeflow_common.redis import Cache

    cache = Cache(FakeRedis())
    result = await with_idempotency(cache, None, lambda: _ok())
    assert result is None
