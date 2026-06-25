from datetime import datetime, timezone
from app.workers.celery_app import celery_app
import structlog
from uuid import UUID
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


async def set_celery_tenant_context(db: AsyncSession, tenant_id: UUID):
    """Sets tenant contextvars, bindings for structured logs, and the database session
    RLS context variable for Row-Level Security during a Celery background execution."""
    from app.core.context import set_actor
    set_actor(None, tenant_id)
    structlog.contextvars.bind_contextvars(tenant_id=str(tenant_id))
    conn = await db.connection()
    if conn.dialect.name == "postgresql":
        await db.execute(
            text("SELECT set_config('app.tenant_id', :tid, true)"),
            {"tid": str(tenant_id)},
        )


def _get_session_factory():
    """Return a session factory, initialising the engine lazily."""
    from app.core import database
    database._init_engine()
    return database._AsyncSessionLocal




@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def deliver_notification(self, log_id: str):
    """Deliver a single notification log entry via the appropriate channel."""
    try:
        from app.models.notification import NotificationLog, NotificationStatus, NotificationChannel
        import asyncio

        async def _deliver():
            SessionFactory = _get_session_factory()
            async with SessionFactory() as db:
                from sqlalchemy import select
                from uuid import UUID as PyUUID
                target_id = PyUUID(log_id) if isinstance(log_id, str) else log_id
                result = await db.execute(select(NotificationLog).where(NotificationLog.id == target_id))
                log = result.scalar_one_or_none()
                if not log or log.status == NotificationStatus.SENT:
                    return

                await set_celery_tenant_context(db, log.tenant_id)
                try:
                    if log.channel == NotificationChannel.EMAIL:
                        from app.models.tenant import Tenant
                        from sqlalchemy import select
                        result_tenant = await db.execute(select(Tenant).where(Tenant.id == log.tenant_id))
                        tenant = result_tenant.scalar_one_or_none()
                        sender = tenant.custom_email_sender if tenant else None
                        await _send_email(log.recipient, log.subject, log.body, sender=sender)
                    elif log.channel == NotificationChannel.SMS:
                        await _send_sms(log.recipient, log.body)
                    elif log.channel == NotificationChannel.WHATSAPP:
                        await _send_whatsapp(log.recipient, log.body)
                    elif log.channel == NotificationChannel.IN_APP:
                        pass  # in-app messages are served from the DB; nothing to deliver

                    log.status = NotificationStatus.SENT
                except Exception as exc:
                    log.status = NotificationStatus.FAILED
                    log.retry_count += 1
                    log.error_detail = str(exc)
                    raise

                await db.commit()

        asyncio.run(_deliver())
    except Exception as exc:
        logger.error("Notification delivery failed", log_id=log_id, error=str(exc))
        raise self.retry(exc=exc)


async def _send_email(recipient: str, subject: str, body: str, sender: str = None):
    import smtplib
    from email.message import EmailMessage
    from app.core.config import get_settings
    settings = get_settings()
    msg = EmailMessage()
    msg["From"] = sender or settings.SMTP_FROM
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as s:
        s.starttls()
        s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        s.send_message(msg)


async def _send_sms(phone: str, body: str):
    import httpx
    from app.core.config import get_settings
    settings = get_settings()
    # Provider URL must come from configuration — never a hardcoded placeholder.
    if not settings.SMS_PROVIDER_URL:
        logger.warning("SMS provider not configured; skipping", recipient=phone)
        return
    async with httpx.AsyncClient() as client:
        await client.post(
            settings.SMS_PROVIDER_URL,
            json={"to": phone, "message": body},
            headers={"Authorization": f"Bearer {settings.SMS_PROVIDER_API_KEY}"},
        )


async def _send_whatsapp(phone: str, body: str):
    import httpx
    from app.core.config import get_settings
    settings = get_settings()
    if not settings.WHATSAPP_API_URL:
        logger.warning("WhatsApp not configured; skipping", recipient=phone)
        return
    async with httpx.AsyncClient() as client:
        await client.post(
            settings.WHATSAPP_API_URL,
            json={"to": phone, "type": "text", "text": {"body": body}},
            headers={"Authorization": f"Bearer {settings.WHATSAPP_API_KEY}"},
        )


@celery_app.task
def check_amc_renewals():
    """Send renewal reminders for AMC contracts expiring in 30 or 7 days."""
    import asyncio

    async def _check():
        from sqlalchemy import select
        from datetime import timedelta, date
        from app.models.amc import AMCContract, AMCStatus
        from app.models.tenant import Tenant

        SessionFactory = _get_session_factory()
        async with SessionFactory() as db:
            tenants = (await db.execute(
                select(Tenant.id).where(Tenant.status.in_(["active", "trial"]))
            )).scalars().all()
            today = date.today()
            for tid in tenants:
                await set_celery_tenant_context(db, tid)
                for days_ahead in (30, 7):
                    target = today + timedelta(days=days_ahead)
                    result = await db.execute(
                        select(AMCContract).where(
                            AMCContract.status == AMCStatus.ACTIVE,
                            AMCContract.end_date == target,
                        )
                    )
                    contracts = result.scalars().all()
                    for c in contracts:
                        await _notify_amc_expiry(db, c, days_ahead)

    asyncio.run(_check())


async def _notify_amc_expiry(db, contract, days_ahead):
    await set_celery_tenant_context(db, contract.tenant_id)
    from sqlalchemy import select
    from app.models.customer import Customer
    from app.services.notification import NotificationService
    from app.services.notification_events import AMC_EXPIRY
    from app.models.notification import NotificationChannel

    customer = (await db.execute(
        select(Customer).where(Customer.id == contract.customer_id)
    )).scalar_one_or_none()
    recipient = (customer.email if customer else None) or ""
    await NotificationService(db, contract.tenant_id).send(
        AMC_EXPIRY,
        recipient=recipient,
        context={"contract_number": contract.contract_number, "days": days_ahead,
                 "end_date": str(contract.end_date)},
        channel=NotificationChannel.EMAIL,
    )
    await db.commit()


@celery_app.task
def check_sla_breaches():
    """Mark tickets whose SLA deadline has passed and send escalation notifications."""
    import asyncio

    async def _check():
        from sqlalchemy import select
        from app.models.service_ticket import ServiceTicket, TicketStatus
        from app.models.tenant import Tenant

        SessionFactory = _get_session_factory()
        async with SessionFactory() as db:
            tenants = (await db.execute(
                select(Tenant.id).where(Tenant.status.in_(["active", "trial"]))
            )).scalars().all()
            now = datetime.now(timezone.utc)
            for tid in tenants:
                await set_celery_tenant_context(db, tid)
                result = await db.execute(
                    select(ServiceTicket).where(
                        ServiceTicket.sla_due_at <= now,
                        ServiceTicket.sla_breached == False,
                        ServiceTicket.status.not_in([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
                    )
                )
                tickets = result.scalars().all()
                for t in tickets:
                    t.sla_breached = True
                    logger.warning("SLA breached", ticket_id=str(t.id))
                    await _notify_sla_breach(db, t)
            await db.commit()

    asyncio.run(_check())


async def _notify_sla_breach(db, ticket):
    await set_celery_tenant_context(db, ticket.tenant_id)
    from app.services.notification import NotificationService
    from app.services.notification_events import SLA_BREACH
    from app.models.notification import NotificationChannel
    await NotificationService(db, ticket.tenant_id).send(
        SLA_BREACH,
        recipient=str(ticket.assigned_to or ""),
        context={"ticket_number": ticket.ticket_number, "priority": ticket.priority},
        channel=NotificationChannel.IN_APP,
        recipient_user_id=ticket.assigned_to,
    )


@celery_app.task
def check_payment_due():
    """Send reminders for invoices that are overdue or due soon."""
    import asyncio

    async def _check():
        from sqlalchemy import select
        from datetime import date, timedelta
        from app.models.invoice import Invoice, InvoiceStatus
        from app.models.customer import Customer
        from app.services.notification import NotificationService
        from app.services.notification_events import PAYMENT_DUE
        from app.models.notification import NotificationChannel
        from app.models.tenant import Tenant

        SessionFactory = _get_session_factory()
        async with SessionFactory() as db:
            tenants = (await db.execute(
                select(Tenant.id).where(Tenant.status.in_(["active", "trial"]))
            )).scalars().all()
            soon = date.today() + timedelta(days=3)
            for tid in tenants:
                await set_celery_tenant_context(db, tid)
                result = await db.execute(
                    select(Invoice).where(
                        Invoice.status.in_([InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID]),
                        Invoice.due_date <= soon,
                    )
                )
                for inv in result.scalars().all():
                    customer = (await db.execute(
                        select(Customer).where(Customer.id == inv.customer_id)
                    )).scalar_one_or_none()
                    await NotificationService(db, inv.tenant_id).send(
                        PAYMENT_DUE,
                        recipient=(customer.email if customer else None) or "",
                        context={"invoice_number": inv.invoice_number,
                                 "amount_due": float(inv.total_amount - (inv.amount_paid or 0)),
                                 "due_date": str(inv.due_date)},
                        channel=NotificationChannel.EMAIL,
                    )
            await db.commit()

    asyncio.run(_check())


@celery_app.task
def generate_recurring_invoices():
    """Generate AMC billing invoices for active contracts whose cycle is due."""
    import asyncio

    async def _run():
        from app.services.invoice import generate_recurring_amc_invoices
        SessionFactory = _get_session_factory()
        async with SessionFactory() as db:
            n = await generate_recurring_amc_invoices(db)
            logger.info("Recurring AMC invoices generated", count=n)

    asyncio.run(_run())


@celery_app.task
def expire_trials():
    """Suspend tenants whose trial window has elapsed (Phase 1 lifecycle)."""
    import asyncio

    async def _run():
        from app.services.tenant import run_trial_expiry
        SessionFactory = _get_session_factory()
        async with SessionFactory() as db:
            n = await run_trial_expiry(db)
            await db.commit()
            logger.info("Trial expiry sweep complete", suspended=n)

    asyncio.run(_run())


@celery_app.task
def aggregate_dashboard_kpis():
    """Pre-aggregate KPI metrics into dashboard_snapshots for fast dashboard loads."""
    import asyncio

    async def _aggregate():
        from sqlalchemy import select
        from app.models.tenant import Tenant
        from app.models.dashboard_snapshot import DashboardSnapshot
        from app.services.reports import dashboard_kpis

        SessionFactory = _get_session_factory()
        async with SessionFactory() as db:
            tenants = (await db.execute(select(Tenant.id))).scalars().all()
            for tid in tenants:
                await set_celery_tenant_context(db, tid)
                metrics = await dashboard_kpis(db, tid)
                existing = (await db.execute(
                    select(DashboardSnapshot).where(DashboardSnapshot.tenant_id == tid)
                )).scalar_one_or_none()
                if existing:
                    existing.metrics = metrics
                else:
                    db.add(DashboardSnapshot(tenant_id=tid, metrics=metrics))
            await db.commit()
        logger.info("Dashboard KPI aggregation complete", tenants=len(tenants))

    asyncio.run(_aggregate())


@celery_app.task
def purge_cancelled_tenants():
    """Daily cron sweep to find cancelled tenants whose retention window has passed,
    and hard-delete all their records from the database and storage."""
    import asyncio
    
    async def _purge():
        from sqlalchemy import select
        from app.models.tenant import Tenant, TenantStatus
        from app.services.offboarding import hard_delete_tenant_data
        
        SessionFactory = _get_session_factory()
        async with SessionFactory() as db:
            now = datetime.now(timezone.utc)
            stmt = select(Tenant.id).where(
                Tenant.status == TenantStatus.CANCELLED.value,
                Tenant.scheduled_hard_delete_at.is_not(None),
                Tenant.scheduled_hard_delete_at <= now,
            )
            result = await db.execute(stmt)
            tids = result.scalars().all()
            for tid in tids:
                logger.info("Purging cancelled tenant", tenant_id=str(tid))
                await hard_delete_tenant_data(db, tid)
            await db.commit()
            
    asyncio.run(_purge())


@celery_app.task
def meter_tenant_usage():
    """Daily cron sweep to pre-aggregate resource counts (users, sites, technicians)
    per tenant and output structured log events for usage metering/billing."""
    import asyncio
    
    async def _meter():
        from sqlalchemy import select
        from app.models.tenant import Tenant, TenantStatus
        from app.services.tenant import tenant_usage
        
        SessionFactory = _get_session_factory()
        async with SessionFactory() as db:
            stmt = select(Tenant.id).where(
                Tenant.status.in_([TenantStatus.ACTIVE.value, TenantStatus.TRIAL.value])
            )
            result = await db.execute(stmt)
            tids = result.scalars().all()
            for tid in tids:
                usage = await tenant_usage(db, tid)
                logger.info(
                    "tenant_usage_meter",
                    tenant_id=str(tid),
                    plan=usage.get("plan"),
                    users=usage["users"]["used"],
                    technicians=usage["technicians"]["used"],
                    sites=usage["sites"]["used"],
                )
                
    asyncio.run(_meter())

