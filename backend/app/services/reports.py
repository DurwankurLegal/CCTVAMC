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
