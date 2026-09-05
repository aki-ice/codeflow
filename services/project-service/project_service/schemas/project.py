from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=2048)
    visibility: str = Field(default="private", pattern="^(private|public)$")


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2048)
    visibility: str | None = Field(default=None, pattern="^(private|public)$")


class ProjectMemberAdd(BaseModel):
    username: str
    role: str = Field(default="developer", pattern="^(admin|developer|viewer)$")


class ProjectMemberUpdate(BaseModel):
    role: str = Field(pattern="^(admin|developer|viewer)$")


class ProjectMemberOut(BaseModel):
    id: int
    user_id: int
    username: str
    role: str
    created_at: datetime


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    visibility: str
    created_by: int
    created_at: datetime
    updated_at: datetime


class Page(BaseModel):
    total: int
    items: list[ProjectOut]
