import os
from collections.abc import AsyncIterator

os.environ.setdefault("GITHUB_WEBHOOK_SECRET", "test-webhook-secret")

import pytest
from httpx import ASGITransport, AsyncClient
from project_service.api.deps import get_db, set_user_client
from project_service.db.base import Base
from project_service.main import create_app
from project_service.services.user_client import FakeUserClient
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

    async def override_get_db() -> AsyncIterator:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    set_user_client(FakeUserClient())
    application = create_app()
    application.dependency_overrides[get_db] = override_get_db
    application.state.test_session_factory = factory
    yield application
    # 重置跨事件循环的全局资源
    import project_service.api.deps as deps

    deps._redis = None
    await engine.dispose()


@pytest.fixture
async def client(app) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def auth_headers() -> dict:
    """project-service 不签发 token，直接用共享密钥造一个（与 user-service 同算法）。"""
    from codeflow_common.security import create_access_token
    from project_service.core.config import settings

    token = create_access_token(1, settings.SECRET_KEY)
    return {"Authorization": f"Bearer {token}"}
