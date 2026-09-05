"""git.push 消费者：创建 Pipeline/Build 并入队执行。

幂等：同一 (repository, commit_sha, branch) 的 git.push 不重复建 Pipeline。
"""

import asyncio
import contextlib
import json
import logging

from codeflow_common.envelope import dlq_for
from codeflow_common.redis import create_redis
from sqlalchemy import select

from ci_service.core.config import settings
from ci_service.db.session import async_session_factory
from ci_service.models.pipeline import Build, OutboxEvent, Pipeline
from ci_service.services import runner

logger = logging.getLogger("ci-service.consumer")


async def handle_git_push(payload: dict, event_id: str) -> None:
    repository = payload.get("repository", "")
    branch = payload.get("branch", "main")
    commit_sha = payload.get("commit_sha", "")

    async with async_session_factory() as session:
        # 幂等：同仓库+commit+branch 已有 pipeline 则跳过
        existing = await session.execute(
            select(Pipeline).where(
                Pipeline.repository == repository,
                Pipeline.commit_sha == commit_sha,
                Pipeline.branch == branch,
            )
        )
        if existing.scalar_one_or_none():
            logger.info("duplicate git.push %s/%s@%s skipped", repository, branch, commit_sha[:8])
            return

        pipeline = Pipeline(
            project_id=int(payload.get("project_id", 0)),
            repository_id=payload.get("repository_id"),
            repository=repository,
            commit_sha=commit_sha,
            branch=branch,
            status="pending",
            trigger_type="webhook",
        )
        session.add(pipeline)
        await session.flush()
        build = Build(pipeline_id=pipeline.id, status="pending", logs="")
        session.add(build)
        await session.flush()

        from codeflow_common.outbox import emit

        await emit(
            session,
            OutboxEvent,
            "pipeline.created",
            pipeline_id=pipeline.id,
            project_id=pipeline.project_id,
            repository=repository,
            branch=branch,
            commit_sha=commit_sha,
        )
        await session.commit()

    runner.enqueue(pipeline.id)
    logger.info("pipeline %s enqueued for %s@%s", pipeline.id, repository, branch)


async def handle_event(event_type: str, payload: dict, event_id: str) -> None:
    handlers = {"git.push": handle_git_push}
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
                dlq_for(topic), value=raw, headers=[("error", error.encode()[:200])]
            )
        finally:
            await producer.stop()
    except Exception:
        logger.exception("failed to send to DLQ")


async def run_consumer(stop: asyncio.Event, on_finished) -> None:
    from aiokafka import AIOKafkaConsumer

    redis = await create_redis(settings.REDIS_URL)
    if redis is not None:
        await redis.aclose()

    while not stop.is_set():
        consumer = AIOKafkaConsumer(
            "codeflow.git.events",
            group_id=settings.CONSUMER_GROUP_ID,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
        )
        try:
            await consumer.start()
            logger.info("ci consumer started, group=%s", settings.CONSUMER_GROUP_ID)
            async for msg in consumer:
                if stop.is_set():
                    break
                try:
                    envelope = json.loads(msg.value)
                    await handle_event(
                        envelope["event_type"], envelope.get("payload", {}), envelope["event_id"]
                    )
                except Exception as exc:
                    logger.warning("process failed: %s, sending to DLQ", exc)
                    await _send_to_dlq(msg.topic, msg.value, str(exc))
                await consumer.commit()
        except Exception as exc:
            logger.warning("consumer connection error: %s, retrying in 5s", exc)
            await asyncio.sleep(5)
        finally:
            with contextlib.suppress(Exception):
                await consumer.stop()
