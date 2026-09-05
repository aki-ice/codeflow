import hashlib
import hmac
import json

from project_service.core.config import settings


def _sign(body: bytes) -> str:
    digest = hmac.new(settings.GITHUB_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


async def test_webhook_ping(client, auth_headers):
    body = b"{}"
    resp = await client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={"X-GitHub-Event": "ping", "X-Hub-Signature-256": _sign(body)},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "pong"


async def test_webhook_push_requires_valid_repo(client, auth_headers):
    body = json.dumps(
        {
            "ref": "refs/heads/main",
            "after": "abc123",
            "pusher": {"name": "alice"},
            "repository": {"full_name": "nobody/unknown"},
        }
    ).encode()
    resp = await client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={"X-GitHub-Event": "push", "X-Hub-Signature-256": _sign(body)},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


async def test_webhook_push_emits_git_push_event(client, auth_headers, app):
    resp = await client.post("/api/v1/projects", json={"name": "gitproj"}, headers=auth_headers)
    project_id = resp.json()["id"]
    resp = await client.post(
        f"/api/v1/projects/{project_id}/repositories",
        json={
            "provider": "github",
            "external_id": "me/codeflow-demo",
            "url": "https://github.com/me/codeflow-demo",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201

    body = json.dumps(
        {
            "ref": "refs/heads/feature-x",
            "after": "deadbeef",
            "pusher": {"name": "alice"},
            "repository": {"full_name": "me/codeflow-demo"},
        }
    ).encode()
    resp = await client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={"X-GitHub-Event": "push", "X-Hub-Signature-256": _sign(body)},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"

    from project_service.models.project import OutboxEvent
    from sqlalchemy import select

    async with app.state.test_session_factory() as session:
        rows = (
            (await session.execute(select(OutboxEvent).where(OutboxEvent.event_type == "git.push")))
            .scalars()
            .all()
        )
    assert len(rows) == 1
    assert rows[0].payload["branch"] == "feature-x"
    assert rows[0].payload["commit_sha"] == "deadbeef"
    assert rows[0].topic == "codeflow.git.events"


async def test_webhook_invalid_signature_rejected(client):
    resp = await client.post(
        "/api/v1/webhooks/github",
        content=b"{}",
        headers={"X-GitHub-Event": "push", "X-Hub-Signature-256": "sha256=bad"},
    )
    assert resp.status_code == 401


async def test_pr_sync_without_token_returns_400(client, auth_headers):
    resp = await client.post("/api/v1/projects", json={"name": "prs"}, headers=auth_headers)
    project_id = resp.json()["id"]
    resp = await client.post(
        f"/api/v1/projects/{project_id}/repositories",
        json={"provider": "github", "external_id": "me/repo"},
        headers=auth_headers,
    )
    repo_id = resp.json()["id"]
    resp = await client.post(f"/api/v1/repositories/{repo_id}/sync-prs", headers=auth_headers)
    assert resp.status_code == 400
    assert "GITHUB_TOKEN" in resp.json()["detail"]
