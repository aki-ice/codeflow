from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    avatar: str | None
    status: str
    created_at: datetime


class UserBrief(BaseModel):
    """内部服务间通信使用的精简用户信息。"""

    id: int
    username: str


class LookupRequest(BaseModel):
    usernames: list[str] = Field(max_length=100)


class LookupByIdRequest(BaseModel):
    ids: list[int] = Field(max_length=200)
