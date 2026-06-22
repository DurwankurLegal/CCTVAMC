from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.customer import Customer, CustomerContact
from app.repositories.base import TenantRepository
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerResponse, ContactCreate


class CustomerRepository(TenantRepository[Customer]):
    model = Customer


class ContactRepository(TenantRepository[CustomerContact]):
    model = CustomerContact


async def list_customers(db: AsyncSession, tenant_id: UUID, offset: int, limit: int):
    repo = CustomerRepository(db, tenant_id)
    return await repo.list(offset=offset, limit=limit)


async def get_customer(db: AsyncSession, tenant_id: UUID, customer_id: UUID) -> Customer:
    repo = CustomerRepository(db, tenant_id)
    obj = await repo.get(customer_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return obj


async def create_customer(db: AsyncSession, tenant_id: UUID, payload: CustomerCreate) -> Customer:
    repo = CustomerRepository(db, tenant_id)
    obj = Customer(**payload.model_dump())
    return await repo.create(obj)


async def update_customer(db: AsyncSession, tenant_id: UUID, customer_id: UUID, payload: CustomerUpdate) -> Customer:
    repo = CustomerRepository(db, tenant_id)
    obj = await repo.get(customer_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    for key, val in payload.model_dump(exclude_none=True).items():
        setattr(obj, key, val)
    return await repo.save(obj)


async def add_contact(db: AsyncSession, tenant_id: UUID, customer_id: UUID, payload: ContactCreate) -> CustomerContact:
    # Ensure the customer exists / is in-tenant.
    if not await CustomerRepository(db, tenant_id).get(customer_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    contact = CustomerContact(customer_id=customer_id, **payload.model_dump())
    return await ContactRepository(db, tenant_id).create(contact)


async def list_contacts(db: AsyncSession, tenant_id: UUID, customer_id: UUID):
    result = await db.execute(
        select(CustomerContact).where(
            CustomerContact.tenant_id == tenant_id,
            CustomerContact.customer_id == customer_id,
        )
    )
    return list(result.scalars().all())


async def interaction_history(db: AsyncSession, tenant_id: UUID, customer_id: UUID) -> dict:
    """Aggregate a customer's leads, tickets, invoices and visits (SRS 4.3)."""
    from app.models.lead import Lead
    from app.models.service_ticket import ServiceTicket
    from app.models.invoice import Invoice
    from app.models.quotation import Quotation

    if not await CustomerRepository(db, tenant_id).get(customer_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    async def _rows(model, **extra):
        stmt = select(model).where(model.tenant_id == tenant_id)
        for k, v in extra.items():
            stmt = stmt.where(getattr(model, k) == v)
        return list((await db.execute(stmt)).scalars().all())

    leads = await _rows(Lead, converted_customer_id=customer_id)
    tickets = await _rows(ServiceTicket, customer_id=customer_id)
    invoices = await _rows(Invoice, customer_id=customer_id)
    quotations = await _rows(Quotation, customer_id=customer_id)
    return {
        "leads": [{"id": str(x.id), "status": x.status} for x in leads],
        "tickets": [{"id": str(x.id), "number": x.ticket_number, "status": x.status} for x in tickets],
        "invoices": [{"id": str(x.id), "number": x.invoice_number, "status": x.status,
                      "total": float(x.total_amount)} for x in invoices],
        "quotations": [{"id": str(x.id), "number": x.quotation_number, "status": x.status} for x in quotations],
    }
