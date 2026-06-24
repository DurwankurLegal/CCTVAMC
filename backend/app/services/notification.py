"""
Central Notification Engine — all modules call NotificationService.send().
Templates are stored in DB per tenant per event type; no code redeploy for template changes.
Actual delivery is dispatched to Celery for async processing.
"""
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.notification import NotificationTemplate, NotificationLog, NotificationStatus, NotificationChannel
import structlog

logger = structlog.get_logger()


class NotificationService:
    def __init__(self, db: AsyncSession, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    async def send(self, event_type: str, recipient: str, context: dict,
                   channel: str = NotificationChannel.EMAIL, recipient_user_id=None):
        template = await self._get_template(event_type, channel)
        if template:
            body = self._render(template.body, context)
            subject = self._render(template.subject or "", context)
        else:
            # Fall back to a generic message so events are never silently dropped.
            logger.warning("No notification template; using fallback",
                           event_type=event_type, channel=channel)
            subject = event_type.replace("_", " ").title()
            body = self._render_fallback(event_type, context)

        log = NotificationLog(
            tenant_id=self.tenant_id,
            event_type=event_type,
            channel=channel,
            recipient=recipient,
            subject=subject,
            body=body,
            status=NotificationStatus.PENDING,
            context_data=context,
            recipient_user_id=recipient_user_id,
        )
        self.db.add(log)
        await self.db.flush()

        # In-app messages are read from the DB directly; no external delivery.
        if channel == NotificationChannel.IN_APP:
            log.status = NotificationStatus.SENT
            await self.db.flush()
            return log

        # Dispatch to Celery worker (import here to avoid circular deps)
        from app.workers.tasks import deliver_notification
        deliver_notification.delay(str(log.id))
        return log

    @staticmethod
    def _render_fallback(event_type: str, context: dict) -> str:
        parts = ", ".join(f"{k}={v}" for k, v in context.items())
        return f"[{event_type}] {parts}"

    async def _get_template(self, event_type: str, channel: str):
        result = await self.db.execute(
            select(NotificationTemplate).where(
                NotificationTemplate.tenant_id == self.tenant_id,
                NotificationTemplate.event_type == event_type,
                NotificationTemplate.channel == channel,
                NotificationTemplate.is_active == True,
            )
        )
        db_template = result.scalar_one_or_none()
        if db_template:
            return db_template

        # Check tenant email templates override JSON
        from app.models.tenant import Tenant
        result_tenant = await self.db.execute(select(Tenant).where(Tenant.id == self.tenant_id))
        tenant = result_tenant.scalar_one_or_none()
        if tenant and tenant.email_templates:
            template_override = tenant.email_templates.get(event_type)
            if template_override and isinstance(template_override, dict):
                class DynamicTemplate:
                    def __init__(self, subject: str, body: str):
                        self.subject = subject
                        self.body = body
                subject = template_override.get("subject", "")
                body = template_override.get("body", "")
                if body:
                    return DynamicTemplate(subject, body)
        return None

    @staticmethod
    def _render(template: str, context: dict) -> str:
        for key, val in context.items():
            template = template.replace(f"{{{{{key}}}}}", str(val))
        return template
