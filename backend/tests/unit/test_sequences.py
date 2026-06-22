"""Persisted document sequences are unique, gapless and monotonic per tenant."""
import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.sequences import next_number


@pytest.mark.asyncio
async def test_sequence_is_monotonic_and_gapless(db: AsyncSession):
    tenant_id = uuid4()
    numbers = [await next_number(db, tenant_id, "invoice", "INV") for _ in range(5)]
    seqs = [int(n.split("-")[-1]) for n in numbers]
    assert seqs == [1, 2, 3, 4, 5]
    assert len(set(numbers)) == 5


@pytest.mark.asyncio
async def test_sequences_are_isolated_per_tenant_and_doctype(db: AsyncSession):
    t1, t2 = uuid4(), uuid4()
    a = await next_number(db, t1, "invoice", "INV")
    b = await next_number(db, t2, "invoice", "INV")
    c = await next_number(db, t1, "quotation", "QT")
    assert a.endswith("00001")
    assert b.endswith("00001")  # separate tenant restarts the counter
    assert c.endswith("00001")  # separate doc_type restarts the counter
