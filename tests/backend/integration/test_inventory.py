"""
Integration tests — Inventory API
=====================================
Covers: create item, list, get, stock adjustment (in/out/consumption),
        insufficient-stock rejection, low-stock list, auth guard.

Real API contract (verified against app/api/v1/inventory.py + schemas):
  * InventoryItemCreate has NO current_stock — items always start at 0 stock.
  * Stock is changed via POST /inventory/adjust (StockAdjustment body), not a
    per-item sub-route.
  * MovementType values: purchase, sale, consumption, transfer, adjustment,
    return. (There is no "stock_in".)
  * low-stock returns items where current_stock <= reorder_level.
"""
import uuid
import pytest


BASE = "/api/v1/inventory"

ITEM_PAYLOAD = {
    "name": "CCTV Camera 2MP",
    "part_number": "CAM-2MP-001",
    "unit": "pcs",
    "reorder_level": 10,
    "unit_cost": 2500.0,
}


async def _create_item(client, headers, **overrides):
    payload = {**ITEM_PAYLOAD, **overrides}
    r = await client.post(BASE, json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _adjust(client, headers, item_id, quantity, movement_type):
    return await client.post(f"{BASE}/adjust", json={
        "item_id": item_id,
        "quantity": quantity,
        "movement_type": movement_type,
    }, headers=headers)


# ── Auth guard ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_inventory_requires_auth(client):
    r = await client.get(BASE)
    assert r.status_code in (401, 403)


# ── Create item ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_inventory_item(client, auth_headers):
    r = await client.post(BASE, json=ITEM_PAYLOAD, headers=auth_headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "CCTV Camera 2MP"
    # Items always start at zero stock; stock changes only via /adjust.
    assert body["current_stock"] == 0


@pytest.mark.asyncio
async def test_create_item_missing_name(client, auth_headers):
    r = await client.post(BASE, json={"part_number": "X"}, headers=auth_headers)
    assert r.status_code == 422


# ── List ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_items_empty(client, auth_headers):
    r = await client.get(BASE, headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_items_returns_created(client, auth_headers):
    await _create_item(client, auth_headers)
    r = await client.get(BASE, headers=auth_headers)
    assert len(r.json()) == 1


# ── Get single ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_item_by_id(client, auth_headers):
    iid = await _create_item(client, auth_headers)
    r = await client.get(f"{BASE}/{iid}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["id"] == iid


@pytest.mark.asyncio
async def test_get_nonexistent_item_returns_404(client, auth_headers):
    r = await client.get(f"{BASE}/{uuid.uuid4()}", headers=auth_headers)
    assert r.status_code == 404


# ── Stock adjustment ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stock_in_increases_stock(client, auth_headers):
    iid = await _create_item(client, auth_headers)
    r = await _adjust(client, auth_headers, iid, 20, "purchase")
    assert r.status_code == 200, r.text
    assert r.json()["current_stock"] == 20


@pytest.mark.asyncio
async def test_stock_out_decreases_stock(client, auth_headers):
    iid = await _create_item(client, auth_headers)
    await _adjust(client, auth_headers, iid, 20, "purchase")
    r = await _adjust(client, auth_headers, iid, -5, "consumption")
    assert r.status_code == 200, r.text
    assert r.json()["current_stock"] == 15


@pytest.mark.asyncio
async def test_stock_out_below_zero_rejected(client, auth_headers):
    iid = await _create_item(client, auth_headers)
    await _adjust(client, auth_headers, iid, 3, "purchase")
    r = await _adjust(client, auth_headers, iid, -10, "consumption")
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_adjust_nonexistent_item_returns_404(client, auth_headers):
    fake_id = str(uuid.uuid4())
    r = await _adjust(client, auth_headers, fake_id, 5, "purchase")
    assert r.status_code == 404


# ── Low-stock ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_low_stock_list_empty_when_all_adequate(client, auth_headers):
    iid = await _create_item(client, auth_headers, reorder_level=10)
    await _adjust(client, auth_headers, iid, 50, "purchase")  # stock 50 > reorder 10
    r = await client.get(f"{BASE}/low-stock", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_low_stock_list_returns_low_items(client, auth_headers):
    iid = await _create_item(client, auth_headers, reorder_level=10)
    await _adjust(client, auth_headers, iid, 5, "purchase")  # stock 5 <= reorder 10
    r = await client.get(f"{BASE}/low-stock", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1
