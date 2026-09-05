import asyncio
import logging
from asyncio import Event as AsyncEvent
from contextlib import asynccontextmanager

from codeflow_common.kafka import KafkaEventPublisher, LogEventPublisher
from codeflow_common.metrics import instrument_app
from codeflow_common.outbox import run_outbox_worker
from codeflow_common.redis import close_redis, create_redis
from codeflow_common.tracing import setup_tracing
from fastapi import FastAPI
from sqlalchemy import select

from ci_service.api.routes import health, pipelines
from ci_service.core.config import settings
from ci_service.db.session import async_session_factory
from ci_service.events.consumer import run_consumer
from ci_service.events.publishers import publish_finished
from ci_service.models.pipeline import Build, OutboxEvent, Pipeline
from ci_service.services import runner  # noqa: F401 (used in lifespan)

logger = logging.getLogger("ci-service")


async def on_pipeline_finished(pipeline_id: int) -> None:
    """执行完成后发 pipeline.finished 事件。"""
    async with async_session_factory() as session:
        pipeline = await session.get(Pipeline, pipeline_id)
        if pipeline is None:
            return
        result = await session.execute(
            select(Build).where(Build.pipeline_id == pipeline_id).order_by(Build.id.desc()).limit(1)
        )
        build = result.scalar_one_or_none()
        await publish_finished(session, pipeline, build.logs if build else "")
        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis = await create_redis(settings.REDIS_URL)
    stop = AsyncEvent()
    runner.start_workers(stop, on_pipeline_finished)

    publisher: KafkaEventPublisher | LogEventPublisher
    if settings.KAFKA_ENABLED:
        publisher = KafkaEventPublisher(settings.KAFKA_BOOTSTRAP_SERVERS, client_id="ci-service")
        try:
            await publisher.start()
        except Exception as exc:  # pragma: no cover
            logger.warning("kafka start failed, fallback to log publisher: %s", exc)
            publisher = LogEventPublisher()
    else:
        publisher = LogEventPublisher()

    tasks = [
        asyncio.create_task(
            run_outbox_worker(
                async_session_factory,
                OutboxEvent,
                publisher,
                stop,
                settings.OUTBOX_POLL_INTERVAL_SECONDS,
            )
        )
    ]
    if settings.KAFKA_ENABLED:
        tasks.append(asyncio.create_task(run_consumer(stop, on_pipeline_finished)))

    yield
    stop.set()
    await runner.stop_workers()
    for task in tasks:
        await task
    if settings.KAFKA_ENABLED and isinstance(publisher, KafkaEventPublisher):
        await publisher.stop()
    await close_redis(redis)


def create_app() -> FastAPI:
    app = FastAPI(title="CodeFlow CI Service", version="0.1.0", lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(pipelines.router, prefix=settings.API_V1_PREFIX)
    instrument_app(app, "ci-service")
    if settings.OTEL_ENABLED:
        setup_tracing(app, "ci-service", settings.OTEL_ENDPOINT)

    return app


app = create_app()
