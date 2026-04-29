import uuid
from sqlalchemy import String, Numeric, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class OpdUnit(Base):
    __tablename__ = "opd_units"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    opd_code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kabupaten: Mapped[str] = mapped_column(String(255), nullable=False)
    total_budget: Mapped[float | None] = mapped_column(Numeric(18, 2))
    fiscal_year: Mapped[int | None] = mapped_column(Integer)
