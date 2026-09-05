from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    project_id: int | None = None
    use_rag: bool = True


class ChatResponse(BaseModel):
    answer: str
    llm: str
    context_used: int


class CodeReviewRequest(BaseModel):
    diff: str = Field(min_length=1, max_length=100_000)
    project_id: int | None = None
    pull_request_id: int | None = None


class ReviewIssueOut(BaseModel):
    severity: str = "info"
    file: str = ""
    line: int = 0
    message: str
    suggestion: str = ""


class CodeReviewResponse(BaseModel):
    id: int
    summary: str
    severity: str
    issues: list[ReviewIssueOut]
    llm: str
    created_at: datetime


class IssueAnalysisRequest(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    description: str = Field(default="", max_length=8000)


class IssueAnalysisResponse(BaseModel):
    category: str
    priority_suggestion: str
    summary: str
    llm: str


class DocumentIngest(BaseModel):
    project_id: int
    name: str = Field(min_length=1, max_length=256)
    content: str = Field(min_length=1, max_length=200_000)


class DocumentIngestResponse(BaseModel):
    chunks: int
    embedding_provider: str
    vector_backend: str


class ContextHit(BaseModel):
    doc_name: str
    chunk_index: int
    content: str
    score: float


class ContextSearchRequest(BaseModel):
    project_id: int
    query: str = Field(min_length=1, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=10)
