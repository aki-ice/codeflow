"""向量检索抽象。

- PgVectorStore：pgvector 的 <=> 余弦距离算子（数据库内计算，性能最优）
- PythonVectorStore：把 JSON 向量读回内存算余弦（SQLite/无 pgvector 时降级）

启动时自动探测 pgvector 可用性并维护 embedding_vec 列。
"""

import json
import logging
import math

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.models.ai import Document

logger = logging.getLogger("ai-service.rag")


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return -1.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


class RAGVectorService:
    def __init__(self, db: AsyncSession, dim: int) -> None:
        self.db = db
        self.dim = dim
        self.pgvector_available = False

    async def ensure_pgvector(self) -> None:
        """探测 pgvector：可用则建扩展 + 向量列（幂等）。"""
        try:
            await self.db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await self.db.execute(
                text(
                    f"ALTER TABLE documents ADD COLUMN IF NOT EXISTS "
                    f"embedding_vec vector({self.dim})"
                )
            )
            await self.db.commit()
            self.pgvector_available = True
            logger.info("pgvector enabled, dim=%s", self.dim)
        except Exception as exc:
            await self.db.rollback()
            self.pgvector_available = False
            logger.info("pgvector unavailable, using python cosine fallback: %s", exc)

    async def upsert_embedding(self, doc_id: int, embedding: list[float]) -> None:
        if self.pgvector_available:
            vec = "[" + ",".join(f"{v:.6f}" for v in embedding) + "]"
            await self.db.execute(
                text("UPDATE documents SET embedding_vec = CAST(:v AS vector) WHERE id = :id"),
                {"v": vec, "id": doc_id},
            )
        # JSON 列由 ORM 维护，无需处理

    async def search(
        self, project_id: int, query_embedding: list[float], k: int
    ) -> list[tuple[Document, float]]:
        if self.pgvector_available:
            vec = "[" + ",".join(f"{v:.6f}" for v in query_embedding) + "]"
            result = await self.db.execute(
                text(
                    "SELECT id, doc_name, chunk_index, content, "
                    "embedding_vec <=> CAST(:q AS vector) AS distance "
                    "FROM documents WHERE project_id = :pid "
                    "ORDER BY embedding_vec <=> CAST(:q AS vector) LIMIT :k"
                ),
                {"q": vec, "pid": project_id, "k": k},
            )
            hits = []
            for row in result.all():
                doc = Document(
                    id=row.id,
                    project_id=project_id,
                    doc_name=row.doc_name,
                    chunk_index=row.chunk_index,
                    content=row.content,
                    embedding=[],
                )
                # <=> 返回余弦距离（越小越相似），统一转成相似度（越大越相似）
                hits.append((doc, 1.0 - float(row.distance)))
            return hits

        # 降级：Python 余弦
        result = await self.db.execute(
            text(
                "SELECT id, doc_name, chunk_index, content, embedding "
                "FROM documents WHERE project_id = :pid"
            ),
            {"pid": project_id},
        )
        scored: list[tuple[Document, float]] = []
        for row in result.all():
            emb = (
                json.loads(row.embedding)
                if isinstance(row.embedding, str)
                else (row.embedding or [])
            )
            score = cosine(query_embedding, emb)
            doc = Document(
                id=row.id,
                project_id=project_id,
                doc_name=row.doc_name,
                chunk_index=row.chunk_index,
                content=row.content,
                embedding=emb,
            )
            scored.append((doc, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]
