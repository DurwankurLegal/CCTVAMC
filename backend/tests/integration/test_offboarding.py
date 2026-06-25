import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, MagicMock

from app.models.tenant import Tenant, TenantStatus
from app.models.user import User, TenantRole
from app.models.customer import Customer
from app.services.tenant import set_tenant_status
from app.services.offboarding import export_tenant_data, hard_delete_tenant_data
from app.workers.tasks import purge_cancelled_tenants
from tests.conftest import IS_POSTGRES


@pytest.mark.asyncio
async def test_tenant_cancellation_lifecycle(db: AsyncSession):
    # Create tenant
    tenant = Tenant(id=uuid4(), name="Offboard Co", slug=f"offboard-co-{uuid4().hex[:6]}", status=TenantStatus.ACTIVE)
    db.add(tenant)
    await db.flush()

    # Cancel tenant
    cancelled_tenant = await set_tenant_status(db, tenant.id, "cancel")
    assert cancelled_tenant.status == TenantStatus.CANCELLED.value
    assert cancelled_tenant.is_active is False
    assert cancelled_tenant.scheduled_hard_delete_at is not None
    # Tolerance check of 1 minute
    sched = cancelled_tenant.scheduled_hard_delete_at.replace(tzinfo=None)
    target = (datetime.now(timezone.utc) + timedelta(days=30)).replace(tzinfo=None)
    time_diff = sched - target
    assert abs(time_diff.total_seconds()) < 60


    # Reactivate tenant
    reactivated_tenant = await set_tenant_status(db, tenant.id, "activate")
    assert reactivated_tenant.status == TenantStatus.ACTIVE.value
    assert reactivated_tenant.is_active is True
    assert reactivated_tenant.scheduled_hard_delete_at is None

@pytest.mark.asyncio
async def test_tenant_data_export_and_purge(db: AsyncSession):
    # Create tenant
    tenant = Tenant(id=uuid4(), name="Export Co", slug=f"export-co-{uuid4().hex[:6]}", status=TenantStatus.ACTIVE)
    db.add(tenant)
    await db.flush()

    # Create dummy user with password
    user = User(
        id=uuid4(),
        tenant_id=tenant.id,
        email="user@export.com",
        full_name="Export User",
        hashed_password="some_super_secret_hash",
        role=TenantRole.ADMIN
    )
    db.add(user)

    # Create dummy customer
    customer = Customer(
        id=uuid4(),
        tenant_id=tenant.id,
        name="Export Customer",
        category="commercial",
        status="active"
    )
    db.add(customer)
    await db.flush()

    # Test export
    exported = await export_tenant_data(db, tenant.id)
    assert exported["tenant"]["slug"].startswith("export-co")
    assert len(exported["users"]) == 1
    assert exported["users"][0]["email"] == "user@export.com"
    # Ensure credentials are excluded
    assert "hashed_password" not in exported["users"][0]
    
    assert len(exported["customers"]) == 1
    assert exported["customers"][0]["name"] == "Export Customer"

    # Test hard delete with storage mock
    with patch("app.services.storage.delete_file") as mock_delete:
        await hard_delete_tenant_data(db, tenant.id)
        await db.commit()

    # Verify everything is gone
    result = await db.execute(select(Tenant).where(Tenant.id == tenant.id))
    assert result.scalar_one_or_none() is None

    result_user = await db.execute(select(User).where(User.tenant_id == tenant.id))
    assert result_user.scalar_one_or_none() is None

    result_cust = await db.execute(select(Customer).where(Customer.tenant_id == tenant.id))
    assert result_cust.scalar_one_or_none() is None

@pytest.mark.skipif(not IS_POSTGRES, reason="Celery task database integration requires PostgreSQL")
def test_purge_cancelled_tenants_task():

    # Create tenant marked for purge (past hard delete date)
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from tests.conftest import TEST_DB_URL

    tenant_id = uuid4()
    past_date = datetime.now(timezone.utc) - timedelta(days=1)

    async def _seed():
        engine = create_async_engine(TEST_DB_URL)
        SessionFactory = async_sessionmaker(engine, expire_on_commit=False)
        async with SessionFactory() as db:
            tenant = Tenant(
                id=tenant_id,
                name="Purge Co",
                slug=f"purge-co-{uuid4().hex[:6]}",
                status=TenantStatus.CANCELLED.value,
                scheduled_hard_delete_at=past_date,
                is_active=False
            )
            db.add(tenant)
            await db.commit()
        await engine.dispose()

    asyncio.run(_seed())

    # Run sweep celery task (executes asyncio.run internally)
    with patch("app.services.storage.delete_file") as mock_delete:
        purge_cancelled_tenants()

    # Check that tenant was hard-deleted
    async def _verify():
        engine = create_async_engine(TEST_DB_URL)
        SessionFactory = async_sessionmaker(engine, expire_on_commit=False)
        async with SessionFactory() as db:
            res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
            assert res.scalar_one_or_none() is None
        await engine.dispose()

    asyncio.run(_verify())


