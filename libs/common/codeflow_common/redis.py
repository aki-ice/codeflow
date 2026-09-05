"""Redis 工具：Cache Aside（防击穿/雪崩）、限流、分布式锁。连接失败自动降级。"""

import asyncio
import json
import logging
import random
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger("codeflow.redis")


async def create_redis(url: str) -> aioredis.Redis | None:
    try:
        client = aioredis.from_url(url, decode_responses=True)
        await client.ping()
        return client
    except Exception as exc:
        logger.warning("redis unavailable, degraded mode: %s", exc)
        return None


async def close_redis(client: aioredis.Redis | None) -> None:
    if client is not None:
        await client.aclose()


class DistributedLock:
    def __init__(self, client: aioredis.Redis | None) -> None:
        self.client = client

    async def acquire(self, name: str, ttl: int = 30) -> str | None:
        if self.client is None:
            return None
        token = uuid.uuid4().hex
        ok = await self.client.set(f"lock:{name}", token, nx=True, ex=ttl)
        return token if ok else None

    async def release(self, name: str, token: str) -> None:
        if self.client is None:
            return
        current = await self.client.get(f"lock:{name}")
        if current == token:
            await self.client.delete(f"lock:{name}")


class Cache:
    def __init__(self, client: aioredis.Redis | None, ttl_seconds: int = 60) -> None:
        self.client = client
        self.ttl_seconds = ttl_seconds

    async def get(self, key: str) -> Any | None:
        if self.client is None:
            return None
        try:
            return await self.client.get(key)
        except Exception as exc:
            logger.warning("cache get failed: %s", exc)
            return None

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        if self.client is None:
            return
        base_ttl = ttl or self.ttl_seconds
        jittered = int(base_ttl * random.uniform(0.8, 1.2)) or 1
        try:
            await self.client.set(key, value, ex=jittered)
        except Exception as exc:
            logger.warning("cache set failed: %s", exc)

    async def delete(self, *keys: str) -> None:
        if self.client is None or not keys:
            return
        try:
            await self.client.delete(*keys)
        except Exception as exc:
            logger.warning("cache delete failed: %s", exc)

    async def get_or_set(self, key: str, builder: Callable[[], Awaitable[Any]]) -> Any:
        """Cache Aside + 分布式锁防击穿。"""
        cached = await self.get(key)
        if cached is not None:
            return json.loads(cached)

        lock = DistributedLock(self.client)
        token = await lock.acquire(f"cache:{key}", ttl=10)
        if token is None:
            await asyncio.sleep(0.05)
            cached = await self.get(key)
            if cached is not None:
                return json.loads(cached)
            return await builder()

        try:
            value = await builder()
            await self.set(
                key, value.model_dump_json() if hasattr(value, "model_dump_json") else value
            )
            return value
        finally:
            await lock.release(f"cache:{key}", token)


class RateLimiter:
    """INCR + EXPIRE 每分钟限流，Redis 不可用时放行。"""

    def __init__(self, client: aioredis.Redis | None) -> None:
        self.client = client

    async def check(self, key: str, limit: int) -> bool:
        if self.client is None:
            return True
        try:
            full_key = f"rate_limit:{key}"
            count = await self.client.incr(full_key)
            if count == 1:
                await self.client.expire(full_key, 60)
            return int(count) <= limit
        except Exception as exc:
            logger.warning("rate limit check failed: %s", exc)
            return True
