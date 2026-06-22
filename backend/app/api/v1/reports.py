from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser
from app.services import reports as report_service

router = APIRouter()


@router.get("/dashboard")
async def dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Role-aware KPI dashboard with pre-aggregated metrics."""
    return await report_service.dashboard_kpis(db, current_user.tenant_id)


@router.get("/sla")
async def sla_report(
    from_date: date = Query(...),
    to_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """SLA compliance report for a date range."""
    return await report_service.ticket_sla_report(db, current_user.tenant_id, from_date, to_date)
