import asyncio
import logging
from asyncio import Event as AsyncEvent
from contextlib import asynccontextmanager

from codeflow_common.kafka import LogEventPublisher
from codeflow_common.metrics import instrument_app
from codeflow_common.outbox import run_outbox_worker
from codeflow_common.tracing import setup_tracing
from fastapi import FastAPI

from ai_service.api.routes import ai, health
from ai_service.core.config import settings
from ai_service.db.session import async_session_factory
from ai_service.models.ai import OutboxEvent

logger = logging.getLogger("ai-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop = AsyncEvent()
    publisher = LogEventPublisher()
    tasks = [
        asyncio.create_task(
            run_outbox_worker(async_session_factory, OutboxEvent, publisher, stop, 1.0)
        )
    ]
    yield
    stop.set()
    for task in tasks:
        await task


def create_app() -> FastAPI:
    app = FastAPI(title="CodeFlow AI Service", version="0.1.0", lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(ai.router, prefix=settings.API_V1_PREFIX)

    # 插桩必须在应用启动前（会添加中间件）
    instrument_app(app, "ai-service")
    if settings.OTEL_ENABLED:
        setup_tracing(app, "ai-service", settings.OTEL_ENDPOINT)
    return app


app = create_app()
