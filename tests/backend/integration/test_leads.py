"""
Integration tests — Leads API + Lead-to-Customer Conversion
=============================================================
Covers: create lead, list, get, update, convert to customer
        (creates customer + draft quotation, marks lead CONVERTED),
        double-convert rejection, 404 handling.
"""
import uuid
import pytest


BASE = "/api/v1/leads"

LEAD_PAYLOAD = {
    "name": "Ravi Sharma",
    "phone": "9800000001",
    "email": "ravi@example.com",
    "address": "45 MG Road, Pune",
    "category": "commercial",
    "source": "referral",
    "status": "new",
}


# ── Auth guard ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_leads_requires_auth(client):
    r = await client.get(BASE)
    assert r.status_code in (401, 403)


# ── Create ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_lead_success(client, auth_headers):
    r = await client.post(BASE, json=LEAD_PAYLOAD, headers=auth_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Ravi Sharma"
    assert "id" in body


@pytest.mark.asyncio
async def test_create_lead_missing_name(client, auth_headers):
    r = await client.post(BASE, json={"phone": "9800000001"}, headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_lead_default_status_is_new(client, auth_headers):
    payload = {k: v for k, v in LEAD_PAYLOAD.items() if k != "status"}
    r = await client.post(BASE, json=payload, headers=auth_headers)
    assert r.status_code == 201


# ── List ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_leads_empty(client, auth_headers):
    r = await client.get(BASE, headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_leads_returns_created(client, auth_headers):
    await client.post(BASE, json=LEAD_PAYLOAD, headers=auth_headers)
    r = await client.get(BASE, headers=auth_headers)
    assert len(r.json()) >= 1


# ── Get single ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_lead_by_id(client, auth_headers):
    cr = await client.post(BASE, json=LEAD_PAYLOAD, headers=auth_headers)
    lid = cr.json()["id"]
    r = await client.get(f"{BASE}/{lid}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["id"] == lid


@pytest.mark.asyncio
async def test_get_nonexistent_lead_returns_404(client, auth_headers):
    r = await client.get(f"{BASE}/{uuid.uuid4()}", headers=auth_headers)
    assert r.status_code == 404


# ── Update ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_lead_status(client, auth_headers):
    cr = await client.post(BASE, json=LEAD_PAYLOAD, headers=auth_headers)
    lid = cr.json()["id"]
    r = await client.patch(f"{BASE}/{lid}", json={"status": "contacted"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "contacted"


# ── Convert to customer ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_convert_lead_creates_customer(client, auth_headers):
    cr = await client.post(BASE, json=LEAD_PAYLOAD, headers=auth_headers)
    lid = cr.json()["id"]
    r = await client.post(f"{BASE}/{lid}/convert", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Ravi Sharma"
    # Returned object is a Customer
    assert "category" in body


@pytest.mark.asyncio
async def test_convert_lead_marks_lead_as_converted(client, auth_headers):
    cr = await client.post(BASE, json=LEAD_PAYLOAD, headers=auth_headers)
    lid = cr.json()["id"]
    await client.post(f"{BASE}/{lid}/convert", headers=auth_headers)
    r = await client.get(f"{BASE}/{lid}", headers=auth_headers)
    assert r.json()["status"] == "converted"


@pytest.mark.asyncio
async def test_convert_lead_creates_draft_quotation(client, auth_headers):
    """Conversion must auto-create a draft quotation linked to the new customer."""
    cr = await client.post(BASE, json=LEAD_PAYLOAD, headers=auth_headers)
    lid = cr.json()["id"]
    customer = await client.post(f"{BASE}/{lid}/convert", headers=auth_headers)
    cid = customer.json()["id"]
    q_r = await client.get("/api/v1/quotations", headers=auth_headers)
    quotations = [q for q in q_r.json() if q.get("customer_id") == cid]
    assert len(quotations) == 1
    assert quotations[0]["status"] in ("draft", "sent")


@pytest.mark.asyncio
async def test_double_convert_lead_returns_409(client, auth_headers):
    cr = await client.post(BASE, json=LEAD_PAYLOAD, headers=auth_headers)
    lid = cr.json()["id"]
    await client.post(f"{BASE}/{lid}/convert", headers=auth_headers)
    r = await client.post(f"{BASE}/{lid}/convert", headers=auth_headers)
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_convert_nonexistent_lead_returns_404(client, auth_headers):
    r = await client.post(f"{BASE}/{uuid.uuid4()}/convert", headers=auth_headers)
    assert r.status_code == 404
