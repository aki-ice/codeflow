from typing import Annotated

import jwt
from codeflow_common.security import decode_token
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from user_service.core.config import settings
from user_service.db.session import get_db
from user_service.models.user import User
from user_service.repositories.user import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

DBSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: DBSession) -> User:
    credentials_error = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id = decode_token(token, settings.SECRET_KEY, expected_type="access")
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise credentials_error from exc
    user = await UserRepository(db).get(user_id)
    if not user or user.status != "active":
        raise credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_internal_token(
    x_internal_token: Annotated[str, Header(alias="X-Internal-Token")] = "",
) -> None:
    """服务间内部调用鉴权（网关不转发外部请求到 /internal/*）。"""
    if x_internal_token != settings.INTERNAL_TOKEN:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid internal token")
