from typing import Optional
from uuid import UUID
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from fastapi import HTTPException, status
from app.models.tenant import Tenant, SubscriptionInvoice, PLAN_LIMITS, TenantStatus
from app.schemas.tenant import TenantCreate, TenantUpdate
from app.services import audit as audit_service


async def _set_rls(db: AsyncSession, tenant_id: UUID) -> None:
    """Scope the RLS session variable to ``tenant_id`` for the current
    transaction so that an audit row for that tenant passes the INSERT WITH
    CHECK policy. Platform-admin actions operate cross-tenant and therefore must
    set this explicitly (the TenantRepository does the same for tenant staff).
    No-op on non-PostgreSQL backends (SQLite in tests)."""
    conn = await db.connection()
    if conn.dialect.name == "postgresql":
        await db.execute(
            text("SELECT set_config('app.tenant_id', :tid, true)"),
            {"tid": str(tenant_id)},
        )


async def list_tenants(
    db: AsyncSession,
    status_filter: Optional[str] = None,
    plan_filter: Optional[str] = None,
    search: Optional[str] = None,
):
    """Platform-admin tenant listing. Unlike tenant-scoped data this returns
    tenants in every lifecycle state (active, suspended, cancelled) so the admin
    console can manage them; optional filters narrow the result set."""
    stmt = select(Tenant)
    if status_filter:
        stmt = stmt.where(Tenant.status == status_filter)
    if plan_filter:
        stmt = stmt.where(Tenant.plan == plan_filter)
    if search:
        like = f"%{search.lower()}%"
        stmt = stmt.where(func.lower(Tenant.name).like(like) | func.lower(Tenant.slug).like(like))
    stmt = stmt.order_by(Tenant.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_tenant(db: AsyncSession, tenant_id):
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return obj


async def create_tenant(db: AsyncSession, payload: TenantCreate,
                        actor_user_id: Optional[UUID] = None) -> Tenant:
    # Slug uniqueness check
    result = await db.execute(select(Tenant).where(Tenant.slug == payload.slug))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already taken")
    tenant = Tenant(**payload.model_dump())
    db.add(tenant)
    await db.flush()
    await db.refresh(tenant)
    await _set_rls(db, tenant.id)
    await audit_service.write_audit(
        db, tenant.id, "tenant", tenant.id, "create",
        before=None, after=audit_service.to_dict(tenant), actor_user_id=actor_user_id)
    return tenant


async def update_tenant(db: AsyncSession, tenant_id, payload: TenantUpdate,
                        actor_user_id: Optional[UUID] = None) -> Tenant:
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
    before, after = audit_service.diff(obj)
    await db.flush()
    await db.refresh(obj)
    if after:
        await _set_rls(db, obj.id)
        await audit_service.write_audit(
            db, obj.id, "tenant", obj.id, "update",
            before=before, after=after, actor_user_id=actor_user_id)
    return obj


# Status lifecycle transitions (SRS 4.1). Each writes an audit row so platform
# actions on a tenant remain on that tenant's tamper-evident chain.
_STATUS_TRANSITIONS = {
    "suspend":  (TenantStatus.SUSPENDED.value, False),
    "activate": (TenantStatus.ACTIVE.value,    True),
    "cancel":   (TenantStatus.CANCELLED.value, False),
}


async def set_tenant_status(db: AsyncSession, tenant_id: UUID, action: str,
                            actor_user_id: Optional[UUID] = None) -> Tenant:
    if action not in _STATUS_TRANSITIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown status action")
    new_status, is_active = _STATUS_TRANSITIONS[action]
    obj = await get_tenant(db, tenant_id)
    before = {"status": obj.status, "is_active": obj.is_active}
    obj.status = new_status
    obj.is_active = is_active
    await db.flush()
    await db.refresh(obj)
    await _set_rls(db, obj.id)
    await audit_service.write_audit(
        db, obj.id, "tenant", obj.id, action,
        before=before, after={"status": new_status, "is_active": is_active},
        actor_user_id=actor_user_id)
    return obj


async def tenant_usage(db: AsyncSession, tenant_id: UUID) -> dict:
    """Current resource counts vs. the tenant's plan limits (0 limit = unlimited)."""
    from app.models.user import User, TenantRole
    from app.models.customer import CustomerSite

    tenant = await get_tenant(db, tenant_id)
    limits = PLAN_LIMITS.get(tenant.plan, {})
    users = (await db.execute(select(func.count()).where(User.tenant_id == tenant_id))).scalar() or 0
    techs = (await db.execute(select(func.count()).where(
        User.tenant_id == tenant_id, User.role == TenantRole.TECHNICIAN))).scalar() or 0
    sites = (await db.execute(select(func.count()).where(CustomerSite.tenant_id == tenant_id))).scalar() or 0

    def _entry(used, cap):
        return {"used": used, "limit": cap, "unlimited": not cap}

    return {
        "tenant_id": str(tenant_id),
        "plan": tenant.plan,
        "users": _entry(users, limits.get("max_users", 0)),
        "technicians": _entry(techs, limits.get("max_technicians", 0)),
        "sites": _entry(sites, limits.get("max_sites", 0)),
    }


async def platform_metrics(db: AsyncSession) -> dict:
    """Aggregate metrics for the platform dashboard: tenant counts by status and
    plan distribution. Platform-admin only."""
    total = (await db.execute(select(func.count()).select_from(Tenant))).scalar() or 0
    by_status_rows = (await db.execute(
        select(Tenant.status, func.count()).group_by(Tenant.status))).all()
    by_plan_rows = (await db.execute(
        select(Tenant.plan, func.count()).group_by(Tenant.plan))).all()
    by_status = {s: c for s, c in by_status_rows}
    return {
        "total_tenants": total,
        "active": by_status.get(TenantStatus.ACTIVE.value, 0),
        "suspended": by_status.get(TenantStatus.SUSPENDED.value, 0),
        "trial": by_status.get(TenantStatus.TRIAL.value, 0),
        "cancelled": by_status.get(TenantStatus.CANCELLED.value, 0),
        "by_status": by_status,
        "by_plan": {p: c for p, c in by_plan_rows},
    }


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
                                        period_start: date, period_end: date,
                                        actor_user_id: Optional[UUID] = None) -> SubscriptionInvoice:
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
    await _set_rls(db, tenant_id)
    await audit_service.write_audit(
        db, tenant_id, "subscription_invoice", inv.id, "create",
        before=None, after={"invoice_number": inv.invoice_number, "plan": inv.plan,
                            "amount": float(inv.amount), "status": inv.status},
        actor_user_id=actor_user_id)
    return inv


async def list_subscription_invoices(db: AsyncSession, tenant_id: UUID):
    return list((await db.execute(
        select(SubscriptionInvoice).where(SubscriptionInvoice.tenant_id == tenant_id)
    )).scalars().all())
