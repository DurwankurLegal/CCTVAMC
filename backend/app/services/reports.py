"""
Reporting service — all queries run against read replica when available.
KPI snapshots are pre-aggregated by Celery; dashboards read from snapshot cache.
"""
from uuid import UUID
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.models.service_ticket import ServiceTicket, TicketStatus
from app.models.invoice import Invoice, InvoiceStatus
from app.models.amc import AMCContract, AMCStatus
from app.models.lead import Lead, LeadStatus
from app.models.payment import Payment


async def dashboard_kpis(db: AsyncSession, tenant_id: UUID) -> dict:
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)

    # Open tickets
    r = await db.execute(
        select(func.count()).where(
            ServiceTicket.tenant_id == tenant_id,
            ServiceTicket.status.not_in([TicketStatus.RESOLVED, TicketStatus.CLOSED])
        )
    )
    open_tickets = r.scalar() or 0

    # SLA breached
    r = await db.execute(
        select(func.count()).where(
            ServiceTicket.tenant_id == tenant_id,
            ServiceTicket.sla_breached == True,
            ServiceTicket.status.not_in([TicketStatus.RESOLVED, TicketStatus.CLOSED])
        )
    )
    sla_breached = r.scalar() or 0

    # Active AMC contracts
    r = await db.execute(
        select(func.count()).where(
            AMCContract.tenant_id == tenant_id,
            AMCContract.status == AMCStatus.ACTIVE,
        )
    )
    active_amc = r.scalar() or 0

    # Revenue this month
    r = await db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.tenant_id == tenant_id,
            Payment.payment_date >= today.replace(day=1),
        )
    )
    revenue_mtd = float(r.scalar() or 0)

    # Lead pipeline
    r = await db.execute(
        select(Lead.status, func.count()).where(
            Lead.tenant_id == tenant_id
        ).group_by(Lead.status)
    )
    lead_pipeline = {row[0]: row[1] for row in r.all()}

    # Outstanding receivables
    r = await db.execute(
        select(func.coalesce(func.sum(Invoice.total_amount - Invoice.amount_paid), 0)).where(
            Invoice.tenant_id == tenant_id,
            Invoice.status.in_([InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID]),
        )
    )
    outstanding = float(r.scalar() or 0)

    return {
        "open_tickets": open_tickets,
        "sla_breached_tickets": sla_breached,
        "active_amc_contracts": active_amc,
        "revenue_mtd": revenue_mtd,
        "outstanding_receivables": outstanding,
        "lead_pipeline": lead_pipeline,
    }


async def lead_conversion_report(db: AsyncSession, tenant_id: UUID) -> dict:
    total = (await db.execute(
        select(func.count()).where(Lead.tenant_id == tenant_id)
    )).scalar() or 0
    converted = (await db.execute(
        select(func.count()).where(Lead.tenant_id == tenant_id, Lead.status == LeadStatus.CONVERTED)
    )).scalar() or 0
    return {"total_leads": total, "converted": converted,
            "conversion_pct": round(converted / total * 100, 1) if total else 0.0}


async def revenue_by_customer(db: AsyncSession, tenant_id: UUID) -> list:
    rows = (await db.execute(
        select(Invoice.customer_id, func.coalesce(func.sum(Invoice.total_amount), 0))
        .where(Invoice.tenant_id == tenant_id)
        .group_by(Invoice.customer_id)
    )).all()
    return [{"customer_id": str(c), "revenue": float(amt)} for c, amt in rows]


async def technician_productivity(db: AsyncSession, tenant_id: UUID) -> list:
    from app.models.engineer_visit import EngineerVisit
    rows = (await db.execute(
        select(EngineerVisit.technician_id, func.count())
        .where(EngineerVisit.tenant_id == tenant_id, EngineerVisit.checkout_at.isnot(None))
        .group_by(EngineerVisit.technician_id)
    )).all()
    return [{"technician_id": str(t), "completed_visits": n} for t, n in rows]


async def inventory_consumption(db: AsyncSession, tenant_id: UUID) -> list:
    from app.models.inventory import InventoryMovement, MovementType
    rows = (await db.execute(
        select(InventoryMovement.item_id, func.coalesce(func.sum(InventoryMovement.quantity), 0))
        .where(InventoryMovement.tenant_id == tenant_id,
               InventoryMovement.movement_type == MovementType.CONSUMPTION)
        .group_by(InventoryMovement.item_id)
    )).all()
    return [{"item_id": str(i), "consumed": abs(int(q))} for i, q in rows]


async def amc_renewal_pipeline(db: AsyncSession, tenant_id: UUID, window_days: int = 90) -> list:
    """Active AMC contracts expiring within `window_days` — renewal pipeline."""
    today = date.today()
    horizon = today + timedelta(days=window_days)
    rows = (await db.execute(
        select(AMCContract.contract_number, AMCContract.customer_id,
               AMCContract.end_date, AMCContract.annual_amount, AMCContract.status)
        .where(AMCContract.tenant_id == tenant_id,
               AMCContract.status.in_([AMCStatus.ACTIVE, "expiring"]),
               AMCContract.end_date <= horizon)
        .order_by(AMCContract.end_date)
    )).all()
    return [{"contract_number": cn, "customer_id": str(cid), "end_date": str(ed),
             "days_to_expiry": (ed - today).days, "annual_amount": float(amt), "status": st}
            for cn, cid, ed, amt, st in rows]


async def overdue_receivables(db: AsyncSession, tenant_id: UUID) -> list:
    """Unpaid/partly-paid invoices past their due date."""
    today = date.today()
    rows = (await db.execute(
        select(Invoice.invoice_number, Invoice.customer_id, Invoice.due_date,
               Invoice.total_amount, Invoice.amount_paid)
        .where(Invoice.tenant_id == tenant_id,
               Invoice.status.in_([InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID]),
               Invoice.due_date < today)
        .order_by(Invoice.due_date)
    )).all()
    return [{"invoice_number": inv, "customer_id": str(cid), "due_date": str(dd),
             "days_overdue": (today - dd).days if dd else None,
             "balance": float(tot) - float(paid)}
            for inv, cid, dd, tot, paid in rows]


async def payment_collection(db: AsyncSession, tenant_id: UUID) -> list:
    """Payments collected grouped by mode."""
    rows = (await db.execute(
        select(Payment.mode, func.count(), func.coalesce(func.sum(Payment.amount), 0))
        .where(Payment.tenant_id == tenant_id)
        .group_by(Payment.mode)
    )).all()
    return [{"mode": m, "count": n, "total_collected": float(amt)} for m, n, amt in rows]


async def installation_pipeline(db: AsyncSession, tenant_id: UUID) -> list:
    """Installation work orders grouped by status."""
    from app.models.installation import Installation
    rows = (await db.execute(
        select(Installation.status, func.count())
        .where(Installation.tenant_id == tenant_id)
        .group_by(Installation.status)
    )).all()
    return [{"status": s, "count": n} for s, n in rows]


async def purchase_orders_report(db: AsyncSession, tenant_id: UUID) -> list:
    """Purchase orders grouped by status with value."""
    from app.models.vendor import PurchaseOrder
    rows = (await db.execute(
        select(PurchaseOrder.status, func.count(),
               func.coalesce(func.sum(PurchaseOrder.total_amount), 0))
        .where(PurchaseOrder.tenant_id == tenant_id)
        .group_by(PurchaseOrder.status)
    )).all()
    return [{"status": s, "count": n, "total_value": float(amt)} for s, n, amt in rows]


async def inventory_valuation(db: AsyncSession, tenant_id: UUID) -> list:
    """Current stock valuation per item (current_stock × unit_cost)."""
    from app.models.inventory import InventoryItem
    rows = (await db.execute(
        select(InventoryItem.name, InventoryItem.current_stock, InventoryItem.unit_cost)
        .where(InventoryItem.tenant_id == tenant_id, InventoryItem.is_active == True)
    )).all()
    return [{"item": name, "current_stock": int(stock or 0),
             "unit_cost": float(cost or 0), "value": float((stock or 0) * float(cost or 0))}
            for name, stock, cost in rows]


# ── Export helpers (CSV / Excel / PDF) ────────────────────────
def to_csv(rows: list[dict]) -> bytes:
    import csv, io
    if not rows:
        return b""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode()


def to_xlsx(rows: list[dict], sheet_name: str = "Report") -> bytes:
    import io
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name[:31]
    if rows:
        headers = list(rows[0].keys())
        ws.append(headers)
        for r in rows:
            ws.append([r.get(h) for h in headers])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def to_pdf(title: str, rows: list[dict]) -> bytes:
    from weasyprint import HTML
    headers = list(rows[0].keys()) if rows else []
    head_html = "".join(f"<th>{h}</th>" for h in headers)
    body_html = "".join(
        "<tr>" + "".join(f"<td>{r.get(h)}</td>" for h in headers) + "</tr>" for r in rows
    )
    html = f"""<html><head><style>
      body{{font-family:sans-serif;font-size:11px}} h1{{font-size:16px}}
      table{{border-collapse:collapse;width:100%}} th,td{{border:1px solid #ccc;padding:4px;text-align:left}}
      th{{background:#0f2a43;color:#fff}}</style></head>
      <body><h1>{title}</h1><table><tr>{head_html}</tr>{body_html}</table></body></html>"""
    return HTML(string=html).write_pdf()


async def ticket_sla_report(db: AsyncSession, tenant_id: UUID, from_date: date, to_date: date) -> dict:
    r = await db.execute(
        select(func.count()).where(
            and_(
                ServiceTicket.tenant_id == tenant_id,
                ServiceTicket.created_at >= from_date,
                ServiceTicket.created_at <= to_date,
            )
        )
    )
    total = r.scalar() or 0

    r = await db.execute(
        select(func.count()).where(
            and_(
                ServiceTicket.tenant_id == tenant_id,
                ServiceTicket.sla_breached == True,
                ServiceTicket.created_at >= from_date,
                ServiceTicket.created_at <= to_date,
            )
        )
    )
    breached = r.scalar() or 0

    return {
        "period": {"from": str(from_date), "to": str(to_date)},
        "total_tickets": total,
        "sla_met": total - breached,
        "sla_breached": breached,
        "compliance_pct": round((total - breached) / total * 100, 1) if total else 100.0,
    }
