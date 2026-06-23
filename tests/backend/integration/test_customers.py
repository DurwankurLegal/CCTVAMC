"""
Integration tests — Customers API
====================================
Covers: list, create, get, update, add contact, list contacts,
        interaction history, 404 on missing ID, auth guard.
"""
import uuid
import pytest


BASE = "/api/v1/customers"

CUSTOMER_PAYLOAD = {
    "name": "Sunrise Housing Society",
    "category": "chs",
    "phone": "9876543210",
    "email": "sunrise@chs.in",
    "address": "Plot 12, Andheri West, Mumbai",
    "status": "active",
}


# ── Auth guard ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_customers_requires_auth(client):
    r = await client.get(BASE)
    assert r.status_code in (401, 403)


# ── Create ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_customer_success(client, auth_headers):
    r = await client.post(BASE, json=CUSTOMER_PAYLOAD, headers=auth_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Sunrise Housing Society"
    assert "id" in body


@pytest.mark.asyncio
async def test_create_customer_missing_required_field(client, auth_headers):
    r = await client.post(BASE, json={"phone": "9876543210"}, headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_customer_returns_correct_category(client, auth_headers):
    payload = {**CUSTOMER_PAYLOAD, "name": "Raj Stores", "category": "single_shop"}
    r = await client.post(BASE, json=payload, headers=auth_headers)
    assert r.status_code == 201
    assert r.json()["category"] == "single_shop"


# ── List ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_customers_empty_initially(client, auth_headers):
    r = await client.get(BASE, headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_customers_returns_created(client, auth_headers):
    await client.post(BASE, json=CUSTOMER_PAYLOAD, headers=auth_headers)
    r = await client.get(BASE, headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_list_customers_pagination(client, auth_headers):
    for i in range(5):
        await client.post(BASE, json={**CUSTOMER_PAYLOAD, "name": f"Customer {i}"},
                          headers=auth_headers)
    r = await client.get(f"{BASE}?limit=2", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 2


# ── Get single ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_customer_by_id(client, auth_headers):
    cr = await client.post(BASE, json=CUSTOMER_PAYLOAD, headers=auth_headers)
    cid = cr.json()["id"]
    r = await client.get(f"{BASE}/{cid}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["id"] == cid


@pytest.mark.asyncio
async def test_get_nonexistent_customer_returns_404(client, auth_headers):
    r = await client.get(f"{BASE}/{uuid.uuid4()}", headers=auth_headers)
    assert r.status_code == 404


# ── Update ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_customer_name(client, auth_headers):
    cr = await client.post(BASE, json=CUSTOMER_PAYLOAD, headers=auth_headers)
    cid = cr.json()["id"]
    r = await client.patch(f"{BASE}/{cid}", json={"name": "Updated Name"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_update_nonexistent_customer_returns_404(client, auth_headers):
    r = await client.patch(f"{BASE}/{uuid.uuid4()}", json={"name": "X"}, headers=auth_headers)
    assert r.status_code == 404


# ── Contacts ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_contact_to_customer(client, auth_headers):
    cr = await client.post(BASE, json=CUSTOMER_PAYLOAD, headers=auth_headers)
    cid = cr.json()["id"]
    r = await client.post(f"{BASE}/{cid}/contacts",
                          json={"name": "John Doe", "phone": "9000000001", "role": "admin"},
                          headers=auth_headers)
    assert r.status_code == 201
    assert r.json()["name"] == "John Doe"


@pytest.mark.asyncio
async def test_list_contacts_for_customer(client, auth_headers):
    cr = await client.post(BASE, json=CUSTOMER_PAYLOAD, headers=auth_headers)
    cid = cr.json()["id"]
    await client.post(f"{BASE}/{cid}/contacts",
                      json={"name": "Jane", "phone": "9000000002"},
                      headers=auth_headers)
    r = await client.get(f"{BASE}/{cid}/contacts", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_add_contact_to_nonexistent_customer(client, auth_headers):
    r = await client.post(f"{BASE}/{uuid.uuid4()}/contacts",
                          json={"name": "Nobody", "phone": "0000000000"},
                          headers=auth_headers)
    assert r.status_code == 404


# ── Interaction history ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_interaction_history_empty(client, auth_headers):
    cr = await client.post(BASE, json=CUSTOMER_PAYLOAD, headers=auth_headers)
    cid = cr.json()["id"]
    r = await client.get(f"{BASE}/{cid}/history", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert "leads" in body
    assert "tickets" in body
    assert "invoices" in body
    assert "quotations" in body


@pytest.mark.asyncio
async def test_interaction_history_nonexistent_customer(client, auth_headers):
    r = await client.get(f"{BASE}/{uuid.uuid4()}/history", headers=auth_headers)
    assert r.status_code == 404
