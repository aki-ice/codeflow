from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from project_service.models.project import ISSUE_PRIORITIES, ISSUE_STATUSES, ISSUE_TYPES


class IssueCreate(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    description: str = Field(default="", max_length=65536)
    type: str = Field(default="task", pattern=f"^({'|'.join(ISSUE_TYPES)})$")
    priority: str = Field(default="medium", pattern=f"^({'|'.join(ISSUE_PRIORITIES)})$")
    assignee_id: int | None = Field(default=None, ge=1)


class IssueUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=256)
    description: str | None = None
    type: str | None = Field(default=None, pattern=f"^({'|'.join(ISSUE_TYPES)})$")
    priority: str | None = Field(default=None, pattern=f"^({'|'.join(ISSUE_PRIORITIES)})$")
    status: str | None = Field(default=None, pattern=f"^({'|'.join(ISSUE_STATUSES)})$")
    assignee_id: int | None = None


class IssueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    number: int | None = None
    title: str
    description: str
    type: str
    priority: str
    status: str
    assignee_id: int | None
    creator_id: int
    created_at: datetime
    updated_at: datetime


class IssuePage(BaseModel):
    total: int
    items: list[IssueOut]


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=65536)


class CommentOut(BaseModel):
    id: int
    issue_id: int
    user_id: int
    username: str | None
    content: str
    created_at: datetime
