from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RepositoryCreate(BaseModel):
    provider: str = Field(default="github", pattern="^(github|gitlab)$")
    external_id: str = Field(min_length=1, max_length=128)  # GitHub: owner/repo
    url: str = Field(default="", max_length=512)
    default_branch: str = Field(default="main", max_length=128)


class RepositoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    provider: str
    external_id: str
    url: str
    default_branch: str
    created_at: datetime


class PullRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repository_id: int
    external_id: int
    title: str
    author_login: str
    status: str
    source_branch: str
    target_branch: str
    created_at: datetime
