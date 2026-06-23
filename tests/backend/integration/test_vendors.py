"""
Integration tests — Vendors & Purchase Orders API
====================================================
Covers: create vendor, list, get, update, create PO (auto-increments
        vendor outstanding_payable), vendor payment (reduces payable),
        auth guard, 404 handling.
"""
import uuid
import pytest


BASE = "/api/v1/vendors"

VENDOR_PAYLOAD = {
    "name": "Hikvision Distributors",
    "contact_name": "Rajesh Kumar",
    "phone": "9700000001",
    "email": "sales@hikvision-dist.in",
    "gstin": "27AABCH1234C1Z5",
    "address": "Seepz, Andheri East, Mumbai",
}


# ── Auth guard ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_vendors_requires_auth(client):
    r = await client.get(BASE)
    assert r.status_code in (401, 403)


# ── Create vendor ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_vendor_success(client, auth_headers):
    r = await client.post(BASE, json=VENDOR_PAYLOAD, headers=auth_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Hikvision Distributors"
    assert "id" in body


@pytest.mark.asyncio
async def test_create_vendor_missing_name(client, auth_headers):
    r = await client.post(BASE, json={"phone": "9700000001"}, headers=auth_headers)
    assert r.status_code == 422


# ── List ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_vendors_empty_initially(client, auth_headers):
    r = await client.get(BASE, headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_vendors_returns_created(client, auth_headers):
    await client.post(BASE, json=VENDOR_PAYLOAD, headers=auth_headers)
    r = await client.get(BASE, headers=auth_headers)
    assert len(r.json()) >= 1


# ── Get ───────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_vendor_by_id(client, auth_headers):
    cr = await client.post(BASE, json=VENDOR_PAYLOAD, headers=auth_headers)
    vid = cr.json()["id"]
    r = await client.get(f"{BASE}/{vid}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["id"] == vid


@pytest.mark.asyncio
async def test_get_nonexistent_vendor_returns_404(client, auth_headers):
    r = await client.get(f"{BASE}/{uuid.uuid4()}", headers=auth_headers)
    assert r.status_code == 404


# ── Update ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_vendor_phone(client, auth_headers):
    cr = await client.post(BASE, json=VENDOR_PAYLOAD, headers=auth_headers)
    vid = cr.json()["id"]
    r = await client.patch(f"{BASE}/{vid}", json={"phone": "9000000099"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["phone"] == "9000000099"


# ── Purchase orders ───────────────────────────────────────────────────────────

# Procurement uses flat routes with vendor_id in the body (POCreate /
# VendorPaymentCreate), not nested /{vendor_id}/... sub-resources.

@pytest.mark.asyncio
async def test_create_purchase_order(client, auth_headers):
    cr = await client.post(BASE, json=VENDOR_PAYLOAD, headers=auth_headers)
    vid = cr.json()["id"]
    r = await client.post(f"{BASE}/purchase-orders", json={
        "vendor_id": vid,
        "line_items": [
            {"description": "CCTV Camera", "qty": 10, "unit_cost": 5000},
        ],
        "notes": "Initial stock order",
    }, headers=auth_headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["po_number"].startswith("PO-")
    assert body["total_amount"] == 50000.0


@pytest.mark.asyncio
async def test_create_po_increments_vendor_outstanding(client, auth_headers):
    cr = await client.post(BASE, json=VENDOR_PAYLOAD, headers=auth_headers)
    vid = cr.json()["id"]
    await client.post(f"{BASE}/purchase-orders", json={
        "vendor_id": vid,
        "line_items": [{"description": "Camera", "qty": 2, "unit_cost": 3000}],
    }, headers=auth_headers)
    vr = await client.get(f"{BASE}/{vid}", headers=auth_headers)
    assert vr.json()["outstanding_payable"] == 6000.0


@pytest.mark.asyncio
async def test_list_purchase_orders(client, auth_headers):
    cr = await client.post(BASE, json=VENDOR_PAYLOAD, headers=auth_headers)
    vid = cr.json()["id"]
    await client.post(f"{BASE}/purchase-orders",
                      json={"vendor_id": vid, "line_items": [{"qty": 1, "unit_cost": 100}]},
                      headers=auth_headers)
    r = await client.get(f"{BASE}/purchase-orders", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_create_po_for_nonexistent_vendor(client, auth_headers):
    r = await client.post(f"{BASE}/purchase-orders",
                          json={"vendor_id": str(uuid.uuid4()), "line_items": []},
                          headers=auth_headers)
    assert r.status_code == 404


# ── Vendor payment ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_record_vendor_payment_reduces_outstanding(client, auth_headers):
    cr = await client.post(BASE, json=VENDOR_PAYLOAD, headers=auth_headers)
    vid = cr.json()["id"]
    # Create a PO first so there's outstanding payable
    await client.post(f"{BASE}/purchase-orders", json={
        "vendor_id": vid,
        "line_items": [{"qty": 1, "unit_cost": 10000}],
    }, headers=auth_headers)
    r = await client.post(f"{BASE}/payments",
                          json={"vendor_id": vid, "amount": 5000.0, "method": "bank_transfer"},
                          headers=auth_headers)
    assert r.status_code == 201, r.text
    vr = await client.get(f"{BASE}/{vid}", headers=auth_headers)
    assert vr.json()["outstanding_payable"] == 5000.0
