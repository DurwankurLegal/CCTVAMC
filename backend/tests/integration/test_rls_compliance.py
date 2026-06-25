"""Database-level RLS compliance verification.
Runs only when running on PostgreSQL.
Checks that all tables in the public schema possessing a 'tenant_id' column have Row-Level Security active.
"""
import os
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from tests.conftest import IS_POSTGRES

pytestmark = pytest.mark.skipif(not IS_POSTGRES, reason="RLS compliance requires PostgreSQL")


@pytest.mark.asyncio
async def test_every_tenant_scoped_table_has_rls_enabled(db: AsyncSession):
    # 1. Fetch all table names that have a column named 'tenant_id' in public schema
    tables_query = """
        SELECT DISTINCT table_name
        FROM information_schema.columns
        WHERE column_name = 'tenant_id'
          AND table_schema = 'public'
          AND table_name NOT IN ('tenants'); -- tenants table is platform level, not RLS isolated
    """
    res = await db.execute(text(tables_query))
    tenant_tables = [r[0] for r in res.fetchall()]

    assert len(tenant_tables) > 0, "No tenant-scoped tables found!"

    # 2. For each table, query pg_class to ensure relrowsecurity is true and policies exist
    for table_name in tenant_tables:
        rls_query = """
            SELECT c.relname, c.relrowsecurity
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relname = :table_name;
        """
        res_rls = await db.execute(text(rls_query), {"table_name": table_name})
        row = res_rls.fetchone()
        
        assert row is not None, f"Table {table_name} not found in pg_class"
        assert row[1] is True, f"RLS is NOT enabled on tenant-scoped table: {table_name} (relrowsecurity is False)"

        # 3. Check that at least one policy exists on this table
        policy_query = """
            SELECT COUNT(*)
            FROM pg_policy p
            JOIN pg_class c ON c.oid = p.polrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relname = :table_name;
        """
        res_policy = await db.execute(text(policy_query), {"table_name": table_name})
        policy_count = res_policy.scalar()
        assert policy_count > 0, f"Table {table_name} has RLS enabled but has no policies configured!"
