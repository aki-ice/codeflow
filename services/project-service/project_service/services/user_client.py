"""用户信息跨服务查询客户端（Service 间通信）。

- HTTPUserClient：调用 user-service 的 /internal/users 接口，带内存 TTL 缓存
- FakeUserClient：测试用
"""

import time
from typing import Any

import httpx
from codeflow_common.breaker import BreakerOpenError, get_breaker
from codeflow_common.retry import async_retry

from project_service.core.config import settings

_breaker = get_breaker("user-service", failure_threshold=5, recovery_timeout=10.0)


class HTTPUserClient:
    def __init__(
        self, base_url: str | None = None, internal_token: str | None = None, cache_ttl: int = 60
    ) -> None:
        self.base_url = base_url or settings.USER_SERVICE_URL
        self.internal_token = internal_token or settings.INTERNAL_TOKEN
        self.cache_ttl = cache_ttl
        self._id_to_name: dict[int, tuple[float, str]] = {}
        self._name_to_id: dict[str, tuple[float, int]] = {}
        self.last_error: str = ""

    def _valid(self, entry: tuple[float, Any] | None) -> bool:
        return entry is not None and time.monotonic() - entry[0] < self.cache_ttl

    async def _request(self, method: str, url: str, body: dict | None = None) -> httpx.Response:
        @async_retry(attempts=2, base_delay=0.2, exceptions=(httpx.HTTPError,))
        async def _do() -> httpx.Response:
            async with httpx.AsyncClient(timeout=3) as client:
                return await client.request(
                    method,
                    url,
                    json=body,
                    headers={"X-Internal-Token": self.internal_token},
                )

        return await _breaker.call(_do)

    async def get_username(self, user_id: int) -> str | None:
        cached = self._id_to_name.get(user_id)
        if cached is not None and self._valid(cached):
            return cached[1]
        try:
            resp = await self._request("GET", f"{self.base_url}/api/v1/internal/users/{user_id}")
        except (httpx.HTTPError, BreakerOpenError) as exc:
            self.last_error = str(exc)
            return None
        if resp.status_code == 200:
            username = resp.json()["username"]
            self._id_to_name[user_id] = (time.monotonic(), username)
            return username
        return None

    async def get_user_id(self, username: str) -> int | None:
        cached = self._name_to_id.get(username)
        if cached is not None and self._valid(cached):
            return cached[1]
        try:
            resp = await self._request(
                "POST", f"{self.base_url}/api/v1/internal/users/lookup", {"usernames": [username]}
            )
        except (httpx.HTTPError, BreakerOpenError) as exc:
            self.last_error = str(exc)
            return None
        if resp.status_code == 200:
            users = resp.json()
            if users:
                user_id = users[0]["id"]
                self._name_to_id[username] = (time.monotonic(), user_id)
                return user_id
        return None

    async def get_usernames(self, user_ids: list[int]) -> dict[int, str]:
        if not user_ids:
            return {}
        result: dict[int, str] = {}
        missing: list[int] = []
        for uid in user_ids:
            cached = self._id_to_name.get(uid)
            if cached is not None and self._valid(cached):
                result[uid] = cached[1]
            else:
                missing.append(uid)
        if missing:
            try:
                resp = await self._request(
                    "POST", f"{self.base_url}/api/v1/internal/users/lookup-ids", {"ids": missing}
                )
            except (httpx.HTTPError, BreakerOpenError) as exc:
                self.last_error = str(exc)
                return result
            if resp.status_code == 200:
                now = time.monotonic()
                for u in resp.json():
                    result[u["id"]] = u["username"]
                    self._id_to_name[u["id"]] = (now, u["username"])
        return result


class FakeUserClient:
    """测试用：预置用户表，无网络调用。"""

    def __init__(self, users: dict[int, str] | None = None) -> None:
        self.users: dict[int, str] = users or {1: "alice", 2: "bob", 3: "carol"}

    async def get_username(self, user_id: int) -> str | None:
        return self.users.get(user_id)

    async def get_user_id(self, username: str) -> int | None:
        for uid, name in self.users.items():
            if name == username:
                return uid
        return None

    async def get_usernames(self, user_ids: list[int]) -> dict[int, str]:
        return {uid: self.users[uid] for uid in user_ids if uid in self.users}
