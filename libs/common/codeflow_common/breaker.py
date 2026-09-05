"""异步熔断器（Circuit Breaker）：closed -> open -> half-open -> closed。

防止下游持续故障时上游被拖垮（如 user-service 宕机时 project-service 快速失败）。
"""

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger("codeflow.breaker")


class BreakerOpenError(Exception):
    """熔断打开期间的快速失败。"""


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 10.0,
        half_open_max_calls: int = 3,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self._state = "closed"
        self._failures = 0
        self._opened_at = 0.0
        self._half_open_calls = 0

    @property
    def state(self) -> str:
        if self._state == "open" and time.monotonic() - self._opened_at >= self.recovery_timeout:
            self._state = "half-open"
            self._half_open_calls = 0
        return self._state

    async def call(self, fn: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> Any:
        state = self.state
        if state == "open":
            raise BreakerOpenError(f"circuit {self.name} is open")
        if state == "half-open":
            if self._half_open_calls >= self.half_open_max_calls:
                raise BreakerOpenError(f"circuit {self.name} half-open limit reached")
            self._half_open_calls += 1
        try:
            result = await fn(*args, **kwargs)
        except Exception:
            self._on_failure()
            raise
        self._on_success()
        return result

    def _on_success(self) -> None:
        self._state = "closed"
        self._failures = 0

    def _on_failure(self) -> None:
        self._failures += 1
        if self._state == "half-open" or self._failures >= self.failure_threshold:
            self._trip()

    def _trip(self) -> None:
        self._state = "open"
        self._opened_at = time.monotonic()
        logger.warning("circuit %s OPEN after %s failures", self.name, self._failures)


_breakers: dict[str, CircuitBreaker] = {}


def get_breaker(name: str, **kwargs: Any) -> CircuitBreaker:
    """同名熔断器全局共享（同一进程内）。"""
    if name not in _breakers:
        _breakers[name] = CircuitBreaker(name)
    return _breakers[name]
