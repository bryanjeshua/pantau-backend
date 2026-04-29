import io
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import supabase
import app.models  # ensure all FK targets are registered in SQLAlchemy metadata
from app.models.document import Document
from app.models.budget_item import BudgetItem
from app.models.vendor import Vendor
from app.models.transaction import ProcurementTransaction
from app.services.gemini_service import extract_document


def _prepare_file_input(file_bytes: bytes, filename: str) -> tuple[bytes | str, str]:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext == "pdf":
        return file_bytes, "application/pdf"
    if ext in ("xlsx", "xls"):
        import pandas as pd
        df_dict = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)
        parts = [f"=== {name} ===\n{df.to_csv(index=False)}" for name, df in df_dict.items()]
        return "\n\n".join(parts), "text/plain"
    if ext == "csv":
        return file_bytes, "text/csv"
    if ext == "txt":
        return file_bytes.decode("utf-8", errors="replace"), "text/plain"
    return file_bytes, "application/octet-stream"


async def _get_or_create_vendor(tx: dict, db: AsyncSession) -> Vendor | None:
    vendor_name = tx.get("vendor_name")
    if not vendor_name:
        return None
    result = await db.execute(select(Vendor).where(Vendor.name == vendor_name))
    vendor = result.scalar_one_or_none()
    if vendor is None:
        vendor = Vendor(
            name=vendor_name,
            npwp=tx.get("vendor_npwp"),
            address=tx.get("vendor_address"),
        )
        db.add(vendor)
        await db.flush()
    return vendor


def _parse_date(value: str | None):
    if not value:
        return None
    from datetime import date
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


async def extract_and_save(document_id: uuid.UUID, db: AsyncSession) -> int:
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one()

    file_bytes = supabase.storage.from_("documents").download(doc.storage_path)
    file_content, mime_type = _prepare_file_input(file_bytes, doc.filename)

    extracted = extract_document(file_content, mime_type, doc.document_type)

    if doc.document_type in ("apbd", "spj"):
        items = extracted.get("items", [])
        for item in items:
            budget_item = BudgetItem(
                document_id=document_id,
                item_code=item.get("item_code"),
                item_name=item["item_name"],
                budget_amount=item.get("budget_amount"),
                realized_amount=item.get("realized_amount"),
                item_type=item.get("item_type"),
                sub_type=item.get("sub_type"),
                raw_data=item,
            )
            db.add(budget_item)
        await db.commit()
        return len(items)

    if doc.document_type == "procurement":
        transactions = extracted.get("transactions", [])
        for tx in transactions:
            vendor = await _get_or_create_vendor(tx, db)
            pt = ProcurementTransaction(
                document_id=document_id,
                vendor_id=vendor.id if vendor else None,
                contract_number=tx.get("contract_number"),
                item_description=tx["item_description"],
                category=tx.get("category"),
                procurement_method=tx.get("procurement_method"),
                contract_value=tx.get("contract_value"),
                contract_date=_parse_date(tx.get("contract_date")),
                work_start_date=_parse_date(tx.get("work_start_date")),
                work_end_date=_parse_date(tx.get("work_end_date")),
                spj_date=_parse_date(tx.get("spj_date")),
                payment_date=_parse_date(tx.get("payment_date")),
                raw_data=tx,
            )
            db.add(pt)
        await db.commit()
        return len(transactions)

    return 0
