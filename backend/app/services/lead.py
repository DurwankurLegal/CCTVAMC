from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.lead import Lead, LeadStatus
from app.models.customer import Customer, CustomerCategory
from app.repositories.base import TenantRepository
from app.schemas.lead import LeadCreate, LeadUpdate
from app.services.crud_base import make_crud


class LeadRepository(TenantRepository[Lead]):
    model = Lead


list_leads, get_lead, _create_lead, update_lead = make_crud(LeadRepository, Lead)


async def create_lead(db: AsyncSession, tenant_id: UUID, payload: LeadCreate) -> Lead:
    return await _create_lead(db, tenant_id, payload)


async def convert_to_customer(db: AsyncSession, tenant_id: UUID, lead_id: UUID) -> Customer:
    """One-click lead → customer conversion."""
    repo = LeadRepository(db, tenant_id)
    lead = await repo.get(lead_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    if lead.status == LeadStatus.CONVERTED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Lead already converted")

    from app.repositories.base import TenantRepository as TR
    from app.models.customer import Customer

    class CustRepo(TR[Customer]):
        model = Customer

    customer = Customer(
        name=lead.name,
        category=CustomerCategory.COMMERCIAL,
        phone=lead.phone,
        email=lead.email,
        address=lead.address,
    )
    customer = await CustRepo(db, tenant_id).create(customer)

    lead.status = LeadStatus.CONVERTED
    lead.converted_customer_id = customer.id
    await repo.save(lead)
    return customer
