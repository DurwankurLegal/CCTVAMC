"""Concurrency-safe document number generation.

Replaces the previous in-memory counters (which produced duplicate, non-sequential
numbers across workers/restarts). Uses an atomic row-locked increment so numbers
are unique, gapless and monotonic per tenant/doc-type/year.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sequence import DocumentSequence


async def next_number(
    db: AsyncSession,
    tenant_id: UUID,
    doc_type: str,
    prefix: str,
    *,
    width: int = 5,
    include_year: bool = True,
) -> str:
    """Return the next formatted document number, e.g. ``DUR-2026-00042``.

    The counter row is locked ``FOR UPDATE`` (on PostgreSQL) for the duration of
    the transaction so concurrent callers serialise rather than collide.
    """
    year = datetime.now(timezone.utc).year
    dialect = (await db.connection()).dialect.name

    stmt = select(DocumentSequence).where(
        DocumentSequence.tenant_id == tenant_id,
        DocumentSequence.doc_type == doc_type,
        DocumentSequence.year == year,
    )
    if dialect == "postgresql":
        stmt = stmt.with_for_update()

    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        row = DocumentSequence(tenant_id=tenant_id, doc_type=doc_type, year=year, last_value=0)
        db.add(row)
        await db.flush()

    row.last_value += 1
    await db.flush()

    seq = f"{row.last_value:0{width}d}"
    if include_year:
        return f"{prefix}-{year}-{seq}"
    return f"{prefix}-{seq}"
