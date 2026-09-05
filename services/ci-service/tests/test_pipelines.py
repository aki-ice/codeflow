import asyncio


async def test_health(client):
    resp = await client.get("/health")
    assert resp.json()["service"] == "ci-service"


async def _wait_status(client, pipeline_id: int, statuses: tuple[str, ...], timeout=15.0):
    for _ in range(int(timeout / 0.3)):
        resp = await client.get(f"/api/v1/pipelines/{pipeline_id}", headers=_H)
        if resp.json()["status"] in statuses:
            return resp.json()
        await asyncio.sleep(0.3)
    raise AssertionError(f"pipeline {pipeline_id} did not reach {statuses}")


_H = {}


async def test_manual_pipeline_runs_to_success(client, auth_headers, app):
    global _H
    _H = auth_headers

    resp = await client.post(
        "/api/v1/pipelines",
        json={"project_id": 1, "repository": "me/demo", "branch": "main", "commit_sha": "abc123"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    pipeline_id = resp.json()["id"]
    assert resp.json()["status"] == "pending"

    final = await _wait_status(client, pipeline_id, ("success", "failed"))
    assert final["status"] == "success"

    detail = (await client.get(f"/api/v1/pipelines/{pipeline_id}", headers=auth_headers)).json()
    assert "[test]" in detail["logs"]
    assert detail["build_status"] == "success"


async def test_cancel_pending_pipeline(client, auth_headers, app):
    resp = await client.post(
        "/api/v1/pipelines",
        json={"project_id": 1, "repository": "me/x", "branch": "dev", "commit_sha": "def456"},
        headers=auth_headers,
    )
    pipeline_id = resp.json()["id"]
    # 立即取消（可能还在 pending 或已 running）
    resp = await client.post(f"/api/v1/pipelines/{pipeline_id}/cancel", headers=auth_headers)
    body = resp.json()
    assert body["id"] == pipeline_id
    assert body["status"] in ("canceled", "success", "failed")


async def test_duplicate_git_push_is_idempotent(app):
    from ci_service.events.consumer import handle_git_push

    payload = {
        "project_id": 1,
        "repository": "me/idem",
        "branch": "main",
        "commit_sha": "same123",
        "repository_id": 1,
    }
    await handle_git_push(payload, "evt-1")
    await asyncio.sleep(0.1)
    await handle_git_push(payload, "evt-2")
    await asyncio.sleep(0.5)

    async with app.state.test_session_factory() as session:
        from ci_service.models.pipeline import Pipeline
        from sqlalchemy import func, select

        count = int(
            (
                await session.execute(
                    select(func.count()).select_from(
                        select(Pipeline).where(Pipeline.repository == "me/idem").subquery()
                    )
                )
            ).scalar_one()
        )
    assert count == 1


async def test_git_push_creates_pipeline_and_event(app):
    from ci_service.events.consumer import handle_git_push
    from ci_service.models.pipeline import OutboxEvent
    from sqlalchemy import select

    await handle_git_push(
        {
            "project_id": 2,
            "repository": "me/evt",
            "branch": "feature",
            "commit_sha": "cafe123",
            "repository_id": 7,
        },
        "evt-9",
    )
    await asyncio.sleep(0.3)

    async with app.state.test_session_factory() as session:
        rows = (
            (
                await session.execute(
                    select(OutboxEvent).where(OutboxEvent.event_type == "pipeline.created")
                )
            )
            .scalars()
            .all()
        )
    assert len(rows) == 1
    assert rows[0].topic == "codeflow.pipeline.events"
    assert rows[0].payload["branch"] == "feature"
