"""Embedding 提供者。

- OpenAICompatibleEmbedding：真实 API（需 Key）
- MockEmbedding：词哈希 256 维归一化向量（确定性、零网络）
"""

import abc
import hashlib
import math
import re

import httpx

from ai_service.core.config import settings


class EmbeddingProvider(abc.ABC):
    name = "base"
    dim: int

    @abc.abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class OpenAICompatibleEmbedding(EmbeddingProvider):
    name = "openai-compatible"

    def __init__(self) -> None:
        self.dim = settings.EMBEDDING_DIM

    async def embed(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.LLM_BASE_URL}/embeddings",
                headers={"Authorization": f"Bearer {settings.LLM_API_KEY}"},
                json={"model": settings.EMBEDDING_MODEL, "input": texts},
            )
            resp.raise_for_status()
            data = resp.json()["data"]
            return [self._fit(v["embedding"]) for v in data]

    def _fit(self, vec: list[float]) -> list[float]:
        if len(vec) == self.dim:
            return vec
        if len(vec) > self.dim:
            return vec[: self.dim]
        return vec + [0.0] * (self.dim - len(vec))


class MockEmbedding(EmbeddingProvider):
    name = "mock"

    def __init__(self) -> None:
        self.dim = settings.EMBEDDING_DIM

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in re.findall(r"[a-zA-Z\u4e00-\u9fff]+", text.lower()):
            digest = hashlib.md5(token.encode()).digest()
            idx = int.from_bytes(digest[:4], "big") % self.dim
            vec[idx] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


def get_embedding_provider() -> EmbeddingProvider:
    if settings.LLM_API_KEY:
        return OpenAICompatibleEmbedding()
    return MockEmbedding()
