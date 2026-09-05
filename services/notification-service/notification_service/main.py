import asyncio
import logging
from asyncio import Event as AsyncEvent
from contextlib import asynccontextmanager

from codeflow_common.metrics import instrument_app
from codeflow_common.tracing import setup_tracing
from fastapi import FastAPI

from notification_service.api.routes import health, notifications
from notification_service.core.config import settings
from notification_service.events.consumer import run_consumer

logger = logging.getLogger("notification-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop = AsyncEvent()
    tasks = []
    if settings.KAFKA_ENABLED:
        tasks.append(asyncio.create_task(run_consumer(stop)))
    else:
        logger.warning("KAFKA_ENABLED=false, consumer not started")

    yield
    stop.set()
    for task in tasks:
        await task


def create_app() -> FastAPI:
    app = FastAPI(title="CodeFlow Notification Service", version="0.1.0", lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(notifications.router, prefix=settings.API_V1_PREFIX)
    instrument_app(app, "notification-service")
    if settings.OTEL_ENABLED:
        setup_tracing(app, "notification-service", settings.OTEL_ENDPOINT)

    return app


app = create_app()
