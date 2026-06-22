from uuid import UUID
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException, status
from app.models.tenant import Tenant, SubscriptionInvoice, PLAN_LIMITS
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


# Plan price per billing period (INR) for platform subscription invoicing.
PLAN_PRICE = {"starter": 2999.0, "growth": 9999.0, "enterprise": 29999.0}


async def enforce_limit(db: AsyncSession, tenant_id: UUID, resource: str) -> None:
    """Raise 403 if creating one more `resource` (users/sites/technicians) would
    exceed the tenant's plan limit (SRS 4.1 / NFR 5.3). 0 = unlimited."""
    from app.models.user import User, TenantRole
    from app.models.customer import CustomerSite

    tenant = await get_tenant(db, tenant_id)
    limits = PLAN_LIMITS.get(tenant.plan, {})
    cap = limits.get(f"max_{resource}", 0)
    if not cap:
        return
    if resource == "users":
        count = (await db.execute(select(func.count()).where(User.tenant_id == tenant_id))).scalar() or 0
    elif resource == "technicians":
        count = (await db.execute(select(func.count()).where(
            User.tenant_id == tenant_id, User.role == TenantRole.TECHNICIAN))).scalar() or 0
    elif resource == "sites":
        count = (await db.execute(select(func.count()).where(CustomerSite.tenant_id == tenant_id))).scalar() or 0
    else:
        return
    if count >= cap:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Plan limit reached for {resource} ({cap}); upgrade your plan")


async def generate_subscription_invoice(db: AsyncSession, tenant_id: UUID,
                                        period_start: date, period_end: date) -> SubscriptionInvoice:
    tenant = await get_tenant(db, tenant_id)
    seq = (await db.execute(
        select(func.count()).where(SubscriptionInvoice.tenant_id == tenant_id)
    )).scalar() or 0
    inv = SubscriptionInvoice(
        tenant_id=tenant_id,
        invoice_number=f"SUB-{str(tenant_id)[:4].upper()}-{seq + 1:05d}",
        plan=tenant.plan, period_start=period_start, period_end=period_end,
        amount=PLAN_PRICE.get(tenant.plan, 0.0), status="issued",
    )
    db.add(inv)
    await db.flush()
    await db.refresh(inv)
    return inv


async def list_subscription_invoices(db: AsyncSession, tenant_id: UUID):
    return list((await db.execute(
        select(SubscriptionInvoice).where(SubscriptionInvoice.tenant_id == tenant_id)
    )).scalars().all())
