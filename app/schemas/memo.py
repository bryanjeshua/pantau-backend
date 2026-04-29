from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import uuid


class MemoGenerateRequest(BaseModel):
    opd_id: Optional[uuid.UUID] = None
    fiscal_year: int
    finding_ids: list[uuid.UUID]
    format: str = "docx"


class MemoResponse(BaseModel):
    id: uuid.UUID
    opd_id: Optional[uuid.UUID] = None
    fiscal_year: int
    format: str
    memo_number: Optional[str] = None
    storage_path: Optional[str] = None
    download_url: Optional[str] = None
    status: str
    generated_at: datetime

    model_config = {"from_attributes": True}
