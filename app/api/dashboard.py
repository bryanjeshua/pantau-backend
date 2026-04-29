from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.finding import Finding
from app.models.opd import OpdUnit

router = APIRouter()


@router.get("/overview")
async def get_overview(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Finding))
    findings = result.scalars().all()

    type_counts: dict[str, int] = defaultdict(int)
    opd_risk: dict[str, dict] = defaultdict(lambda: {"red": 0, "yellow": 0, "green": 0, "total": 0})

    for f in findings:
        type_counts[f.finding_type] += 1
        if f.opd_id:
            opd_risk[str(f.opd_id)][f.risk_level] += 1
            opd_risk[str(f.opd_id)]["total"] += 1

    top_risk_opds = sorted(
        [{"opd_id": k, **v} for k, v in opd_risk.items()],
        key=lambda x: x["red"] * 2 + x["yellow"],
        reverse=True,
    )[:5]

    return {
        "red_count": sum(1 for f in findings if f.risk_level == "red"),
        "yellow_count": sum(1 for f in findings if f.risk_level == "yellow"),
        "green_count": sum(1 for f in findings if f.risk_level == "green"),
        "total_findings": len(findings),
        "top_risk_opds": top_risk_opds,
        "findings_by_type": dict(type_counts),
    }


@router.get("/opd/{opd_id}")
async def get_opd_dashboard(opd_id: str, db: AsyncSession = Depends(get_db)):
    opd_result = await db.execute(select(OpdUnit).where(OpdUnit.id == opd_id))
    opd = opd_result.scalar_one_or_none()
    if opd is None:
        raise HTTPException(404, "OPD tidak ditemukan")

    findings_result = await db.execute(
        select(Finding).where(Finding.opd_id == opd_id)
    )
    findings = findings_result.scalars().all()

    type_counts: dict[str, int] = defaultdict(int)
    for f in findings:
        type_counts[f.finding_type] += 1

    return {
        "opd_id": str(opd.id),
        "opd_name": opd.name,
        "kabupaten": opd.kabupaten,
        "total_budget": float(opd.total_budget) if opd.total_budget else None,
        "fiscal_year": opd.fiscal_year,
        "red_count": sum(1 for f in findings if f.risk_level == "red"),
        "yellow_count": sum(1 for f in findings if f.risk_level == "yellow"),
        "green_count": sum(1 for f in findings if f.risk_level == "green"),
        "total_findings": len(findings),
        "findings_by_type": dict(type_counts),
    }
