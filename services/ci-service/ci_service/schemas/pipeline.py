from datetime import datetime

from pydantic import BaseModel


class PipelineTrigger(BaseModel):
    project_id: int
    repository: str = ""
    repository_id: int | None = None
    branch: str = "main"
    commit_sha: str = ""


class PipelineOut(BaseModel):
    id: int
    project_id: int
    repository: str
    repository_id: int | None
    commit_sha: str
    branch: str
    status: str
    trigger_type: str
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class PipelineDetail(PipelineOut):
    build_id: int | None = None
    build_status: str | None = None
    logs: str = ""


class PipelinePage(BaseModel):
    total: int
    items: list[PipelineOut]
