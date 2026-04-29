from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.core.database import get_db
from app.models.finding import Finding
from app.schemas.finding import FindingResponse, FindingSummaryResponse, FindingUpdateRequest

router = APIRouter()


@router.get("/summary", response_model=FindingSummaryResponse)
async def get_findings_summary(
    document_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Finding)
    if document_id:
        query = query.where(Finding.document_id == document_id)

    result = await db.execute(query)
    findings = result.scalars().all()

    return FindingSummaryResponse(
        total=len(findings),
        red=sum(1 for f in findings if f.risk_level == "red"),
        yellow=sum(1 for f in findings if f.risk_level == "yellow"),
        green=sum(1 for f in findings if f.risk_level == "green"),
        pending=sum(1 for f in findings if f.status == "pending"),
        confirmed=sum(1 for f in findings if f.status == "confirmed"),
        dismissed=sum(1 for f in findings if f.status == "dismissed"),
    )


@router.get("/", response_model=list[FindingResponse])
async def list_findings(
    document_id: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Finding).order_by(Finding.created_at.desc())
    if document_id:
        query = query.where(Finding.document_id == document_id)
    if risk_level:
        query = query.where(Finding.risk_level == risk_level)
    if status:
        query = query.where(Finding.status == status)
    if source:
        query = query.where(Finding.source == source)
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{finding_id}", response_model=FindingResponse)
async def get_finding(finding_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Finding).where(Finding.id == finding_id))
    finding = result.scalar_one_or_none()
    if finding is None:
        raise HTTPException(404, "Temuan tidak ditemukan")
    return finding


@router.patch("/{finding_id}/status", response_model=FindingResponse)
async def update_finding_status(
    finding_id: str,
    body: FindingUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    valid_statuses = {"confirmed", "dismissed", "pending"}
    if body.status not in valid_statuses:
        raise HTTPException(400, f"Status harus salah satu dari: {valid_statuses}")

    result = await db.execute(select(Finding).where(Finding.id == finding_id))
    finding = result.scalar_one_or_none()
    if finding is None:
        raise HTTPException(404, "Temuan tidak ditemukan")

    finding.status = body.status
    if body.status == "confirmed":
        from datetime import datetime, timezone
        finding.confirmed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(finding)
    return finding
