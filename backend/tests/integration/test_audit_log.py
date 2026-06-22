"""Audit logging is written on every mutation and forms a verifiable hash chain."""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.services.audit import verify_chain


@pytest.mark.asyncio
async def test_create_writes_audit_row(client: AsyncClient, db: AsyncSession, admin_token: str, tenant):
    resp = await client.post(
        "/api/v1/customers",
        json={"name": "Audited Co", "category": "commercial"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    rows = (await db.execute(
        select(AuditLog).where(AuditLog.tenant_id == tenant.id, AuditLog.action == "CREATE")
    )).scalars().all()
    assert any(r.entity_type == "Customer" for r in rows)


@pytest.mark.asyncio
async def test_chain_is_valid_and_tamper_detectable(client: AsyncClient, db: AsyncSession, admin_token: str, tenant):
    for name in ("A", "B", "C"):
        await client.post(
            "/api/v1/customers",
            json={"name": name, "category": "single_shop"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert await verify_chain(db, tenant.id) is True

    # Tamper with one row → chain must break.
    row = (await db.execute(
        select(AuditLog).where(AuditLog.tenant_id == tenant.id).limit(1)
    )).scalar_one()
    row.after_state = {"name": "HACKED"}
    await db.flush()
    assert await verify_chain(db, tenant.id) is False
