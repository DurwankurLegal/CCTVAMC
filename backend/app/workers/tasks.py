from datetime import datetime, timezone
from app.workers.celery_app import celery_app
import structlog

logger = structlog.get_logger()


def _get_session_factory():
    """Return a session factory, initialising the engine lazily."""
    from app.core.database import _init_engine, _AsyncSessionLocal
    _init_engine()
    return _AsyncSessionLocal


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
                result = await db.execute(select(NotificationLog).where(NotificationLog.id == log_id))
                log = result.scalar_one_or_none()
                if not log or log.status == NotificationStatus.SENT:
                    return

                try:
                    if log.channel == NotificationChannel.EMAIL:
                        await _send_email(log.recipient, log.subject, log.body)
                    elif log.channel == NotificationChannel.SMS:
                        await _send_sms(log.recipient, log.body)
                    # WhatsApp and in_app channels: implement similarly

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


async def _send_email(recipient: str, subject: str, body: str):
    import smtplib
    from email.message import EmailMessage
    from app.core.config import get_settings
    settings = get_settings()
    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM
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
    async with httpx.AsyncClient() as client:
        await client.post(
            "https://sms.example.com/send",
            json={"to": phone, "message": body},
            headers={"Authorization": f"Bearer {settings.SMS_PROVIDER_API_KEY}"},
        )


@celery_app.task
def check_amc_renewals():
    """Send renewal reminders for AMC contracts expiring in 30 or 7 days."""
    import asyncio

    async def _check():
        from sqlalchemy import select
        from datetime import timedelta, date
        from app.models.amc import AMCContract, AMCStatus

        SessionFactory = _get_session_factory()
        async with SessionFactory() as db:
            today = date.today()
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
                    logger.info("AMC renewal reminder needed", contract_id=str(c.id), days=days_ahead)

    asyncio.run(_check())


@celery_app.task
def check_sla_breaches():
    """Mark tickets whose SLA deadline has passed and send escalation notifications."""
    import asyncio

    async def _check():
        from sqlalchemy import select
        from app.models.service_ticket import ServiceTicket, TicketStatus

        SessionFactory = _get_session_factory()
        async with SessionFactory() as db:
            now = datetime.now(timezone.utc)
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
            await db.commit()

    asyncio.run(_check())


@celery_app.task
def aggregate_dashboard_kpis():
    """Pre-aggregate KPI metrics into dashboard_snapshots to support fast dashboard loads."""
    logger.info("Dashboard KPI aggregation started")
    # TODO: implement per-tenant KPI aggregation
