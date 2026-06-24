"""
Integration tests — plan-limit enforcement (Phase 1)
=====================================================
enforce_limit must block creating resources beyond the tenant's plan caps.
Starter caps: max_users=5, max_technicians=3. Exercised through the user
service so the same code path the API uses is covered.
"""
import uuid

import pytest
from fastapi import HTTPException
from app.models.tenant import Tenant
from app.models.user import TenantRole
from app.schemas.user import UserCreate
from app.services.user import create_user


async def _starter_tenant(db):
    t = Tenant(id=uuid.uuid4(), name="Starter Co", slug=f"starter-{uuid.uuid4().hex[:8]}",
               plan="starter", status="active", is_active=True)
    db.add(t)
    await db.flush()
    return t


def _payload(email, role):
    return UserCreate(email=email, full_name="U", password="Pass@1234", role=role)


@pytest.mark.asyncio
async def test_technician_limit_enforced(db):
    t = await _starter_tenant(db)
    # 3 technicians allowed on starter.
    for i in range(3):
        await create_user(db, t.id, _payload(f"tech{i}@test.com", TenantRole.TECHNICIAN))
    # 4th technician must be rejected.
    with pytest.raises(HTTPException) as exc:
        await create_user(db, t.id, _payload("tech3@test.com", TenantRole.TECHNICIAN))
    assert exc.value.status_code == 403
    assert "technicians" in exc.value.detail


@pytest.mark.asyncio
async def test_non_technician_not_charged_to_technician_cap(db):
    t = await _starter_tenant(db)
    # 3 viewers do not consume the technician cap...
    for i in range(3):
        await create_user(db, t.id, _payload(f"view{i}@test.com", TenantRole.VIEWER))
    # ...so a technician can still be created (users used=3 < 5, techs used=0 < 3).
    u = await create_user(db, t.id, _payload("tech@test.com", TenantRole.TECHNICIAN))
    assert u.role == TenantRole.TECHNICIAN
