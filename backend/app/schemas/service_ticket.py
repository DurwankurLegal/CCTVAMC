from uuid import UUID
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.models.service_ticket import TicketStatus, TicketPriority


class ServiceTicketCreate(BaseModel):
    company_id: Optional[UUID] = None
    customer_id: UUID
    site_id: Optional[UUID] = None
    asset_id: Optional[UUID] = None
    amc_contract_id: Optional[UUID] = None
    priority: TicketPriority = TicketPriority.MEDIUM
    complaint: str


class ServiceTicketUpdate(BaseModel):
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    assigned_to: Optional[UUID] = None
    resolution_notes: Optional[str] = None


class ServiceTicketResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    tenant_id: UUID
    company_id: UUID
    ticket_number: str
    customer_id: UUID
    status: str
    priority: str
    complaint: str
    resolution_notes: Optional[str]
    assigned_to: Optional[UUID]
    sla_due_at: Optional[datetime]
    sla_breached: bool
    resolved_at: Optional[datetime]
    closed_at: Optional[datetime]
    created_at: datetime
