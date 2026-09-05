"""异步重试工具：指数退避 + 随机抖动。

from codeflow_common.retry import async_retry

@async_retry(attempts=3, base_delay=0.2)
async def call_remote(): ...
"""

import asyncio
import functools
import logging
import random
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger("codeflow.retry")


def async_retry(
    attempts: int = 3,
    base_delay: float = 0.2,
    max_delay: float = 5.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    def decorator(fn: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_error: BaseException | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return await fn(*args, **kwargs)
                except exceptions as exc:
                    last_error = exc
                    if attempt == attempts:
                        break
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    delay += random.uniform(0, delay * 0.3)  # 抖动防雪崩
                    logger.warning("retry %s/%s after %.2fs: %s", attempt, attempts, delay, exc)
                    await asyncio.sleep(delay)
            assert last_error is not None
            raise last_error

        return wrapper

    return decorator
