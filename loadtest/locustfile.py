"""CodeFlow 负载测试（Phase 15）。

模拟真实研发协作流程：登录 → 建项目 → 建 Issue → 查询。

运行（先 scripts/start-all.ps1 起全栈）：
    uv run locust -f loadtest/locustfile.py --headless -u 50 -r 5 -t 60s \
        --host http://localhost:8000

观察：
    - Grafana CodeFlow API Overview（QPS / P95 / P99 / 错误率）
    - Prometheus: sum(rate(codeflow_http_requests_total[1m])) by (service)
"""

import random
import string
import time

from locust import HttpUser, between, task


def _rand_suffix() -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=8))


class CodeFlowUser(HttpUser):
    wait_time = between(0.2, 1.0)
    host = "http://localhost:8000"

    def on_start(self) -> None:
        """每个虚拟用户注册并登录一次。"""
        suffix = _rand_suffix()
        self.username = f"locust_{suffix}"
        self.password = "locust-pass-123"
        self.project_id: int | None = None
        self._created_issues = 0

        resp = self.client.post(
            "/api/v1/auth/register",
            json={
                "username": self.username,
                "email": f"{self.username}@loadtest.dev",
                "password": self.password,
            },
            name="/api/v1/auth/register [setup]",
            catch_response=True,
        )
        with resp as r:
            if r.status_code not in (200, 201, 409):
                r.failure(f"register failed: {r.status_code} {r.text[:100]}")

        resp = self.client.post(
            "/api/v1/auth/login",
            data={"username": self.username, "password": self.password},
            name="/api/v1/auth/login [setup]",
            catch_response=True,
        )
        with resp as r:
            if r.status_code == 200:
                self.headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
                # 建一个本项目用户专属的工作项目
                resp2 = self.client.post(
                    "/api/v1/projects",
                    json={"name": f"load-{suffix}"},
                    headers=self.headers,
                    name="/api/v1/projects [setup]",
                )
                if resp2.status_code in (200, 201):
                    self.project_id = resp2.json()["id"]
            else:
                r.failure("login failed")
                self.headers = {}

    @task(4)
    def list_projects(self) -> None:
        self.client.get("/api/v1/projects", headers=self.headers, name="/api/v1/projects")

    @task(3)
    def create_issue(self) -> None:
        if not self.project_id:
            return
        self._created_issues += 1
        self.client.post(
            f"/api/v1/projects/{self.project_id}/issues",
            json={"title": f"loadtest issue {self._created_issues}", "type": "task"},
            headers=self.headers,
            name="/api/v1/projects/:id/issues",
        )

    @task(3)
    def list_issues(self) -> None:
        if not self.project_id:
            return
        self.client.get(
            f"/api/v1/projects/{self.project_id}/issues",
            headers=self.headers,
            name="/api/v1/projects/:id/issues",
        )

    @task(1)
    def ai_chat(self) -> None:
        """低频 AI 请求（Mock LLM，验证 AI 链路在负载下的表现）。"""
        self.client.post(
            "/api/v1/ai/chat",
            json={"message": "ping", "use_rag": False},
            headers=self.headers,
            name="/api/v1/ai/chat",
        )

    @task(1)
    def health(self) -> None:
        self.client.get("/health", name="/health")
