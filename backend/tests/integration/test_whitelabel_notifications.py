import pytest
from unittest.mock import patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.tenant import Tenant
from app.models.notification import NotificationLog, NotificationChannel
from app.services.notification import NotificationService
from app.workers.tasks import deliver_notification

@pytest.mark.asyncio
async def test_notification_service_uses_json_template_override(db: AsyncSession, tenant: Tenant):
    # Set email_templates overrides on the tenant record
    tenant.email_templates = {
        "custom_test_event": {
            "subject": "Custom Subject for {{name}}",
            "body": "Custom Body for {{name}} containing {{detail}}"
        }
    }
    db.add(tenant)
    await db.commit()

    service = NotificationService(db, tenant.id)
    log = await service.send(
        event_type="custom_test_event",
        recipient="test@example.com",
        context={"name": "Alice", "detail": "Test Detail"},
        channel=NotificationChannel.EMAIL
    )

    # Verify that the generated log used the custom template from the Tenant model
    assert log.subject == "Custom Subject for Alice"
    assert log.body == "Custom Body for Alice containing Test Detail"


def test_celery_task_uses_custom_email_sender():
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from app.models.tenant import Tenant
    from app.models.notification import NotificationLog, NotificationChannel
    from app.core.database import Base
    import uuid
    
    # 1. Create engine and session_factory
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    
    async def init_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.run(init_db())
    
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    
    # 2. Seed data
    async def seed():
        async with session_factory() as session:
            t = Tenant(
                id=uuid.uuid4(),
                name="Test Tenant",
                slug="test-tenant",
                custom_email_sender="noreply@custombrand.com"
            )
            session.add(t)
            await session.flush()
            
            log = NotificationLog(
                tenant_id=t.id,
                event_type="standard_event",
                channel=NotificationChannel.EMAIL,
                recipient="customer@example.com",
                subject="Hello Custom Brand",
                body="Body Text"
            )
            session.add(log)
            await session.commit()
            return str(log.id)
            
    log_id = asyncio.run(seed())
    
    # 3. Execute celery task synchronously (which runs asyncio.run internally)
    with patch("app.workers.tasks._get_session_factory", return_value=session_factory), \
         patch("app.workers.tasks._send_email") as mock_send_email:
        deliver_notification(log_id)
        
        mock_send_email.assert_called_once_with(
            "customer@example.com",
            "Hello Custom Brand",
            "Body Text",
            sender="noreply@custombrand.com"
        )
        
    # 4. Clean up
    async def cleanup():
        await engine.dispose()
    asyncio.run(cleanup())
