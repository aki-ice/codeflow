from typing import Annotated

import jwt
from codeflow_common.redis import Cache, RateLimiter, create_redis
from codeflow_common.security import decode_token
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from project_service.core.config import settings
from project_service.db.session import get_db
from project_service.services.user_client import FakeUserClient, HTTPUserClient

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

DBSession = Annotated[AsyncSession, Depends(get_db)]

_redis = None


async def get_redis_client():
    global _redis
    if _redis is None:
        _redis = await create_redis(settings.REDIS_URL)
    return _redis


async def get_cache() -> Cache:
    return Cache(await get_redis_client(), settings.CACHE_TTL_SECONDS)


async def get_rate_limiter() -> RateLimiter:
    return RateLimiter(await get_redis_client())


CacheDep = Annotated[Cache, Depends(get_cache)]
RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]


async def rate_limit(request: Request, limiter: RateLimiterDep) -> None:
    identity = "anonymous"
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        identity = auth[7:32]
    client_ip = request.client.host if request.client else "unknown"
    ok = await limiter.check(
        f"{request.url.path}:{identity or client_ip}", settings.RATE_LIMIT_PER_MINUTE
    )
    if not ok:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "rate limit exceeded")


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> int:
    """JWT 本地校验（网关已验一次，这里二次校验），返回 user_id。"""
    credentials_error = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        return decode_token(token, settings.SECRET_KEY, expected_type="access")
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise credentials_error from exc


CurrentUser = Annotated[int, Depends(get_current_user)]

_user_client: HTTPUserClient | FakeUserClient | None = None


def get_user_client() -> HTTPUserClient | FakeUserClient:
    global _user_client
    if _user_client is None:
        _user_client = HTTPUserClient()
    return _user_client


def set_user_client(client) -> None:
    global _user_client
    _user_client = client


UserClientDep = Annotated[object, Depends(get_user_client)]
