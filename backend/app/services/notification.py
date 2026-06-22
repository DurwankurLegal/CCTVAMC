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

    async def send(self, event_type: str, recipient: str, context: dict, channel: str = NotificationChannel.EMAIL):
        template = await self._get_template(event_type, channel)
        if not template:
            logger.warning("No notification template", event_type=event_type, channel=channel)
            return

        body = self._render(template.body, context)
        subject = self._render(template.subject or "", context)

        log = NotificationLog(
            tenant_id=self.tenant_id,
            event_type=event_type,
            channel=channel,
            recipient=recipient,
            subject=subject,
            body=body,
            status=NotificationStatus.PENDING,
            context_data=context,
        )
        self.db.add(log)
        await self.db.flush()

        # Dispatch to Celery worker (import here to avoid circular deps)
        from app.workers.tasks import deliver_notification
        deliver_notification.delay(str(log.id))

    async def _get_template(self, event_type: str, channel: str):
        result = await self.db.execute(
            select(NotificationTemplate).where(
                NotificationTemplate.tenant_id == self.tenant_id,
                NotificationTemplate.event_type == event_type,
                NotificationTemplate.channel == channel,
                NotificationTemplate.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _render(template: str, context: dict) -> str:
        for key, val in context.items():
            template = template.replace(f"{{{{{key}}}}}", str(val))
        return template
