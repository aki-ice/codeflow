from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from user_service.api.deps import DBSession
from user_service.core.config import settings
from user_service.core.security import decode_token
from user_service.schemas.user import RefreshRequest, TokenPair, UserCreate, UserOut
from user_service.services.auth import AuthError, AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate, db: DBSession) -> UserOut:
    try:
        user = await AuthService(db).register(body.username, body.email, body.password)
    except AuthError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return UserOut.model_validate(user)


@router.post("/login", response_model=TokenPair)
async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DBSession) -> TokenPair:
    try:
        access, refresh = await AuthService(db).login(form.username, form.password)
    except AuthError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest, db: DBSession) -> TokenPair:
    try:
        user_id = decode_token(body.refresh_token, settings.SECRET_KEY, expected_type="refresh")
        access, refresh_token = await AuthService(db).refresh(user_id)
    except AuthError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid refresh token") from exc
    return TokenPair(access_token=access, refresh_token=refresh_token)
