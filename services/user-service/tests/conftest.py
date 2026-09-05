from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from user_service.db.base import Base
from user_service.db.session import get_db
from user_service.main import create_app


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
async def auth_headers(client: AsyncClient) -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={"username": "alice", "email": "alice@example.com", "password": "secret1234"},
    )
    resp = await client.post(
        "/api/v1/auth/login", data={"username": "alice", "password": "secret1234"}
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
