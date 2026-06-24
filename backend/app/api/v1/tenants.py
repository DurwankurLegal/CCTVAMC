from typing import List, Optional
from uuid import UUID
from datetime import date
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_platform_admin
from app.schemas.tenant import (
    TenantCreate, TenantUpdate, TenantResponse,
    TenantProvisionRequest, TenantProvisionResponse, ProvisionedAdmin,
)
from app.services import tenant as tenant_service

router = APIRouter()


class SubscriptionInvoiceRequest(BaseModel):
    period_start: date
    period_end: date


@router.get("/platform/metrics")
async def platform_metrics(
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_platform_admin),
):
    """Aggregate tenant metrics for the platform-admin dashboard."""
    return await tenant_service.platform_metrics(db)


@router.get("", response_model=List[TenantResponse])
async def list_tenants(
    status: Optional[str] = Query(None, description="Filter by lifecycle status"),
    plan: Optional[str] = Query(None, description="Filter by subscription plan"),
    search: Optional[str] = Query(None, description="Search name/slug"),
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_platform_admin),
):
    return await tenant_service.list_tenants(db, status_filter=status, plan_filter=plan, search=search)


@router.post("", response_model=TenantResponse, status_code=201)
async def create_tenant(
    payload: TenantCreate, db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_platform_admin),
):
    return await tenant_service.create_tenant(db, payload, actor_user_id=user.user_id)


@router.post("/provision", response_model=TenantProvisionResponse, status_code=201)
async def provision_tenant(
    payload: TenantProvisionRequest, db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_platform_admin),
):
    """Onboard a company in one action: tenant + first admin + workspace defaults.
    Returns the first admin's one-time temp password (shown once; not retrievable)."""
    from app.services.provisioning import provision_tenant as _provision
    result = await _provision(db, payload, actor_user_id=user.user_id)
    return TenantProvisionResponse(
        tenant=result.tenant,
        first_admin=(
            ProvisionedAdmin(
                id=result.first_admin.id,
                email=result.first_admin.email,
                must_change_password=result.first_admin.must_change_password,
            ) if result.first_admin else None
        ),
        temp_password=result.temp_password,
    )


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID, db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_platform_admin),
):
    return await tenant_service.get_tenant(db, tenant_id)


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: UUID, payload: TenantUpdate, db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_platform_admin),
):
    return await tenant_service.update_tenant(db, tenant_id, payload, actor_user_id=user.user_id)


async def _status_transition(tenant_id: UUID, action: str, db: AsyncSession, user: CurrentUser):
    return await tenant_service.set_tenant_status(db, tenant_id, action, actor_user_id=user.user_id)


@router.post("/{tenant_id}/suspend", response_model=TenantResponse)
async def suspend_tenant(
    tenant_id: UUID, db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_platform_admin),
):
    return await _status_transition(tenant_id, "suspend", db, user)


@router.post("/{tenant_id}/activate", response_model=TenantResponse)
async def activate_tenant(
    tenant_id: UUID, db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_platform_admin),
):
    return await _status_transition(tenant_id, "activate", db, user)


@router.post("/{tenant_id}/cancel", response_model=TenantResponse)
async def cancel_tenant(
    tenant_id: UUID, db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_platform_admin),
):
    return await _status_transition(tenant_id, "cancel", db, user)


@router.get("/{tenant_id}/usage")
async def tenant_usage(
    tenant_id: UUID, db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_platform_admin),
):
    """Resource usage vs. plan limits (users, technicians, sites)."""
    return await tenant_service.tenant_usage(db, tenant_id)


@router.post("/{tenant_id}/subscription-invoices", status_code=201)
async def create_subscription_invoice(
    tenant_id: UUID, payload: SubscriptionInvoiceRequest, db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_platform_admin),
):
    """Generate a platform-level subscription invoice for a tenant (SRS 4.1)."""
    inv = await tenant_service.generate_subscription_invoice(
        db, tenant_id, payload.period_start, payload.period_end, actor_user_id=user.user_id)
    return {"id": str(inv.id), "invoice_number": inv.invoice_number,
            "plan": inv.plan, "amount": float(inv.amount), "status": inv.status}


@router.get("/{tenant_id}/subscription-invoices")
async def list_subscription_invoices(
    tenant_id: UUID, db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_platform_admin),
):
    rows = await tenant_service.list_subscription_invoices(db, tenant_id)
    return [{"id": str(r.id), "invoice_number": r.invoice_number, "plan": r.plan,
             "amount": float(r.amount), "status": r.status} for r in rows]
