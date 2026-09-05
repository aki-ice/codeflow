"""Outbox Pattern 通用实现。

各服务在业务事务内调用 emit() 写入自己的 outbox 表；
worker 轮询投递到 Kafka，成功标记 published，失败重试至上限标记 failed。
"""

import asyncio
import contextlib
import logging
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from codeflow_common.envelope import Event

logger = logging.getLogger("codeflow.outbox")

MAX_RETRIES = 3
BATCH_SIZE = 100


class EventPublisher(Protocol):
    async def publish(self, event: Event) -> None: ...


class OutboxModelProtocol:
    """各服务 OutboxEvent 模型需满足的形状（同一张表结构）。"""


async def emit(
    db: AsyncSession,
    outbox_model: type,
    event_type: str,
    **payload: Any,
) -> Event:
    """业务事务内写 outbox 行（与业务数据原子提交）。"""
    event = Event(event_type=event_type, payload=dict(payload))
    db.add(
        outbox_model(
            event_id=event.event_id,
            topic=event.topic(),
            event_type=event.event_type,
            payload=event.payload,
        )
    )
    return event


async def process_batch(
    session_factory: async_sessionmaker,
    outbox_model: Any,
    publisher: Any,
) -> int:
    processed = 0
    async with session_factory() as session:
        result = await session.execute(
            select(outbox_model)
            .where(
                outbox_model.status == "pending",
                outbox_model.retry_count < MAX_RETRIES,
            )
            .order_by(outbox_model.id)
            .limit(BATCH_SIZE)
        )
        rows = result.scalars().all()
        for row in rows:
            event = Event(
                event_id=row.event_id,
                event_type=row.event_type,
                payload=row.payload,
                timestamp=row.created_at.isoformat() if row.created_at else "",
            )
            try:
                await publisher.publish(event)
            except Exception as exc:
                row.retry_count += 1
                row.last_error = str(exc)[:1024]
                if row.retry_count >= MAX_RETRIES:
                    row.status = "failed"
                logger.warning("outbox publish failed id=%s err=%s", row.event_id, exc)
            else:
                row.status = "published"
                row.published_at = datetime.now(UTC)
                processed += 1
        await session.commit()
    return processed


async def run_outbox_worker(
    session_factory: async_sessionmaker,
    outbox_model: type,
    publisher: Any,
    stop: asyncio.Event,
    poll_interval: float = 1.0,
) -> None:
    logger.info("outbox worker started")
    while not stop.is_set():
        try:
            count = await process_batch(session_factory, outbox_model, publisher)
            if count:
                logger.info("outbox published %s events", count)
        except Exception:
            logger.exception("outbox worker iteration failed")
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=poll_interval)
    logger.info("outbox worker stopped")
