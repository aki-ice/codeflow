"""LLM 客户端抽象。

- OpenAICompatibleClient：OpenAI/DeepSeek/Ollama 等兼容 API（需 LLM_API_KEY）
- MockLLMClient：无 Key 时降级，规则化输出，保证本地可演示、测试零网络
"""

import json
import logging
import re
from typing import Any, Protocol

import httpx

from ai_service.core.config import settings

logger = logging.getLogger("ai-service.llm")


class LLMClient(Protocol):
    name: str

    async def chat(self, system: str, user: str) -> str: ...


class OpenAICompatibleClient:
    name = "openai-compatible"

    async def chat(self, system: str, user: str) -> str:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{settings.LLM_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {settings.LLM_API_KEY}"},
                json={
                    "model": settings.LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": 0.2,
                },
            )
            resp.raise_for_status()
            return str(resp.json()["choices"][0]["message"]["content"])


class MockLLMClient:
    """规则化 Mock：可确定性演示，无外部依赖。"""

    name = "mock"

    async def chat(self, system: str, user: str) -> str:
        lowered = system.lower()
        if "code reviewer" in lowered:
            return self._mock_review(user)
        if "triage" in lowered:
            return self._mock_issue_analysis(user)
        return self._mock_chat(user)

    def _mock_chat(self, user: str) -> str:
        return (
            "[mock-llm] 关于你的问题：\n\n"
            f"「{user[:200]}」\n\n"
            "这是一个来自 Mock LLM 的确定性回复（未配置 LLM_API_KEY）。\n"
            "配置后本服务将通过 OpenAI 兼容接口调用真实大模型。\n"
            "如上下文中包含知识库内容，请优先依据上下文回答。"
        )

    def _mock_review(self, diff: str) -> str:
        issues: list[dict[str, Any]] = []
        if re.search(r"password\s*=\s*[\"'][^\"']+[\"']", diff, re.I):
            issues.append(
                {
                    "severity": "high",
                    "file": "diff",
                    "line": 1,
                    "message": "疑似硬编码密码，存在凭据泄露风险",
                    "suggestion": "使用环境变量或密钥管理服务",
                }
            )
        if "SELECT *" in diff:
            issues.append(
                {
                    "severity": "medium",
                    "file": "diff",
                    "line": 1,
                    "message": "SELECT * 可能带来性能与安全问题",
                    "suggestion": "只查询需要的列",
                }
            )
        if re.search(r"except\s*:", diff):
            issues.append(
                {
                    "severity": "low",
                    "file": "diff",
                    "line": 1,
                    "message": "裸 except 会吞掉所有异常",
                    "suggestion": "捕获具体异常类型并记录日志",
                }
            )
        severity = (
            "high"
            if any(i["severity"] == "high" for i in issues)
            else ("medium" if any(i["severity"] == "medium" for i in issues) else "info")
        )
        summary = (
            "Mock 审查：发现潜在问题，见 issues 列表。" if issues else "Mock 审查：未发现明显问题。"
        )
        return json.dumps(
            {"summary": summary, "severity": severity, "issues": issues}, ensure_ascii=False
        )

    def _mock_issue_analysis(self, user: str) -> str:
        text = user.lower()
        if "crash" in text or "500" in text or "error" in text:
            category, priority = "bug", "high"
        elif "slow" in text or "性能" in text or "latency" in text:
            category, priority = "performance", "medium"
        else:
            category, priority = "task", "medium"
        return json.dumps(
            {
                "category": category,
                "priority_suggestion": priority,
                "summary": "Mock 分析：根据描述关键词归类并给出优先级建议。",
            },
            ensure_ascii=False,
        )


def get_llm_client() -> LLMClient:
    if settings.LLM_API_KEY:
        return OpenAICompatibleClient()
    logger.warning("LLM_API_KEY empty, using MockLLMClient (degraded mode)")
    return MockLLMClient()
