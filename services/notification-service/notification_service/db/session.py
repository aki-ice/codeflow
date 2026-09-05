from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from notification_service.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DB_ECHO, pool_pre_ping=True)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db():
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
