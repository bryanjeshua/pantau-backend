from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import uuid


class DocumentUploadResponse(BaseModel):
    document_id: uuid.UUID
    status: str


class DocumentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    document_type: str
    fiscal_year: int
    status: str
    page_count: Optional[int] = None
    item_count: Optional[int] = None
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}


class BudgetItemResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    item_code: Optional[str] = None
    item_name: str
    budget_amount: Optional[float] = None
    realized_amount: Optional[float] = None
    item_type: Optional[str] = None
    sub_type: Optional[str] = None

    model_config = {"from_attributes": True}


class TransactionResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    contract_number: Optional[str] = None
    item_description: str
    category: Optional[str] = None
    procurement_method: Optional[str] = None
    contract_value: Optional[float] = None
    vendor_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}
