from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantUpdate


async def list_tenants(db: AsyncSession):
    result = await db.execute(select(Tenant).where(Tenant.is_active == True))
    return list(result.scalars().all())


async def get_tenant(db: AsyncSession, tenant_id):
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return obj


async def create_tenant(db: AsyncSession, payload: TenantCreate) -> Tenant:
    # Slug uniqueness check
    result = await db.execute(select(Tenant).where(Tenant.slug == payload.slug))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already taken")
    tenant = Tenant(**payload.model_dump())
    db.add(tenant)
    await db.flush()
    await db.refresh(tenant)
    return tenant


async def update_tenant(db: AsyncSession, tenant_id, payload: TenantUpdate) -> Tenant:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        if k == "branding":
            obj.branding = {**obj.branding, **v}
        elif k == "settings":
            obj.settings = {**obj.settings, **v}
        else:
            setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj
