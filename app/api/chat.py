from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import uuid

from app.core.database import get_db
from app.services.chat_service import (
    answer_question,
    create_session,
    get_messages,
    get_sessions,
)

router = APIRouter()


class CreateSessionRequest(BaseModel):
    title: Optional[str] = None


class SendMessageRequest(BaseModel):
    content: str


@router.post("/sessions", status_code=201)
async def new_session(
    body: CreateSessionRequest, db: AsyncSession = Depends(get_db)
):
    session = await create_session(body.title, db)
    return {"id": str(session.id), "title": session.title, "created_at": session.created_at}


@router.get("/sessions")
async def list_sessions(db: AsyncSession = Depends(get_db)):
    sessions = await get_sessions(db)
    return [{"id": str(s.id), "title": s.title, "created_at": s.created_at} for s in sessions]


@router.post("/sessions/{session_id}/messages", status_code=201)
async def send_message(
    session_id: uuid.UUID,
    body: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    if not body.content.strip():
        raise HTTPException(400, "Pesan tidak boleh kosong")
    msg = await answer_question(session_id, body.content.strip(), db)
    return {
        "id": str(msg.id),
        "role": msg.role,
        "content": msg.content,
        "regulation_refs": msg.regulation_refs,
        "created_at": msg.created_at,
    }


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    messages = await get_messages(session_id, db)
    return [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "regulation_refs": m.regulation_refs,
            "created_at": m.created_at,
        }
        for m in messages
    ]
