from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Union

from app.core.database import get_db, supabase
from app.models.document import Document
from app.models.budget_item import BudgetItem
from app.models.transaction import ProcurementTransaction
from app.pipelines.document_pipeline import process_document
from app.schemas.document import (
    BudgetItemResponse,
    DocumentResponse,
    DocumentUploadResponse,
    TransactionResponse,
)

router = APIRouter()

VALID_TYPES = {"apbd", "spj", "procurement"}


@router.post("/upload", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    document_type: str = Form(...),
    fiscal_year: int = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if document_type not in VALID_TYPES:
        raise HTTPException(400, f"document_type harus salah satu dari: {VALID_TYPES}")

    doc = Document(
        filename=file.filename,
        document_type=document_type,
        fiscal_year=fiscal_year,
        status="pending",
    )
    db.add(doc)
    await db.flush()

    file_bytes = await file.read()
    storage_path = f"{doc.id}/{file.filename}"

    try:
        supabase.storage.from_("documents").upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": file.content_type or "application/octet-stream"},
        )
    except Exception as exc:
        await db.rollback()
        raise HTTPException(500, f"Gagal mengunggah file: {exc}")

    doc.storage_path = storage_path
    await db.commit()

    background_tasks.add_task(process_document, str(doc.id))

    return DocumentUploadResponse(document_id=doc.id, status="pending")


@router.get("/", response_model=list[DocumentResponse])
async def list_documents(
    status: Optional[str] = Query(None),
    document_type: Optional[str] = Query(None),
    fiscal_year: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Document).order_by(Document.uploaded_at.desc())
    if status:
        query = query.where(Document.status == status)
    if document_type:
        query = query.where(Document.document_type == document_type)
    if fiscal_year:
        query = query.where(Document.fiscal_year == fiscal_year)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(404, "Dokumen tidak ditemukan")
    return doc


@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(404, "Dokumen tidak ditemukan")

    if doc.storage_path:
        try:
            supabase.storage.from_("documents").remove([doc.storage_path])
        except Exception:
            pass

    await db.delete(doc)
    await db.commit()


@router.get("/{document_id}/items")
async def get_document_items(
    document_id: str, db: AsyncSession = Depends(get_db)
) -> list[Union[BudgetItemResponse, TransactionResponse]]:
    doc_result = await db.execute(select(Document).where(Document.id == document_id))
    doc = doc_result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(404, "Dokumen tidak ditemukan")

    if doc.document_type in ("apbd", "spj"):
        result = await db.execute(
            select(BudgetItem).where(BudgetItem.document_id == document_id)
        )
        return [BudgetItemResponse.model_validate(i) for i in result.scalars().all()]

    if doc.document_type == "procurement":
        result = await db.execute(
            select(ProcurementTransaction).where(
                ProcurementTransaction.document_id == document_id
            )
        )
        return [TransactionResponse.model_validate(t) for t in result.scalars().all()]

    return []
