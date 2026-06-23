"""Database-level RLS verification.

Skipped unless TEST_DATABASE_URL points at PostgreSQL (RLS does not exist on
SQLite). Verifies that with FORCE ROW LEVEL SECURITY and the tenant_isolation
policy, setting ``app.tenant_id`` blocks rows belonging to other tenants at the
SQL layer — independent of application-layer filtering.
"""
import os
import uuid
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import IS_POSTGRES

pytestmark = pytest.mark.skipif(not IS_POSTGRES, reason="RLS requires PostgreSQL")


@pytest.mark.asyncio
async def test_rls_blocks_cross_tenant_rows(db: AsyncSession):
    t1, t2 = uuid.uuid4(), uuid.uuid4()

    # Seed one customer per tenant BEFORE enabling RLS.
    for tid in (t1, t2):
        await db.execute(text(
            "INSERT INTO customers (id, tenant_id, name, category, status, is_active) "
            "VALUES (:id, :tid, 'C', 'commercial', 'active', true)"
        ), {"id": uuid.uuid4(), "tid": tid})

    # Enable the tenant_isolation policy.
    await db.execute(text("ALTER TABLE customers ENABLE ROW LEVEL SECURITY"))
    await db.execute(text("DROP POLICY IF EXISTS tenant_isolation ON customers"))
    await db.execute(text(
        "CREATE POLICY tenant_isolation ON customers "
        "USING (tenant_id = current_setting('app.tenant_id', true)::uuid)"
    ))
    await db.execute(text("ALTER TABLE customers FORCE ROW LEVEL SECURITY"))

    # Superusers/owners bypass RLS; the app must connect as a limited role.
    # Switch to one (transaction-scoped) to verify the policy actually applies —
    # this mirrors the production deployment requirement (WS1.3).
    await db.execute(text("DROP ROLE IF EXISTS rls_check_role"))
    await db.execute(text("CREATE ROLE rls_check_role"))
    await db.execute(text("GRANT USAGE ON SCHEMA public TO rls_check_role"))
    await db.execute(text("GRANT SELECT ON customers TO rls_check_role"))
    await db.execute(text("SET LOCAL ROLE rls_check_role"))
    await db.execute(text("SELECT set_config('search_path', 'public', true)"))

    # Scope to tenant 1 → only tenant 1's row is visible at the SQL layer.
    await db.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": str(t1)})
    visible = (await db.execute(text("SELECT tenant_id FROM customers"))).scalars().all()
    assert len(visible) == 1
    assert str(visible[0]) == str(t1)
