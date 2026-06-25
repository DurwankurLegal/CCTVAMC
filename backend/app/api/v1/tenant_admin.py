from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_permission
from app.schemas.tenant import TenantResponse, TenantUpdate
from app.services import tenant as tenant_service

router = APIRouter()

@router.get("/settings", response_model=TenantResponse)
async def get_tenant_settings(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("tenants:read")),
):
    """Retrieve settings for the logged-in user's tenant."""
    return await tenant_service.get_tenant(db, current_user.tenant_id)

@router.patch("/settings", response_model=TenantResponse)
async def update_tenant_settings(
    payload: TenantUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("tenants:write")),
):
    """Update settings for the logged-in user's tenant."""
    return await tenant_service.update_tenant(
        db, current_user.tenant_id, payload, actor_user_id=current_user.user_id
    )

@router.get("/usage")
async def get_tenant_usage(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("tenants:read")),
):
    """Resource usage vs. plan limits for the logged-in user's tenant."""
    return await tenant_service.tenant_usage(db, current_user.tenant_id)

@router.get("/subscription-invoices")
async def get_subscription_invoices(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("tenants:read")),
):
    """List platform subscription invoices for the logged-in user's tenant."""
    invoices = await tenant_service.list_subscription_invoices(db, current_user.tenant_id)
    return [{"id": str(r.id), "invoice_number": r.invoice_number, "plan": r.plan,
             "amount": float(r.amount), "status": r.status} for r in invoices]


@router.get("/settings/export")
async def export_own_tenant(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("tenants:read")),
):
    """Self-service tenant data export for tenant administrators."""
    from app.services.offboarding import export_tenant_data
    from fastapi import HTTPException
    data = await export_tenant_data(db, current_user.tenant_id)
    if not data:
        raise HTTPException(status_code=404, detail="Tenant data not found")
    return data

