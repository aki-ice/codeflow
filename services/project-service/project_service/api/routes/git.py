import json
import logging

from fastapi import APIRouter, HTTPException, Request, status

from project_service.api.deps import CurrentUser, DBSession
from project_service.core.config import settings
from project_service.schemas.repository import PullRequestOut, RepositoryCreate, RepositoryOut
from project_service.services.github import GitHubService, WebhookError, verify_github_signature
from project_service.services.project import ProjectError, ProjectService

logger = logging.getLogger("project-service.github")

router = APIRouter(tags=["git"])


@router.post(
    "/projects/{project_id}/repositories",
    response_model=RepositoryOut,
    status_code=status.HTTP_201_CREATED,
)
async def register_repository(
    project_id: int, body: RepositoryCreate, user: CurrentUser, db: DBSession
) -> RepositoryOut:
    service = ProjectService(db)
    github = GitHubService(db)
    try:
        await service.require_role(project_id, user, "developer")
        repo = await github.register_repo(
            project_id, body.provider, body.external_id, body.url, body.default_branch
        )
    except ProjectError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    return RepositoryOut.model_validate(repo)


@router.get("/projects/{project_id}/repositories", response_model=list[RepositoryOut])
async def list_repositories(
    project_id: int, user: CurrentUser, db: DBSession
) -> list[RepositoryOut]:
    service = ProjectService(db)
    github = GitHubService(db)
    try:
        await service.require_role(project_id, user, "viewer")
        repos = await github.repos.list_for_project(project_id)
    except ProjectError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    return [RepositoryOut.model_validate(r) for r in repos]


@router.post("/repositories/{repository_id}/sync-prs", response_model=list[PullRequestOut])
async def sync_pull_requests(
    repository_id: int, user: CurrentUser, db: DBSession
) -> list[PullRequestOut]:
    github = GitHubService(db)
    repo = await github.repos.get(repository_id)
    if repo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "repository not found")
    try:
        await ProjectService(db).require_role(repo.project_id, user, "developer")
        await github.sync_pull_requests(repository_id)
        prs = await github.repos.list_prs(repository_id)
    except ProjectError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    except WebhookError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return [PullRequestOut.model_validate(p) for p in prs]


@router.post("/webhooks/github")
async def github_webhook(request: Request, db: DBSession) -> dict:
    """接收 GitHub Webhook: 验证 HMAC 签名, 处理 push, 发出 git.push 事件."""
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    event = request.headers.get("X-GitHub-Event", "")
    delivery_id = request.headers.get("X-GitHub-Delivery", "")

    if not verify_github_signature(body, signature, settings.GITHUB_WEBHOOK_SECRET):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid json") from exc

    if event == "ping":
        return {"status": "pong", "delivery": delivery_id}

    if event == "push":
        ref = payload.get("ref", "")
        branch = ref.split("/", 2)[-1] if ref.startswith("refs/heads/") else ref
        push = {
            "branch": branch,
            "commit_sha": payload.get("after", ""),
            "pusher": (payload.get("pusher") or {}).get("name", ""),
        }
        external_id = str((payload.get("repository") or {}).get("full_name", ""))
        github = GitHubService(db)
        result = await github.handle_push("github", external_id, push)
        await db.commit()
        logger.info("push webhook processed delivery=%s result=%s", delivery_id, result)
        return result

    return {"status": "ignored", "event": event}
