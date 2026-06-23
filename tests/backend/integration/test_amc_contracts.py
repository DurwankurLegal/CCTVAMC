"""
Integration tests — AMC Contracts API
=======================================
Covers: create, list, get, update, activate (PM schedule generation),
        idempotent PM generation, contract number formatting.
"""
import uuid
import pytest
from datetime import date, timedelta


BASE = "/api/v1/amc"
TODAY = date.today()
END = TODAY + timedelta(days=365)


async def _make_customer(client, headers) -> str:
    r = await client.post("/api/v1/customers",
                          json={"name": "AMC Customer", "category": "commercial"},
                          headers=headers)
    assert r.status_code == 201
    return r.json()["id"]


AMC_PAYLOAD = lambda cid: {
    "customer_id": cid,
    "start_date": str(TODAY),
    "end_date": str(END),
    "annual_amount": 60000.0,
    "payment_frequency": "annual",
    "preventive_visits_per_year": 4,
    "asset_ids": [],
}


# ── Auth guard ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_amc_requires_auth(client):
    r = await client.get(BASE)
    assert r.status_code in (401, 403)


# ── Create ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_amc_success(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    r = await client.post(BASE, json=AMC_PAYLOAD(cid), headers=auth_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["contract_number"].startswith("AMC-")
    assert body["status"] == "draft"


@pytest.mark.asyncio
async def test_create_amc_contract_numbers_are_unique(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    r1 = await client.post(BASE, json=AMC_PAYLOAD(cid), headers=auth_headers)
    r2 = await client.post(BASE, json=AMC_PAYLOAD(cid), headers=auth_headers)
    assert r1.json()["contract_number"] != r2.json()["contract_number"]


@pytest.mark.asyncio
async def test_create_amc_requires_customer_id(client, auth_headers):
    r = await client.post(BASE,
                          json={"start_date": str(TODAY), "end_date": str(END),
                                "annual_amount": 10000},
                          headers=auth_headers)
    assert r.status_code == 422


# ── List ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_amc_empty(client, auth_headers):
    r = await client.get(BASE, headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_amc_returns_created(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    await client.post(BASE, json=AMC_PAYLOAD(cid), headers=auth_headers)
    r = await client.get(BASE, headers=auth_headers)
    assert len(r.json()) == 1


# ── Get ───────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_amc_by_id(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    cr = await client.post(BASE, json=AMC_PAYLOAD(cid), headers=auth_headers)
    aid = cr.json()["id"]
    r = await client.get(f"{BASE}/{aid}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["id"] == aid


@pytest.mark.asyncio
async def test_get_nonexistent_amc_returns_404(client, auth_headers):
    r = await client.get(f"{BASE}/{uuid.uuid4()}", headers=auth_headers)
    assert r.status_code == 404


# ── Activate → PM schedule generation ────────────────────────────────────────

@pytest.mark.asyncio
async def test_activate_amc_generates_pm_schedule(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    cr = await client.post(BASE, json=AMC_PAYLOAD(cid), headers=auth_headers)
    aid = cr.json()["id"]
    r = await client.post(f"{BASE}/{aid}/activate", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "active"

    # PM schedule should now exist
    pm_r = await client.get(f"{BASE}/{aid}/pm-schedule", headers=auth_headers)
    assert pm_r.status_code == 200
    # pm-schedule returns {"summary": {...}, "visits": [...]}.
    pm_list = pm_r.json()["visits"]
    assert len(pm_list) == 4   # preventive_visits_per_year=4


@pytest.mark.asyncio
async def test_activate_amc_idempotent_pm_generation(client, auth_headers):
    """Activating the same contract twice must not create duplicate PM visits."""
    cid = await _make_customer(client, auth_headers)
    cr = await client.post(BASE, json=AMC_PAYLOAD(cid), headers=auth_headers)
    aid = cr.json()["id"]
    await client.post(f"{BASE}/{aid}/activate", headers=auth_headers)
    await client.post(f"{BASE}/{aid}/activate", headers=auth_headers)
    pm_r = await client.get(f"{BASE}/{aid}/pm-schedule", headers=auth_headers)
    assert len(pm_r.json()["visits"]) == 4  # not 8


@pytest.mark.asyncio
async def test_pm_schedule_sequence_numbers(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    cr = await client.post(BASE, json=AMC_PAYLOAD(cid), headers=auth_headers)
    aid = cr.json()["id"]
    await client.post(f"{BASE}/{aid}/activate", headers=auth_headers)
    pm_r = await client.get(f"{BASE}/{aid}/pm-schedule", headers=auth_headers)
    seq_nos = [pm["sequence_no"] for pm in pm_r.json()["visits"]]
    assert seq_nos == [1, 2, 3, 4]


# ── Update ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_amc_annual_amount(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    cr = await client.post(BASE, json=AMC_PAYLOAD(cid), headers=auth_headers)
    aid = cr.json()["id"]
    r = await client.patch(f"{BASE}/{aid}",
                           json={"annual_amount": 75000.0},
                           headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["annual_amount"] == 75000.0
