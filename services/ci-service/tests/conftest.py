import asyncio
import os
from collections.abc import AsyncIterator

os.environ.setdefault("CI_SIMULATE", "true")

import ci_service.db.session as db_session
import ci_service.events.consumer as consumer_mod
import ci_service.main as main_mod
import ci_service.services.runner as runner_mod
import pytest
from ci_service.api.deps import get_db
from ci_service.db.base import Base
from ci_service.main import create_app
from ci_service.services import runner
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool


@pytest.fixture
async def app():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    # ASGITransport 不触发 lifespan，后台组件手动接线
    for mod in (db_session, runner_mod, consumer_mod, main_mod):
        mod.async_session_factory = factory
    stop = asyncio.Event()
    runner._queue = asyncio.Queue()  # 清空跨测试残留
    runner.start_workers(stop, main_mod.on_pipeline_finished, concurrency=2)

    async def override_get_db() -> AsyncIterator:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    application = create_app()
    application.dependency_overrides[get_db] = override_get_db
    application.state.test_session_factory = factory
    yield application

    stop.set()
    await runner.stop_workers()
    await engine.dispose()


@pytest.fixture
async def client(app) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def auth_headers() -> dict:
    from ci_service.core.config import settings
    from codeflow_common.security import create_access_token

    token = create_access_token(1, settings.SECRET_KEY)
    return {"Authorization": f"Bearer {token}"}
