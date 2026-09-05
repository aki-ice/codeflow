from fastapi import APIRouter

from ai_service.api.deps import CurrentUser, DBSession
from ai_service.schemas.ai import (
    ChatRequest,
    ChatResponse,
    CodeReviewRequest,
    CodeReviewResponse,
    ContextHit,
    ContextSearchRequest,
    DocumentIngest,
    DocumentIngestResponse,
    IssueAnalysisRequest,
    IssueAnalysisResponse,
    ReviewIssueOut,
)
from ai_service.services.embeddings import get_embedding_provider
from ai_service.services.llm import get_llm_client
from ai_service.services.rag_service import RAGService
from ai_service.services.review import CHAT_SYSTEM, run_code_review, run_issue_analysis

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, user: CurrentUser, db: DBSession) -> ChatResponse:
    llm = get_llm_client()
    user_message = body.message
    context_count = 0

    if body.project_id and body.use_rag:
        rag = RAGService(db, get_embedding_provider())
        await rag.vectors.ensure_pgvector()
        context = await rag.search_context(body.project_id, body.message)
        context_count = len(context)
        if context:
            context_prompt = rag.build_context_prompt(context)
            user_message = (
                f"Context from project knowledge base:\n{context_prompt}\n\n"
                f"Question: {body.message}"
            )

    answer = await llm.chat(CHAT_SYSTEM, user_message)
    return ChatResponse(answer=answer, llm=llm.name, context_used=context_count)


@router.post("/code-review", response_model=CodeReviewResponse)
async def code_review(
    body: CodeReviewRequest, user: CurrentUser, db: DBSession
) -> CodeReviewResponse:
    llm = get_llm_client()
    review = await run_code_review(db, llm, body.diff, body.project_id, body.pull_request_id)
    await db.commit()
    return CodeReviewResponse(
        id=review.id,
        summary=review.summary,
        severity=review.severity,
        issues=[ReviewIssueOut(**i) for i in review.result.get("issues", [])],
        llm=llm.name,
        created_at=review.created_at,
    )


@router.post("/issue-analysis", response_model=IssueAnalysisResponse)
async def issue_analysis(
    body: IssueAnalysisRequest, user: CurrentUser, db: DBSession
) -> IssueAnalysisResponse:
    llm = get_llm_client()
    data = await run_issue_analysis(llm, body.title, body.description)
    return IssueAnalysisResponse(
        category=str(data.get("category", "task")),
        priority_suggestion=str(data.get("priority_suggestion", "medium")),
        summary=str(data.get("summary", "")),
        llm=llm.name,
    )


@router.post("/documents", response_model=DocumentIngestResponse)
async def ingest_document(
    body: DocumentIngest, user: CurrentUser, db: DBSession
) -> DocumentIngestResponse:
    rag = RAGService(db, get_embedding_provider())
    await rag.vectors.ensure_pgvector()
    chunks = await rag.ingest(body.project_id, body.name, body.content)
    backend = "pgvector" if rag.vectors.pgvector_available else "python-cosine"
    return DocumentIngestResponse(
        chunks=chunks, embedding_provider=rag.embeddings.name, vector_backend=backend
    )


@router.post("/documents/search", response_model=list[ContextHit])
async def search_context(
    body: ContextSearchRequest, user: CurrentUser, db: DBSession
) -> list[ContextHit]:
    rag = RAGService(db, get_embedding_provider())
    await rag.vectors.ensure_pgvector()
    hits = await rag.search_context(body.project_id, body.query, body.top_k)
    return [ContextHit(**h) for h in hits]
