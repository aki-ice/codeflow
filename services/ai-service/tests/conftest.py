from collections.abc import AsyncIterator

import pytest
from ai_service.api.deps import get_db
from ai_service.db.base import Base
from ai_service.main import create_app
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
    await engine.dispose()


@pytest.fixture
async def client(app) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def auth_headers() -> dict:
    from ai_service.core.config import settings
    from codeflow_common.security import create_access_token

    token = create_access_token(1, settings.SECRET_KEY)
    return {"Authorization": f"Bearer {token}"}
