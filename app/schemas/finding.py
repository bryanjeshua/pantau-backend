from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import uuid


class RegulationRefSchema(BaseModel):
    peraturan: str
    pasal: str
    isi: str


class FindingResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    budget_item_id: Optional[uuid.UUID] = None
    transaction_id: Optional[uuid.UUID] = None
    source: str
    finding_type: str
    risk_level: str
    title: str
    description: str
    regulation_refs: Optional[list[RegulationRefSchema]] = None
    evidence: Optional[dict] = None
    ai_explanation: Optional[str] = None
    confidence_score: Optional[float] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class FindingUpdateRequest(BaseModel):
    status: str  # "confirmed" or "dismissed"


class FindingSummaryResponse(BaseModel):
    total: int
    red: int
    yellow: int
    green: int
    pending: int
    confirmed: int
    dismissed: int
