import json
import logging
import time

from prometheus_client import Counter, Histogram
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.models.ai import AiReview
from ai_service.services.llm import LLMClient

logger = logging.getLogger("ai-service.review")

AI_REQUESTS = Counter(
    "codeflow_ai_requests_total", "AI requests by endpoint", ["endpoint", "status"]
)
AI_LATENCY = Histogram("codeflow_ai_request_duration_seconds", "AI request latency", ["endpoint"])


class ReviewIssue(BaseModel):
    severity: str = "info"
    file: str = ""
    line: int = 0
    message: str
    suggestion: str = ""


class ReviewResult(BaseModel):
    summary: str
    severity: str = "info"
    issues: list[ReviewIssue] = []


CODE_REVIEW_SYSTEM = (
    "You are a senior code reviewer. Review the following diff and respond ONLY with "
    'JSON: {"summary": str, "severity": "info|low|medium|high", '
    '"issues": [{"severity": str, "file": str, "line": int, '
    '"message": str, "suggestion": str}]}'
)

ISSUE_ANALYSIS_SYSTEM = (
    "You are a project issue triage assistant. Analyze the issue and respond ONLY with "
    'JSON: {"category": "bug|performance|feature|task", '
    '"priority_suggestion": "low|medium|high|critical", "summary": str}'
)

CHAT_SYSTEM = (
    "You are CodeFlow AI assistant for a software team. "
    "Answer in the user's language. Prefer facts from provided context; "
    "say you don't know otherwise."
)


def _parse_json_reply(reply: str) -> dict:
    """容错解析 LLM 返回的 JSON（可能包裹在 ```json ... ``` 中）。"""
    text = reply.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = None
        for m_len in range(len(text), 1, -1):
            try:
                match = json.loads(text[:m_len])
                break
            except json.JSONDecodeError:
                continue
        if match is None:
            raise
        return match


async def run_code_review(
    db: AsyncSession,
    llm: LLMClient,
    diff: str,
    project_id: int | None = None,
    pull_request_id: int | None = None,
) -> AiReview:
    started = time.monotonic()
    raw = await llm.chat(CODE_REVIEW_SYSTEM, f"Review the following diff:\n\n{diff[:8000]}")
    AI_LATENCY.labels("code-review").observe(time.monotonic() - started)
    try:
        data = _parse_json_reply(raw)
        result = ReviewResult(**data)
        AI_REQUESTS.labels("code-review", "ok").inc()
    except (ValidationError, Exception) as exc:
        logger.warning("review parse failed: %s", exc)
        AI_REQUESTS.labels("code-review", "parse_error").inc()
        result = ReviewResult(
            summary=raw[:1000] or "review failed to produce structured output",
            severity="info",
            issues=[],
        )
    review = AiReview(
        project_id=project_id,
        pull_request_id=pull_request_id,
        summary=result.summary,
        severity=result.severity,
        result=result.model_dump(),
    )
    db.add(review)
    await db.flush()
    return review


async def run_issue_analysis(llm: LLMClient, title: str, description: str) -> dict:
    started = time.monotonic()
    raw = await llm.chat(
        ISSUE_ANALYSIS_SYSTEM,
        f"Issue analysis request:\ntitle: {title}\ndescription: {description[:3000]}",
    )
    AI_LATENCY.labels("issue-analysis").observe(time.monotonic() - started)
    try:
        data = _parse_json_reply(raw)
        AI_REQUESTS.labels("issue-analysis", "ok").inc()
        return data
    except Exception as exc:
        logger.warning("issue analysis parse failed: %s", exc)
        AI_REQUESTS.labels("issue-analysis", "parse_error").inc()
        return {"category": "task", "priority_suggestion": "medium", "summary": raw[:500]}
