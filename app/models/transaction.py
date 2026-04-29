import uuid
from datetime import date
from sqlalchemy import String, Text, Numeric, Integer, Date, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ProcurementTransaction(Base):
    __tablename__ = "procurement_transactions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    opd_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("opd_units.id"))
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vendors.id"))
    contract_number: Mapped[str | None] = mapped_column(String(100))
    item_description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(50))
    procurement_method: Mapped[str | None] = mapped_column(String(50))
    contract_value: Mapped[float | None] = mapped_column(Numeric(18, 2))
    shsr_benchmark: Mapped[float | None] = mapped_column(Numeric(18, 2))
    contract_date: Mapped[date | None] = mapped_column(Date)
    work_start_date: Mapped[date | None] = mapped_column(Date)
    work_end_date: Mapped[date | None] = mapped_column(Date)
    spj_date: Mapped[date | None] = mapped_column(Date)
    payment_date: Mapped[date | None] = mapped_column(Date)
    fiscal_year: Mapped[int | None] = mapped_column(Integer)
    raw_data: Mapped[dict | None] = mapped_column(JSONB)
