import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.budget_item import BudgetItem
from app.models.transaction import ProcurementTransaction
from app.models.finding import Finding
from app.services.gemini_service import classify_risk
from app.services.vector_service import search_regulations


def _budget_item_text(item: BudgetItem) -> str:
    parts = [f"Nama item: {item.item_name}"]
    if item.item_code:
        parts.append(f"Kode rekening: {item.item_code}")
    if item.item_type:
        parts.append(f"Jenis belanja: {item.item_type}")
    if item.sub_type:
        parts.append(f"Sub jenis: {item.sub_type}")
    if item.budget_amount is not None:
        parts.append(f"Nilai anggaran: Rp{item.budget_amount:,.0f}")
    if item.realized_amount is not None:
        parts.append(f"Nilai realisasi: Rp{item.realized_amount:,.0f}")
    return "\n".join(parts)


def _transaction_text(tx: ProcurementTransaction) -> str:
    parts = [f"Deskripsi pengadaan: {tx.item_description}"]
    if tx.category:
        parts.append(f"Kategori: {tx.category}")
    if tx.procurement_method:
        parts.append(f"Metode pengadaan: {tx.procurement_method}")
    if tx.contract_value is not None:
        parts.append(f"Nilai kontrak: Rp{tx.contract_value:,.0f}")
    if tx.contract_number:
        parts.append(f"Nomor kontrak: {tx.contract_number}")
    return "\n".join(parts)


async def scan_document(document_id: uuid.UUID, db: AsyncSession) -> int:
    finding_count = 0

    budget_result = await db.execute(
        select(BudgetItem).where(BudgetItem.document_id == document_id)
    )
    budget_items = budget_result.scalars().all()

    for item in budget_items:
        item_text = _budget_item_text(item)
        chunks = await search_regulations(item_text, db, top_k=5)
        classification = classify_risk(item_text, chunks)

        if classification["risk_level"] in ("red", "yellow"):
            finding = Finding(
                document_id=document_id,
                budget_item_id=item.id,
                source="compliance_scan",
                finding_type=classification.get("title", "Potensi Pelanggaran Regulasi"),
                risk_level=classification["risk_level"],
                title=classification["title"],
                description=classification["description"],
                regulation_refs=classification.get("regulation_refs"),
                ai_explanation=classification.get("ai_explanation"),
                confidence_score=classification.get("confidence_score"),
            )
            db.add(finding)
            finding_count += 1

    tx_result = await db.execute(
        select(ProcurementTransaction).where(
            ProcurementTransaction.document_id == document_id
        )
    )
    transactions = tx_result.scalars().all()

    for tx in transactions:
        tx_text = _transaction_text(tx)
        chunks = await search_regulations(tx_text, db, top_k=5)
        classification = classify_risk(tx_text, chunks)

        if classification["risk_level"] in ("red", "yellow"):
            finding = Finding(
                document_id=document_id,
                transaction_id=tx.id,
                source="compliance_scan",
                finding_type=classification.get("title", "Potensi Pelanggaran Pengadaan"),
                risk_level=classification["risk_level"],
                title=classification["title"],
                description=classification["description"],
                regulation_refs=classification.get("regulation_refs"),
                ai_explanation=classification.get("ai_explanation"),
                confidence_score=classification.get("confidence_score"),
            )
            db.add(finding)
            finding_count += 1

    await db.commit()
    return finding_count
