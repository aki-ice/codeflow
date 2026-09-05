from sqlalchemy import select
from user_service.models.audit import AuditLog


async def test_audit_login_recorded(client, app):
    await client.post(
        "/api/v1/auth/register",
        json={"username": "auditor", "email": "auditor@example.com", "password": "secret1234"},
    )
    await client.post("/api/v1/auth/login", data={"username": "auditor", "password": "secret1234"})
    # 登录失败也记录
    await client.post("/api/v1/auth/login", data={"username": "auditor", "password": "wrong-pass"})

    async with app.state.test_session_factory() as session:
        rows = (await session.execute(select(AuditLog))).scalars().all()
    actions = {r.action for r in rows}
    assert "user.registered" in actions
    assert "user.login" in actions
    assert "user.login_failed" in actions


async def test_ready_endpoint(client):
    resp = await client.get("/ready")
    assert resp.status_code == 200
    assert resp.json()["ready"] is True
