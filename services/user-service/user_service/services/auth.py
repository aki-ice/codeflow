from codeflow_common.outbox import emit
from codeflow_common.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)

from user_service.core.config import settings
from user_service.models.audit import AuditLog
from user_service.models.user import OutboxEvent, User
from user_service.repositories.user import UserRepository


class AuthError(Exception):
    pass


class AuthService:
    def __init__(self, db) -> None:
        self.users = UserRepository(db)
        self.db = db

    async def register(self, username: str, email: str, password: str) -> User:
        if await self.users.get_by_username(username):
            raise AuthError("username already exists")
        if await self.users.get_by_email(email):
            raise AuthError("email already exists")
        user = User(username=username, email=email, password_hash=hash_password(password))
        user = await self.users.create(user)
        await emit(self.db, OutboxEvent, "user.created", user_id=user.id, username=user.username)
        self.db.add(
            AuditLog(
                user_id=user.id,
                action="user.registered",
                resource_type="user",
                resource_id=str(user.id),
            )
        )
        return user

    async def login(self, username: str, password: str) -> tuple[str, str]:
        user = await self.users.get_by_username(username)
        if not user or not verify_password(password, user.password_hash):
            # 失败审计需独立提交（请求事务会随 AuthError 回滚）
            self.db.add(
                AuditLog(action="user.login_failed", resource_type="user", resource_id=username)
            )
            await self.db.commit()
            raise AuthError("invalid username or password")
        if user.status != "active":
            raise AuthError("user is not active")
        self.db.add(
            AuditLog(
                user_id=user.id, action="user.login", resource_type="user", resource_id=str(user.id)
            )
        )
        return self._tokens(user.id)

    async def refresh(self, user_id: int) -> tuple[str, str]:
        user = await self.users.get(user_id)
        if not user or user.status != "active":
            raise AuthError("user not found or inactive")
        return self._tokens(user.id)

    def _tokens(self, user_id: int) -> tuple[str, str]:
        return (
            create_access_token(user_id, settings.SECRET_KEY, settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            create_refresh_token(user_id, settings.SECRET_KEY, settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
