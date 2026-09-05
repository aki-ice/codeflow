async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "project-service"


async def test_project_crud_flow(client, auth_headers):
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "demo", "description": "first project", "visibility": "private"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    project = resp.json()
    project_id = project["id"]

    resp = await client.get(f"/api/v1/projects/{project_id}", headers=auth_headers)
    assert resp.status_code == 200

    resp = await client.get("/api/v1/projects", headers=auth_headers)
    assert resp.json()["total"] == 1

    resp = await client.patch(
        f"/api/v1/projects/{project_id}", json={"description": "updated"}, headers=auth_headers
    )
    assert resp.json()["description"] == "updated"

    resp = await client.delete(f"/api/v1/projects/{project_id}", headers=auth_headers)
    assert resp.status_code == 204


async def test_member_add_via_user_service(client, auth_headers):
    # add member 通过 user-service 内部 API 解析 username -> user_id
    resp = await client.post("/api/v1/projects", json={"name": "team"}, headers=auth_headers)
    project_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"username": "bob", "role": "developer"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["user_id"] == 2
    assert resp.json()["username"] == "bob"

    resp = await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"username": "ghost", "role": "viewer"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


async def test_issue_crud_with_number(client, auth_headers):
    resp = await client.post("/api/v1/projects", json={"name": "seq"}, headers=auth_headers)
    project_id = resp.json()["id"]

    r1 = await client.post(
        f"/api/v1/projects/{project_id}/issues", json={"title": "first"}, headers=auth_headers
    )
    r2 = await client.post(
        f"/api/v1/projects/{project_id}/issues", json={"title": "second"}, headers=auth_headers
    )
    assert r1.status_code == 201 and r2.status_code == 201
    assert r2.json()["number"] == r1.json()["number"] + 1

    resp = await client.patch(
        f"/api/v1/issues/{r1.json()['id']}", json={"status": "in_progress"}, headers=auth_headers
    )
    assert resp.json()["status"] == "in_progress"

    resp = await client.get(
        f"/api/v1/projects/{project_id}/issues?status=in_progress", headers=auth_headers
    )
    assert resp.json()["total"] == 1


async def test_comments(client, auth_headers):
    resp = await client.post("/api/v1/projects", json={"name": "cproj"}, headers=auth_headers)
    project_id = resp.json()["id"]
    resp = await client.post(
        f"/api/v1/projects/{project_id}/issues", json={"title": "task A"}, headers=auth_headers
    )
    issue_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/issues/{issue_id}/comments",
        json={"content": "hello"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["username"] == "alice"

    resp = await client.get(f"/api/v1/issues/{issue_id}/comments", headers=auth_headers)
    assert len(resp.json()) == 1


async def test_non_member_issue_403(client, auth_headers):
    resp = await client.post(
        "/api/v1/projects/99999/issues", json={"title": "ghost"}, headers=auth_headers
    )
    assert resp.status_code == 403
