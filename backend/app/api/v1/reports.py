from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_permission, get_tenant_active_modules
from app.services import reports as report_service

router = APIRouter()

# Report key -> (title, required_module, async producer returning a list[dict])
_REPORTS = {
    "lead-conversion": ("Lead Conversion", None, lambda db, t: report_service.lead_conversion_report(db, t)),
    "revenue-by-customer": ("Revenue by Customer", "sales", lambda db, t: report_service.revenue_by_customer(db, t)),
    "technician-productivity": ("Technician Productivity", "amc", lambda db, t: report_service.technician_productivity(db, t)),
    "inventory-consumption": ("Inventory Consumption", "inventory", lambda db, t: report_service.inventory_consumption(db, t)),
    "amc-renewal-pipeline": ("AMC Renewal Pipeline", "amc", lambda db, t: report_service.amc_renewal_pipeline(db, t)),
    "overdue-receivables": ("Overdue Receivables", None, lambda db, t: report_service.overdue_receivables(db, t)),
    "payment-collection": ("Payment Collection", None, lambda db, t: report_service.payment_collection(db, t)),
    "installation-pipeline": ("Installation Pipeline", "amc", lambda db, t: report_service.installation_pipeline(db, t)),
    "purchase-orders": ("Purchase Orders", "inventory", lambda db, t: report_service.purchase_orders_report(db, t)),
    "inventory-valuation": ("Inventory Valuation", "inventory", lambda db, t: report_service.inventory_valuation(db, t)),
}


@router.get("/catalogue")
async def catalogue(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List of available standard reports (key + title) for the reports UI."""
    active_modules = await get_tenant_active_modules(db, current_user.tenant_id)
    available_reports = []
    for k, (title, req_module, _p) in _REPORTS.items():
        if req_module is None or req_module in active_modules:
            available_reports.append({"key": k, "title": title})
    return {"reports": available_reports}


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


@router.get("/sla/export")
async def export_sla_report(
    from_date: date = Query(...),
    to_date: date = Query(...),
    company_id: UUID = Query(None),
    fmt: str = Query("pdf", pattern="^(pdf|xlsx)$"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Export the SLA Compliance Report as PDF or Excel."""
    from fastapi import HTTPException
    from app.services.company import resolve_company_id
    comp_id = await resolve_company_id(db, current_user.tenant_id, company_id)
    filename_stem = f"SLA-Compliance-Report-{from_date}-to-{to_date}"

    if fmt == "xlsx":
        data = await report_service.ticket_sla_report(db, current_user.tenant_id, from_date, to_date)
        content = report_service.to_xlsx_sla_report(data)
        return Response(
            content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename_stem}.xlsx"'},
        )

    # fmt == "pdf"
    try:
        content = await report_service.to_pdf_sla_report(db, current_user.tenant_id, comp_id, from_date, to_date)
    except (OSError, ImportError):
        raise HTTPException(status_code=503, detail="PDF rendering unavailable.")
    return Response(
        content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename_stem}.pdf"'},
    )


@router.get("/service-consolidated")
async def service_consolidated_preview(
    from_date: date = Query(...),
    to_date: date = Query(...),
    company_id: UUID = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Consolidated service report preview data."""
    from app.services.company import resolve_company_id
    comp_id = await resolve_company_id(db, current_user.tenant_id, company_id)
    return await report_service.service_consolidated_report(db, current_user.tenant_id, comp_id, from_date, to_date)


@router.get("/service-consolidated/export")
async def export_service_consolidated_report(
    from_date: date = Query(...),
    to_date: date = Query(...),
    company_id: UUID = Query(None),
    fmt: str = Query("pdf", pattern="^(pdf|xlsx)$"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Export the Consolidated Service Report as PDF or Excel."""
    from fastapi import HTTPException
    from app.services.company import resolve_company_id
    comp_id = await resolve_company_id(db, current_user.tenant_id, company_id)
    filename_stem = f"Service-Report-{from_date}-to-{to_date}"

    if fmt == "xlsx":
        data = await report_service.service_consolidated_report(db, current_user.tenant_id, comp_id, from_date, to_date)
        content = report_service.to_xlsx_service_report(data)
        return Response(
            content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename_stem}.xlsx"'},
        )

    # fmt == "pdf"
    try:
        content = await report_service.to_pdf_service_report(db, current_user.tenant_id, comp_id, from_date, to_date)
    except (OSError, ImportError):
        raise HTTPException(status_code=503, detail="PDF rendering unavailable.")
    return Response(
        content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename_stem}.pdf"'},
    )


@router.get("/amc-consolidated")
async def amc_consolidated_report(
    amc_id: UUID = Query(..., description="AMC contract UUID"),
    from_date: date = Query(...),
    to_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("reports:read")),
):
    """
    Consolidated AMC Performance & Service Report (JSON).
    Returns contract header, customer, assets, tickets, visits, PM schedules,
    invoices, payments, and computed KPIs for the given contract and date range.
    """
    from fastapi import HTTPException
    data = await report_service.amc_consolidated_report(
        db, current_user.tenant_id, amc_id, from_date, to_date
    )
    if not data:
        raise HTTPException(status_code=404, detail="AMC contract not found or not accessible")
    return data


@router.get("/amc-consolidated/export")
async def export_amc_consolidated_report(
    amc_id: UUID = Query(..., description="AMC contract UUID"),
    from_date: date = Query(...),
    to_date: date = Query(...),
    fmt: str = Query("pdf", pattern="^(pdf|xlsx)$"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("reports:read")),
):
    """
    Export the Consolidated AMC Performance & Service Report as PDF or Excel.
    Filename: AMC-{contract_number}-Report-{from_date}-to-{to_date}.{fmt}
    """
    from fastapi import HTTPException
    data = await report_service.amc_consolidated_report(
        db, current_user.tenant_id, amc_id, from_date, to_date
    )
    if not data:
        raise HTTPException(status_code=404, detail="AMC contract not found or not accessible")

    contract_number = data.get("contract", {}).get("contract_number", str(amc_id))
    # Sanitise contract number for safe filenames
    safe_cn = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in contract_number)
    filename_stem = f"AMC-{safe_cn}-Report-{from_date}-to-{to_date}"

    if fmt == "xlsx":
        content = report_service.to_xlsx_amc_report(data)
        return Response(
            content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename_stem}.xlsx"'},
        )

    # fmt == "pdf"
    try:
        from uuid import UUID
        company_id_str = data.get("contract", {}).get("company_id")
        company_id = UUID(company_id_str) if company_id_str else None
        content = await report_service.to_pdf_amc_report(db, current_user.tenant_id, company_id, data)
    except (OSError, ImportError) as exc:
        raise HTTPException(
            status_code=503,
            detail="PDF rendering unavailable in this environment — use Excel export.",
        ) from exc
    return Response(
        content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename_stem}.pdf"'},
    )


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
    title, req_module, producer = _REPORTS[report_key]
    
    if req_module:
        active_modules = await get_tenant_active_modules(db, current_user.tenant_id)
        if req_module not in active_modules:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Subscription upgrade required. The '{req_module}' module is disabled."
            )

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
    from fastapi import status as http_status
    if report_key not in _REPORTS:
        raise HTTPException(status_code=404, detail="Unknown report")
    title, req_module, producer = _REPORTS[report_key]

    if req_module:
        active_modules = await get_tenant_active_modules(db, current_user.tenant_id)
        if req_module not in active_modules:
            raise HTTPException(
                status_code=http_status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Subscription upgrade required. The '{req_module}' module is disabled."
            )

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
