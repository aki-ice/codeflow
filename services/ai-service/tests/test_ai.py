async def test_health(client):
    resp = await client.get("/health")
    assert resp.json()["service"] == "ai-service"


async def test_chat_mock_llm(client, auth_headers):
    resp = await client.post(
        "/api/v1/ai/chat",
        json={"message": "hello, what is codeflow?"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["llm"] == "mock"
    assert "mock" in body["answer"].lower()


async def test_code_review_detects_hardcoded_password(client, auth_headers):
    diff = """
+ def connect():
+     password = "super-secret-123"
+     return create_conn(password)
"""
    resp = await client.post(
        "/api/v1/ai/code-review",
        json={"diff": diff, "project_id": 1},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["llm"] == "mock"
    assert body["severity"] == "high"
    assert any("密码" in i["message"] or "password" in i["message"].lower() for i in body["issues"])
    assert body["id"] > 0


async def test_code_review_clean_diff(client, auth_headers):
    diff = "+ def add(a, b):\n+     return a + b\n"
    resp = await client.post("/api/v1/ai/code-review", json={"diff": diff}, headers=auth_headers)
    body = resp.json()
    assert body["severity"] == "info"
    assert body["issues"] == []


async def test_issue_analysis(client, auth_headers):
    resp = await client.post(
        "/api/v1/ai/issue-analysis",
        json={"title": "service crashes with 500 error", "description": "stack trace..."},
        headers=auth_headers,
    )
    body = resp.json()
    assert body["category"] == "bug"
    assert body["priority_suggestion"] == "high"


async def test_rag_ingest_and_search(client, auth_headers):
    content = (
        "CodeFlow deployment guide.\n\n"
        "The project-service connects to PostgreSQL database codeflow_projects "
        "and uses Redis for caching and rate limiting.\n\n"
        "CI pipelines are executed by ci-service which consumes git.push events "
        "from Kafka and runs checkout, test, lint and build steps."
    )
    resp = await client.post(
        "/api/v1/ai/documents",
        json={"project_id": 1, "name": "ops.md", "content": content},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["embedding_provider"] == "mock"
    assert body["vector_backend"] == "python-cosine"
    assert body["chunks"] >= 1

    resp = await client.post(
        "/api/v1/ai/documents/search",
        json={
            "project_id": 1,
            "query": "which service runs CI pipelines from git.push events",
            "top_k": 2,
        },
        headers=auth_headers,
    )
    hits = resp.json()
    assert len(hits) >= 1
    assert "ci-service" in hits[0]["content"] or "Kafka" in hits[0]["content"]


async def test_chat_with_rag_context(client, auth_headers):
    content = (
        "The api rate limit is 120 requests per minute.\n\nDatabase backups run every night at 3am."
    )
    await client.post(
        "/api/v1/ai/documents",
        json={"project_id": 9, "name": "faq.md", "content": content},
        headers=auth_headers,
    )
    resp = await client.post(
        "/api/v1/ai/chat",
        json={"message": "what is the api rate limit?", "project_id": 9},
        headers=auth_headers,
    )
    body = resp.json()
    assert body["context_used"] >= 1
