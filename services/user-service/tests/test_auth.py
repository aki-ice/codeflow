async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "user-service"


async def test_register_login_me(client, auth_headers):
    resp = await client.get("/api/v1/users/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "alice"


async def test_login_wrong_password(client):
    await client.post(
        "/api/v1/auth/register",
        json={"username": "dave", "email": "dave@example.com", "password": "secret1234"},
    )
    resp = await client.post(
        "/api/v1/auth/login", data={"username": "dave", "password": "wrong-pass"}
    )
    assert resp.status_code == 401


async def test_refresh(client, auth_headers):
    resp = await client.post(
        "/api/v1/auth/login", data={"username": "alice", "password": "secret1234"}
    )
    refresh = resp.json()["refresh_token"]
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


async def test_internal_lookup(client, auth_headers):
    resp = await client.post(
        "/api/v1/internal/users/lookup",
        json={"usernames": ["alice"]},
        headers={"X-Internal-Token": "dev-internal-token"},
    )
    assert resp.status_code == 200
    users = resp.json()
    assert len(users) == 1
    assert users[0]["username"] == "alice"

    resp = await client.post(
        "/api/v1/internal/users/lookup", json={"usernames": ["alice"]}, headers={}
    )
    assert resp.status_code == 401
