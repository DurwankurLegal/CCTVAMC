from uuid import UUID
from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel
from app.models.engineer_visit import VisitType


class PartUsed(BaseModel):
    item_id: UUID
    quantity: int
    description: Optional[str] = None


class CheckinRequest(BaseModel):
    lat: float
    lng: float


class CheckoutRequest(BaseModel):
    lat: float
    lng: float
    work_performed: str
    parts_used: List[PartUsed] = []
    customer_feedback: Optional[str] = None


class EngineerVisitCreate(BaseModel):
    ticket_id: Optional[UUID] = None
    amc_contract_id: Optional[UUID] = None
    visit_type: VisitType = VisitType.CORRECTIVE


class EngineerVisitResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    tenant_id: UUID
    ticket_id: Optional[UUID]
    amc_contract_id: Optional[UUID]
    technician_id: UUID
    visit_type: str
    checkin_at: Optional[datetime]
    checkout_at: Optional[datetime]
    checkin_lat: Optional[float]
    checkin_lng: Optional[float]
    work_performed: Optional[str]
    parts_used: List[Any]
    photo_urls: List[Any]
    signature_url: Optional[str]
    is_synced: bool
