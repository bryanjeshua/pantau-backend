import uuid
from sqlalchemy import String, Text, Numeric, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BudgetItem(Base):
    __tablename__ = "budget_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    opd_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("opd_units.id"))
    item_code: Mapped[str | None] = mapped_column(String(50))
    item_name: Mapped[str] = mapped_column(Text, nullable=False)
    budget_amount: Mapped[float | None] = mapped_column(Numeric(18, 2))
    realized_amount: Mapped[float | None] = mapped_column(Numeric(18, 2))
    item_type: Mapped[str | None] = mapped_column(String(20))
    sub_type: Mapped[str | None] = mapped_column(String(50))
    source_page: Mapped[int | None] = mapped_column(Integer)
    raw_data: Mapped[dict | None] = mapped_column(JSONB)
