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

from project_service.api.routes import audit, git, health, issues, projects
from project_service.core.config import settings
from project_service.db.session import async_session_factory
from project_service.models.project import OutboxEvent

logger = logging.getLogger("project-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis = await create_redis(settings.REDIS_URL)
    app.state.redis = redis
    stop = AsyncEvent()
    tasks = []

    if settings.KAFKA_ENABLED:
        publisher: KafkaEventPublisher | LogEventPublisher = KafkaEventPublisher(
            settings.KAFKA_BOOTSTRAP_SERVERS, client_id="project-service"
        )
        try:
            await publisher.start()
        except Exception as exc:  # pragma: no cover
            logger.warning("kafka start failed, fallback to log publisher: %s", exc)
            publisher = LogEventPublisher()
    else:
        publisher = LogEventPublisher()

    tasks.append(
        asyncio.create_task(
            run_outbox_worker(
                async_session_factory,
                OutboxEvent,
                publisher,
                stop,
                settings.OUTBOX_POLL_INTERVAL_SECONDS,
            )
        )
    )

    yield
    stop.set()
    for task in tasks:
        await task
    if settings.KAFKA_ENABLED and isinstance(publisher, KafkaEventPublisher):
        await publisher.stop()
    await close_redis(redis)


def create_app() -> FastAPI:
    app = FastAPI(title="CodeFlow Project Service", version="0.1.0", lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(audit.router, prefix=settings.API_V1_PREFIX)
    app.include_router(projects.router, prefix=settings.API_V1_PREFIX)
    app.include_router(issues.router, prefix=settings.API_V1_PREFIX)
    app.include_router(git.router, prefix=settings.API_V1_PREFIX)
    instrument_app(app, "project-service")
    if settings.OTEL_ENABLED:
        setup_tracing(app, "project-service", settings.OTEL_ENDPOINT)

    return app


app = create_app()
