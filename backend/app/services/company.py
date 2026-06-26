from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.company import Company
from app.repositories.base import TenantRepository
from app.services.crud_base import make_crud
from app.schemas.company import CompanyCreate, CompanyUpdate

class CompanyRepository(TenantRepository[Company]):
    model = Company

list_companies, get_company, _create_company_raw, _update_company_raw = make_crud(CompanyRepository, Company)

async def create_company(db: AsyncSession, tenant_id: UUID, payload: CompanyCreate) -> Company:
    repo = CompanyRepository(db, tenant_id)
    
    # Check if there are any existing companies for this tenant
    existing_list = await repo.list(limit=100)
    
    is_default = payload.is_default
    if not existing_list:
        # First company is always default
        is_default = True

    # If setting as default, clear others
    if is_default:
        await clear_default_companies(db, tenant_id)

    company = Company(**payload.model_dump())
    company.is_default = is_default
    return await repo.create(company)

async def update_company(db: AsyncSession, tenant_id: UUID, company_id: UUID, payload: CompanyUpdate) -> Company:
    repo = CompanyRepository(db, tenant_id)
    company = await repo.get(company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    data = payload.model_dump(exclude_none=True)
    
    if "is_default" in data:
        new_is_default = data["is_default"]
        if new_is_default:
            await clear_default_companies(db, tenant_id)
        else:
            # If trying to turn default to false, check if other default exists
            existing_list = await repo.list(limit=100)
            other_defaults = [c for c in existing_list if c.is_default and c.id != company_id]
            if not other_defaults:
                # Keep it default, do not allow setting default to false if no other defaults exist
                data["is_default"] = True

    for k, v in data.items():
        setattr(company, k, v)

    return await repo.save(company)

async def clear_default_companies(db: AsyncSession, tenant_id: UUID):
    # Sets is_default = False for all companies of this tenant
    repo = CompanyRepository(db, tenant_id)
    await repo._set_rls_context()
    await db.execute(
        update(Company)
        .where(Company.tenant_id == tenant_id)
        .values(is_default=False)
    )

async def resolve_company_id(db: AsyncSession, tenant_id: UUID, company_id: "Optional[UUID]" = None) -> UUID:
    from typing import Optional
    from uuid import uuid4
    
    if company_id:
        return company_id

    # 1. Query for default company of this tenant
    stmt = select(Company.id).where(Company.tenant_id == tenant_id, Company.is_default == True)
    res = await db.execute(stmt)
    db_company_id = res.scalar_one_or_none()
    if db_company_id:
        return db_company_id

    # 2. Query for first active company of this tenant
    stmt = select(Company.id).where(Company.tenant_id == tenant_id).limit(1)
    res = await db.execute(stmt)
    db_company_id = res.scalar_one_or_none()
    if db_company_id:
        return db_company_id

    # 3. Fallback: Dynamically create a default company for the tenant
    from app.models.tenant import Tenant
    tenant_stmt = select(Tenant).where(Tenant.id == tenant_id)
    tenant_res = await db.execute(tenant_stmt)
    tenant_obj = tenant_res.scalar_one_or_none()
    tenant_name = tenant_obj.name if tenant_obj else "Default Company"

    fallback_company = Company(
        id=uuid4(),
        tenant_id=tenant_id,
        name=tenant_name,
        gst_status="NON_GST",
        is_default=True,
        is_active=True
    )
    db.add(fallback_company)
    await db.flush()
    return fallback_company.id

