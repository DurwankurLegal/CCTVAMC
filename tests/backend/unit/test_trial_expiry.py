"""
Unit tests — trial expiry sweep (Phase 1)
==========================================
run_trial_expiry suspends only TRIAL tenants whose trial_ends_at is in the past.
"""
import uuid
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import select
from app.models.tenant import Tenant
from app.services.tenant import run_trial_expiry


def _tenant(slug, status, trial_ends_at):
    return Tenant(
        id=uuid.uuid4(), name=slug, slug=slug, plan="starter",
        status=status, is_active=(status != "suspended"), trial_ends_at=trial_ends_at,
    )


@pytest.mark.asyncio
async def test_run_trial_expiry_suspends_only_expired_trials(db):
    now = datetime.now(timezone.utc)
    expired = _tenant("exp-trial", "trial", now - timedelta(days=1))
    future = _tenant("fut-trial", "trial", now + timedelta(days=3))
    active = _tenant("active-co", "active", None)
    db.add_all([expired, future, active])
    await db.flush()

    n = await run_trial_expiry(db)
    assert n == 1

    async def _status(t):
        return (await db.execute(select(Tenant.status).where(Tenant.id == t.id))).scalar_one()

    assert await _status(expired) == "suspended"
    assert await _status(future) == "trial"
    assert await _status(active) == "active"


@pytest.mark.asyncio
async def test_run_trial_expiry_noop_when_nothing_expired(db):
    now = datetime.now(timezone.utc)
    db.add(_tenant("fut-only", "trial", now + timedelta(days=10)))
    await db.flush()
    assert await run_trial_expiry(db) == 0
