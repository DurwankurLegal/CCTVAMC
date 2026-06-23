from datetime import date
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser
from app.services import reports as report_service

router = APIRouter()

# Report key -> (title, async producer returning a list[dict])
_REPORTS = {
    "lead-conversion": ("Lead Conversion", lambda db, t: report_service.lead_conversion_report(db, t)),
    "revenue-by-customer": ("Revenue by Customer", lambda db, t: report_service.revenue_by_customer(db, t)),
    "technician-productivity": ("Technician Productivity", lambda db, t: report_service.technician_productivity(db, t)),
    "inventory-consumption": ("Inventory Consumption", lambda db, t: report_service.inventory_consumption(db, t)),
    "amc-renewal-pipeline": ("AMC Renewal Pipeline", lambda db, t: report_service.amc_renewal_pipeline(db, t)),
    "overdue-receivables": ("Overdue Receivables", lambda db, t: report_service.overdue_receivables(db, t)),
    "payment-collection": ("Payment Collection", lambda db, t: report_service.payment_collection(db, t)),
    "installation-pipeline": ("Installation Pipeline", lambda db, t: report_service.installation_pipeline(db, t)),
    "purchase-orders": ("Purchase Orders", lambda db, t: report_service.purchase_orders_report(db, t)),
    "inventory-valuation": ("Inventory Valuation", lambda db, t: report_service.inventory_valuation(db, t)),
}


@router.get("/catalogue")
async def catalogue(
    _: CurrentUser = Depends(get_current_user),
):
    """List of available standard reports (key + title) for the reports UI."""
    return {"reports": [{"key": k, "title": title} for k, (title, _p) in _REPORTS.items()]}


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


@router.get("/{report_key}")
async def standard_report(
    report_key: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Standard report set (SRS 4.16): lead-conversion, revenue-by-customer,
    technician-productivity, inventory-consumption."""
    from fastapi import HTTPException
    if report_key not in _REPORTS:
        raise HTTPException(status_code=404, detail="Unknown report")
    _, producer = _REPORTS[report_key]
    data = await producer(db, current_user.tenant_id)
    return data if isinstance(data, list) else data


@router.get("/{report_key}/export")
async def export_report(
    report_key: str,
    fmt: str = Query("csv", pattern="^(csv|xlsx|pdf)$"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Export a standard report as CSV, Excel, or PDF (SRS 4.16)."""
    from fastapi import HTTPException
    if report_key not in _REPORTS:
        raise HTTPException(status_code=404, detail="Unknown report")
    title, producer = _REPORTS[report_key]
    data = await producer(db, current_user.tenant_id)
    rows = data if isinstance(data, list) else [data]

    if fmt == "csv":
        return Response(report_service.to_csv(rows), media_type="text/csv",
                        headers={"Content-Disposition": f'attachment; filename="{report_key}.csv"'})
    if fmt == "xlsx":
        return Response(
            report_service.to_xlsx(rows, title),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{report_key}.xlsx"'})
    try:
        pdf = report_service.to_pdf(title, rows)
    except (OSError, ImportError) as exc:
        # weasyprint needs native libs (pango/cairo/gobject). If they're absent,
        # fail cleanly instead of a 500 stack trace; CSV/XLSX remain available.
        raise HTTPException(
            status_code=503,
            detail="PDF rendering is unavailable in this environment; use CSV or Excel export.",
        ) from exc
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{report_key}.pdf"'})
