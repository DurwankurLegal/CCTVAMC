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


_LEAD_TO_CUSTOMER_CATEGORY = {
    "chs": CustomerCategory.CHS,
    "commercial": CustomerCategory.COMMERCIAL,
    "single_shop": CustomerCategory.SINGLE_SHOP,
}


async def convert_to_customer(db: AsyncSession, tenant_id: UUID, lead_id: UUID) -> Customer:
    """One-click lead → customer conversion.

    Carries the lead's category through to the Customer Master and creates an
    initial draft Quotation in the same action (SRS 4.2), with no data re-entry.
    """
    repo = LeadRepository(db, tenant_id)
    lead = await repo.get(lead_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    if lead.status == LeadStatus.CONVERTED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Lead already converted")

    from app.services.customer import CustomerRepository

    category = _LEAD_TO_CUSTOMER_CATEGORY.get(lead.category, CustomerCategory.COMMERCIAL)
    customer = Customer(
        name=lead.name,
        category=category,
        phone=lead.phone,
        email=lead.email,
        address=lead.address,
    )
    customer = await CustomerRepository(db, tenant_id).create(customer)

    # Create an initial draft quotation linked to both the customer and the lead.
    from app.services.quotation import create_quotation
    from app.schemas.quotation import QuotationCreate
    await create_quotation(db, tenant_id, QuotationCreate(
        company_id=lead.company_id, customer_id=customer.id, lead_id=lead.id, line_items=[],
    ))

    lead.status = LeadStatus.CONVERTED
    lead.converted_customer_id = customer.id
    await repo.save(lead)
    return customer
