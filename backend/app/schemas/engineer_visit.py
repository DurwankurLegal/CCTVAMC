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
    # Allow admin/coordinator to assign the visit to a specific technician.
    # When omitted the API falls back to current_user.user_id.
    technician_id: Optional[UUID] = None


class EngineerVisitUpdate(BaseModel):
    """Partial update — only supplied fields are applied."""
    visit_type: Optional[VisitType] = None
    ticket_id: Optional[UUID] = None
    amc_contract_id: Optional[UUID] = None
    technician_id: Optional[UUID] = None
    work_performed: Optional[str] = None
    customer_feedback: Optional[str] = None
    # Admin/manager time-override fields (bypass GPS geofence for corrections)
    checkin_at: Optional[datetime] = None
    checkout_at: Optional[datetime] = None


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
    checkout_lat: Optional[float]
    checkout_lng: Optional[float]
    work_performed: Optional[str]
    parts_used: List[Any]
    photo_urls: List[Any]
    signature_url: Optional[str]
    customer_feedback: Optional[str]
    is_synced: bool
