from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from user_service.models.user import User


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, user_id: int) -> User | None:
        return await self.db.get(User, user_id)

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_many_by_ids(self, ids: list[int]) -> list[User]:
        if not ids:
            return []
        result = await self.db.execute(select(User).where(User.id.in_(ids)))
        return list(result.scalars().all())

    async def get_many_by_usernames(self, usernames: list[str]) -> list[User]:
        if not usernames:
            return []
        result = await self.db.execute(select(User).where(User.username.in_(usernames)))
        return list(result.scalars().all())

    async def create(self, user: User) -> User:
        self.db.add(user)
        await self.db.flush()
        return user

    async def count(self) -> int:
        result = await self.db.execute(select(func.count(User.id)))
        return int(result.scalar_one())
