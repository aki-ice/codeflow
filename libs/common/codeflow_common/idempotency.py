"""API 幂等键：客户端带 Idempotency-Key 头的 POST 不重复执行。

- Redis SETNX 抢占，值缓存响应快照（TTL 内重放）
- Redis 不可用降级为直接执行（至少不丢请求）
"""

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from codeflow_common.redis import Cache

logger = logging.getLogger("codeflow.idempotency")

DEFAULT_TTL = 24 * 3600


class IdempotencyResult:
    def __init__(self, response: Any, replayed: bool) -> None:
        self.response = response
        self.replayed = replayed


async def with_idempotency(
    cache: Cache,
    key: str | None,
    execute: Callable[[], Awaitable[Any]],
    ttl: int = DEFAULT_TTL,
) -> IdempotencyResult | None:
    """key 为 None（客户端未提供）时直接执行，返回 None 由调用方处理。"""
    if not key:
        return None
    stored = await cache.get(f"idempotency:{key}")
    if stored is not None:
        try:
            data = json.loads(stored)
            logger.info("idempotency replay: %s", key)
            return IdempotencyResult(data, replayed=True)
        except json.JSONDecodeError:
            logger.warning("idempotency cache corrupt for %s, re-executing", key)

    response = await execute()
    await cache.set(
        f"idempotency:{key}",
        response.model_dump_json()
        if hasattr(response, "model_dump_json")
        else json.dumps(response, default=str),
        ttl=ttl,
    )
    return IdempotencyResult(response, replayed=False)
