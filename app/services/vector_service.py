import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.services.gemini_service import embed_text


def _vec_str(embedding: list[float]) -> str:
    return f"[{','.join(str(x) for x in embedding)}]"


async def search_regulations(query: str, db: AsyncSession, top_k: int = 5) -> list[dict]:
    embedding = embed_text(query, task_type="retrieval_query")

    emb_str = _vec_str(embedding)
    result = await db.execute(
        text(
            "SELECT id, peraturan_number, pasal, content, "
            "1 - (embedding <=> CAST(:emb AS vector)) AS similarity "
            "FROM regulation_chunks WHERE embedding IS NOT NULL "
            "ORDER BY embedding <=> CAST(:emb AS vector) LIMIT :k"
        ),
        {"emb": emb_str, "k": top_k},
    )
    return [
        {
            "id": str(row.id),
            "peraturan_number": row.peraturan_number,
            "pasal": row.pasal,
            "content": row.content,
            "similarity": float(row.similarity),
        }
        for row in result.fetchall()
    ]


async def index_chunk(chunk: dict, db: AsyncSession) -> None:
    embedding = embed_text(chunk["content"], task_type="retrieval_document")

    await db.execute(
        text(
            "INSERT INTO regulation_chunks "
            "(id, regulation_id, peraturan_number, pasal, content, embedding, topic_tags) "
            "VALUES (:id, :regulation_id, :peraturan_number, :pasal, :content, CAST(:emb AS vector), :tags)"
        ),
        {
            "id": str(uuid.uuid4()),
            "regulation_id": chunk["regulation_id"],
            "peraturan_number": chunk["peraturan_number"],
            "pasal": chunk["pasal"],
            "content": chunk["content"],
            "emb": _vec_str(embedding),
            "tags": chunk.get("topic_tags", []),
        },
    )
    await db.commit()
