from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.customer import Customer
from app.repositories.base import TenantRepository
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerResponse


class CustomerRepository(TenantRepository[Customer]):
    model = Customer


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
