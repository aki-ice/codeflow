"""Kafka Consumer：Consumer Group + 幂等 + 重试 + DLQ。

链路：codeflow.*.events -> 消费 -> notifications 表。
幂等两层：
  1. Redis SETNX processed:{event_id}（第一道闸，快速去重）
  2. notifications.event_id 唯一约束（数据库兜底）
"""

import asyncio
import contextlib
import json
import logging

from codeflow_common.envelope import dlq_for
from codeflow_common.redis import create_redis

from notification_service.core.config import settings
from notification_service.db.session import async_session_factory
from notification_service.models.notification import Notification

logger = logging.getLogger("notification-service.consumer")

CONSUME_TOPICS = (
    "codeflow.user.events",
    "codeflow.project.events",
    "codeflow.issue.events",
)
PROCESSED_TTL_SECONDS = 24 * 3600


async def _already_processed(client, event_id: str) -> bool:
    if client is None:
        return False
    try:
        return not await client.set(f"processed:{event_id}", "1", nx=True, ex=PROCESSED_TTL_SECONDS)
    except Exception as exc:
        logger.warning("idempotency check failed, rely on db constraint: %s", exc)
        return False


async def handle_issue_created(payload: dict, event_id: str) -> None:
    """issue.created -> 给 watchers 生成通知（事件契约：payload.watchers）。"""
    watchers = [int(uid) for uid in payload.get("watchers", [])]
    if not watchers:
        return
    title = f"New Issue #{payload.get('number')}: {payload.get('title', '')}"
    content = f"project={payload.get('project_id')} issue_id={payload.get('issue_id')}"

    async with async_session_factory() as session:
        session.add(
            Notification(
                user_id=watchers[0],
                event_id=event_id,
                title=title,
                content=content,
            )
        )
        # 其余 watchers 不携带 event_id（唯一约束只允许一条），整体幂等由 Redis 键保证
        for uid in watchers[1:]:
            session.add(Notification(user_id=uid, title=title, content=content))
        await session.commit()


async def handle_event(event_type: str, payload: dict, event_id: str) -> None:
    handlers = {
        "issue.created": handle_issue_created,
    }
    handler = handlers.get(event_type)
    if handler is None:
        logger.debug("no handler for %s, skipped", event_type)
        return
    await handler(payload, event_id)


async def _send_to_dlq(topic: str, raw: bytes, error: str) -> None:
    try:
        from aiokafka import AIOKafkaProducer

        producer = AIOKafkaProducer(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS)
        await producer.start()
        try:
            await producer.send_and_wait(
                dlq_for(topic),
                value=raw,
                headers=[("error", error.encode("utf-8")[:200])],
            )
        finally:
            await producer.stop()
        logger.error("message sent to DLQ topic=%s error=%s", dlq_for(topic), error)
    except Exception:
        logger.exception("failed to send message to DLQ")


async def run_consumer(stop: asyncio.Event) -> None:
    from aiokafka import AIOKafkaConsumer

    redis = await create_redis(settings.REDIS_URL)
    while not stop.is_set():
        consumer = AIOKafkaConsumer(
            *CONSUME_TOPICS,
            group_id=settings.CONSUMER_GROUP_ID,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
        )
        try:
            await consumer.start()
            logger.info(
                "kafka consumer started topics=%s group=%s",
                CONSUME_TOPICS,
                settings.CONSUMER_GROUP_ID,
            )
            async for msg in consumer:
                if stop.is_set():
                    break
                raw = msg.value
                try:
                    envelope = json.loads(raw)
                    event_id = envelope["event_id"]
                    event_type = envelope["event_type"]
                    payload = envelope.get("payload", {})
                except Exception:
                    await _send_to_dlq(msg.topic, raw, "malformed envelope")
                    await consumer.commit()
                    continue

                if await _already_processed(redis, event_id):
                    logger.info("duplicate event %s skipped", event_id)
                    await consumer.commit()
                    continue

                ok = False
                last_error = ""
                for attempt in range(1, settings.PROCESS_MAX_RETRIES + 1):
                    try:
                        await handle_event(event_type, payload, event_id)
                        ok = True
                        break
                    except Exception as exc:
                        last_error = str(exc)
                        logger.warning(
                            "process failed event=%s attempt=%s/%s err=%s",
                            event_id,
                            attempt,
                            settings.PROCESS_MAX_RETRIES,
                            exc,
                        )
                        await asyncio.sleep(0.5 * attempt)

                if ok:
                    await consumer.commit()
                else:
                    await _send_to_dlq(msg.topic, raw, last_error)
                    await consumer.commit()
        except Exception as exc:
            logger.warning("consumer connection error: %s, retrying in 5s", exc)
            await asyncio.sleep(5)
        finally:
            with contextlib.suppress(Exception):
                await consumer.stop()
    logger.info("kafka consumer stopped")
