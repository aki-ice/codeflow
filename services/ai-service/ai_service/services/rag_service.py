"""RAG 流程：文档 -> Chunk -> Embedding -> 向量库 -> 相似检索 -> 上下文 -> LLM。"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.core.config import settings
from ai_service.models.ai import Document
from ai_service.services.embeddings import EmbeddingProvider
from ai_service.services.rag import RAGVectorService

logger = logging.getLogger("ai-service.rag")


def chunk_text(content: str, chunk_size: int | None = None) -> list[str]:
    """按段落聚合分块，单块不超过 chunk_size 字符。"""
    size = chunk_size or settings.RAG_CHUNK_SIZE
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    chunks: list[str] = []
    buf = ""
    for para in paragraphs:
        # 超长段落硬切
        while len(para) > size:
            if buf:
                chunks.append(buf)
                buf = ""
            chunks.append(para[:size])
            para = para[size:]
        if len(buf) + len(para) + 2 <= size:
            buf = f"{buf}\n\n{para}".strip()
        else:
            if buf:
                chunks.append(buf)
            buf = para
    if buf:
        chunks.append(buf)
    return chunks or ([content[:size]] if content else [])


class RAGService:
    def __init__(self, db: AsyncSession, embeddings: EmbeddingProvider) -> None:
        self.db = db
        self.embeddings = embeddings
        self.vectors = RAGVectorService(db, settings.EMBEDDING_DIM)

    async def ingest(self, project_id: int, doc_name: str, content: str) -> int:
        chunks = chunk_text(content)
        vectors = await self.embeddings.embed(chunks)
        count = 0
        for i, (chunk, emb) in enumerate(zip(chunks, vectors, strict=False)):
            doc = Document(
                project_id=project_id,
                doc_name=doc_name,
                chunk_index=i,
                content=chunk,
                embedding=emb,
            )
            self.db.add(doc)
            await self.db.flush()
            await self.vectors.upsert_embedding(doc.id, emb)
            count += 1
        await self.db.commit()
        logger.info("ingested %s chunks from %s", count, doc_name)
        return count

    async def search_context(self, project_id: int, query: str, k: int | None = None) -> list[dict]:
        top_k = k or settings.RAG_TOP_K
        [query_vec] = await self.embeddings.embed([query])
        hits = await self.vectors.search(project_id, query_vec, top_k)
        return [
            {
                "doc_name": doc.doc_name,
                "chunk_index": doc.chunk_index,
                "content": doc.content,
                "score": round(score, 4),
            }
            for doc, score in hits
        ]

    def build_context_prompt(self, context: list[dict]) -> str:
        if not context:
            return ""
        parts = [
            f"[{c['doc_name']}#L{c['chunk_index']} score={c['score']}]\n{c['content']}"
            for c in context
        ]
        return "\n\n".join(parts)
