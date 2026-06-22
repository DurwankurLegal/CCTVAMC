"""Tamper-evident audit logging.

Every create/update/delete routed through ``TenantRepository`` records an
``AuditLog`` row whose ``chain_hash`` is ``sha256(previous_hash + payload)``,
forming a per-tenant hash chain. A broken or edited row invalidates every
subsequent hash, making tampering detectable.

Serialization keeps only column values (no relationships) and is JSON-safe.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select, desc
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

GENESIS_HASH = "0" * 64


def _json_default(value):
    if isinstance(value, (UUID, Decimal)):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def to_dict(obj) -> dict:
    """Serialise an ORM object's column values to a JSON-safe dict."""
    mapper = sa_inspect(obj).mapper
    data = {}
    for col in mapper.column_attrs:
        val = getattr(obj, col.key)
        if isinstance(val, (UUID, Decimal, datetime, date)):
            val = _json_default(val)
        data[col.key] = val
    return data


def diff(obj) -> tuple[dict, dict]:
    """Return (before, after) for the dirty columns of an ORM object."""
    state = sa_inspect(obj)
    before, after = {}, {}
    for attr in state.attrs:
        hist = attr.history
        if hist.has_changes():
            before[attr.key] = _json_default(hist.deleted[0]) if hist.deleted else None
            after[attr.key] = _json_default(hist.added[0]) if hist.added else None
    return before, after


async def _previous_hash(session: AsyncSession, tenant_id: UUID) -> str:
    result = await session.execute(
        select(AuditLog.chain_hash)
        .where(AuditLog.tenant_id == tenant_id)
        .order_by(desc(AuditLog.created_at), desc(AuditLog.id))
        .limit(1)
    )
    return result.scalar_one_or_none() or GENESIS_HASH


async def write_audit(
    session: AsyncSession,
    tenant_id: UUID,
    entity_type: str,
    entity_id: Optional[UUID],
    action: str,
    before: Optional[dict],
    after: Optional[dict],
    actor_user_id: Optional[UUID] = None,
) -> AuditLog:
    prev = await _previous_hash(session, tenant_id)
    payload = {
        "tenant_id": str(tenant_id),
        "entity_type": entity_type,
        "entity_id": str(entity_id) if entity_id else None,
        "action": action,
        "before": before,
        "after": after,
        "actor_user_id": str(actor_user_id) if actor_user_id else None,
    }
    chain_hash = AuditLog.compute_hash(prev, payload)
    entry = AuditLog(
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        before_state=before,
        after_state=after,
        chain_hash=chain_hash,
    )
    session.add(entry)
    await session.flush()
    return entry


async def verify_chain(session: AsyncSession, tenant_id: UUID) -> bool:
    """Recompute the chain for a tenant; return True if intact."""
    result = await session.execute(
        select(AuditLog)
        .where(AuditLog.tenant_id == tenant_id)
        .order_by(AuditLog.created_at, AuditLog.id)
    )
    prev = GENESIS_HASH
    for row in result.scalars().all():
        payload = {
            "tenant_id": str(row.tenant_id),
            "entity_type": row.entity_type,
            "entity_id": str(row.entity_id) if row.entity_id else None,
            "action": row.action,
            "before": row.before_state,
            "after": row.after_state,
            "actor_user_id": str(row.actor_user_id) if row.actor_user_id else None,
        }
        if AuditLog.compute_hash(prev, payload) != row.chain_hash:
            return False
        prev = row.chain_hash
    return True
