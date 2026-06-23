"""
Integration tests — Sales Orders API
========================================
Covers: create/list sales orders, total computation, auth guard.
"""
import pytest
from datetime import date


BASE = "/api/v1/sales-orders"


async def _make_customer(client, headers):
    r = await client.post("/api/v1/customers",
                          json={"name": "SO Cust", "category": "commercial"},
                          headers=headers)
    return r.json()["id"]


def _payload(cid):
    return {
        "customer_id": cid,
        "order_date": str(date.today()),
        "line_items": [
            {"description": "DVR", "quantity": 2, "unit_price": 8000.0, "amount": 16000.0},
        ],
    }


@pytest.mark.asyncio
async def test_sales_orders_requires_auth(client):
    r = await client.get(BASE)
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_sales_order(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    r = await client.post(BASE, json=_payload(cid), headers=auth_headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["order_number"].startswith("SO-")
    assert body["total_amount"] == 16000.0


@pytest.mark.asyncio
async def test_list_sales_orders(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    await client.post(BASE, json=_payload(cid), headers=auth_headers)
    r = await client.get(BASE, headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_sales_order_numbers_are_unique_and_sequential(client, auth_headers):
    """Regression (BUG-1): order numbers come from the durable DB sequence,
    so successive orders get distinct, monotonically increasing numbers."""
    cid = await _make_customer(client, auth_headers)
    numbers = []
    for _ in range(3):
        r = await client.post(BASE, json=_payload(cid), headers=auth_headers)
        assert r.status_code == 201, r.text
        numbers.append(r.json()["order_number"])
    assert len(set(numbers)) == 3                       # all unique
    assert all(n.startswith("SO-") for n in numbers)
    # Trailing counter strictly increases.
    tails = [int(n.split("-")[-1]) for n in numbers]
    assert tails == sorted(tails) and tails[0] != tails[-1]
