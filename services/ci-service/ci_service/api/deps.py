from typing import Annotated

import jwt
from codeflow_common.security import decode_token
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ci_service.core.config import settings
from ci_service.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

DBSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user_id(token: Annotated[str, Depends(oauth2_scheme)]) -> int:
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


CurrentUser = Annotated[int, Depends(get_current_user_id)]
