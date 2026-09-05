"""GitHub 集成（Phase 6）。

- Webhook HMAC 验签（X-Hub-Signature-256，sha256=<hexdigest>）
- push 事件 -> 经 Outbox 发出 codeflow.git.events 的 git.push 事件
- PR 同步：调用 GitHub REST API（需手动配置 GITHUB_TOKEN）
"""

import hashlib
import hmac
import logging

import httpx
from codeflow_common.outbox import emit
from sqlalchemy.ext.asyncio import AsyncSession

from project_service.core.config import settings
from project_service.models.project import OutboxEvent, Repository
from project_service.repositories.issue import GitRepository

logger = logging.getLogger("project-service.github")


class WebhookError(Exception):
    pass


def verify_github_signature(payload_body: bytes, signature_header: str | None, secret: str) -> bool:
    """X-Hub-Signature-256 校验：sha256=HMAC(secret, body)。"""
    if not secret:
        logger.warning("GITHUB_WEBHOOK_SECRET not configured, skipping verification")
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), payload_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature_header[7:], expected)


class GitHubService:
    def __init__(self, db: AsyncSession) -> None:
        self.repos = GitRepository(db)
        self.db = db

    async def register_repo(
        self, project_id: int, provider: str, external_id: str, url: str, default_branch: str
    ) -> Repository:
        repo = Repository(
            project_id=project_id,
            provider=provider,
            external_id=external_id,
            url=url,
            default_branch=default_branch,
            webhook_secret_configured=bool(settings.GITHUB_WEBHOOK_SECRET),
        )
        return await self.repos.create(repo)

    async def handle_push(self, provider: str, external_id: str, push: dict) -> dict:
        repo = await self.repos.get_by_external_id(provider, external_id)
        if repo is None:
            logger.warning("push for unregistered repo %s, ignored", external_id)
            return {"status": "ignored", "reason": "repository not registered"}

        await emit(
            self.db,
            OutboxEvent,
            "git.push",
            repository_id=repo.id,
            project_id=repo.project_id,
            provider=provider,
            repository=external_id,
            branch=push.get("branch", repo.default_branch),
            commit_sha=push.get("commit_sha", ""),
            pusher=push.get("pusher", ""),
        )
        return {"status": "accepted", "project_id": repo.project_id}

    async def sync_pull_requests(self, repo_id: int) -> int:
        repo = await self.repos.get(repo_id)
        if repo is None:
            raise WebhookError("repository not found")
        if not settings.GITHUB_TOKEN:
            raise WebhookError("GITHUB_TOKEN is not configured")

        headers = {
            "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
        }
        prs: list[dict] = []
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{settings.GITHUB_API_URL}/repos/{repo.external_id}/pulls",
                headers=headers,
                params={"state": "open", "per_page": 50},
            )
            resp.raise_for_status()
            for item in resp.json():
                prs.append(
                    {
                        "external_id": item["number"],
                        "title": item["title"],
                        "description": item.get("body") or "",
                        "author_login": (item.get("user") or {}).get("login", ""),
                        "status": "open",
                        "source_branch": item["head"]["ref"],
                        "target_branch": item["base"]["ref"],
                    }
                )
        return await self.repos.upsert_prs(repo_id, prs)
