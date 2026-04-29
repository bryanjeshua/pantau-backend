from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db, supabase
from app.models.memo import AuditMemo
from app.schemas.memo import MemoGenerateRequest, MemoResponse
from app.services.memo_service import generate_memo

router = APIRouter()


@router.post("/generate", status_code=201)
async def generate_memo_endpoint(
    body: MemoGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    if not body.finding_ids:
        raise HTTPException(400, "finding_ids tidak boleh kosong")

    valid_formats = {"docx", "pdf"}
    if body.format not in valid_formats:
        raise HTTPException(400, f"Format harus salah satu dari: {valid_formats}")

    memo = await generate_memo(
        finding_ids=body.finding_ids,
        fiscal_year=body.fiscal_year,
        opd_id=body.opd_id,
        fmt=body.format,
        db=db,
    )
    return {"memo_id": str(memo.id), "status": "ready", "memo_number": memo.memo_number}


@router.get("/", response_model=list[MemoResponse])
async def list_memos(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AuditMemo).order_by(AuditMemo.generated_at.desc())
    )
    memos = result.scalars().all()
    return [_to_response(m) for m in memos]


@router.get("/{memo_id}", response_model=MemoResponse)
async def get_memo(memo_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuditMemo).where(AuditMemo.id == memo_id))
    memo = result.scalar_one_or_none()
    if memo is None:
        raise HTTPException(404, "Memo tidak ditemukan")
    return _to_response(memo)


def _to_response(memo: AuditMemo) -> MemoResponse:
    download_url = None
    if memo.storage_path:
        try:
            signed = supabase.storage.from_("memos").create_signed_url(
                memo.storage_path, expires_in=3600
            )
            download_url = signed.get("signedURL") or signed.get("signedUrl")
        except Exception:
            pass

    return MemoResponse(
        id=memo.id,
        opd_id=memo.opd_id,
        fiscal_year=memo.fiscal_year,
        format=memo.format,
        memo_number=memo.memo_number,
        storage_path=memo.storage_path,
        download_url=download_url,
        status="ready" if memo.storage_path else "generating",
        generated_at=memo.generated_at,
    )
