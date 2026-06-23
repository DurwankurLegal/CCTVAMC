from typing import List
from uuid import UUID
from datetime import date
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_platform_admin
from app.schemas.tenant import TenantCreate, TenantUpdate, TenantResponse
from app.services import tenant as tenant_service

router = APIRouter()


class SubscriptionInvoiceRequest(BaseModel):
    period_start: date
    period_end: date


@router.get("", response_model=List[TenantResponse])
async def list_tenants(
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_platform_admin),
):
    return await tenant_service.list_tenants(db)


@router.post("", response_model=TenantResponse, status_code=201)
async def create_tenant(
    payload: TenantCreate, db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_platform_admin),
):
    return await tenant_service.create_tenant(db, payload)


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID, db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_platform_admin),
):
    return await tenant_service.get_tenant(db, tenant_id)


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: UUID, payload: TenantUpdate, db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_platform_admin),
):
    return await tenant_service.update_tenant(db, tenant_id, payload)


@router.post("/{tenant_id}/subscription-invoices", status_code=201)
async def create_subscription_invoice(
    tenant_id: UUID, payload: SubscriptionInvoiceRequest, db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_platform_admin),
):
    """Generate a platform-level subscription invoice for a tenant (SRS 4.1)."""
    inv = await tenant_service.generate_subscription_invoice(
        db, tenant_id, payload.period_start, payload.period_end)
    return {"id": str(inv.id), "invoice_number": inv.invoice_number,
            "plan": inv.plan, "amount": float(inv.amount)}


@router.get("/{tenant_id}/subscription-invoices")
async def list_subscription_invoices(
    tenant_id: UUID, db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_platform_admin),
):
    rows = await tenant_service.list_subscription_invoices(db, tenant_id)
    return [{"id": str(r.id), "invoice_number": r.invoice_number, "plan": r.plan,
             "amount": float(r.amount), "status": r.status} for r in rows]
