import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import TIMESTAMP, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditMemo(Base):
    __tablename__ = "audit_memos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    opd_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("opd_units.id"))
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    finding_ids: Mapped[list | None] = mapped_column(ARRAY(PGUUID))
    storage_path: Mapped[str | None] = mapped_column(Text)
    format: Mapped[str] = mapped_column(String(10), default="docx")
    memo_number: Mapped[str | None] = mapped_column(String(100))
    generated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow)
