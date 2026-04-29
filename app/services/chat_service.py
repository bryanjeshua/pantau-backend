import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.chat import ChatSession, ChatMessage
from app.services.gemini_service import generate_chat_response
from app.services.vector_service import search_regulations


async def create_session(title: str | None, db: AsyncSession) -> ChatSession:
    session = ChatSession(title=title or "Sesi Konsultasi Baru")
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_sessions(db: AsyncSession) -> list[ChatSession]:
    result = await db.execute(
        select(ChatSession).order_by(ChatSession.created_at.desc())
    )
    return result.scalars().all()


async def get_messages(session_id: uuid.UUID, db: AsyncSession) -> list[ChatMessage]:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    return result.scalars().all()


async def answer_question(
    session_id: uuid.UUID, question: str, db: AsyncSession
) -> ChatMessage:
    user_msg = ChatMessage(session_id=session_id, role="user", content=question)
    db.add(user_msg)

    chunks = await search_regulations(question, db, top_k=5)
    result = generate_chat_response(question, chunks)

    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=result["answer"],
        regulation_refs=result.get("regulation_refs"),
    )
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(assistant_msg)
    return assistant_msg
