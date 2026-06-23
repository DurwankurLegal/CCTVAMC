"""
Integration tests — Installations API (project lifecycle)
============================================================
Covers: create work order, list/get, survey capture, OTP-gated handover that
        spins up an AMC contract, auth guard.
"""
import uuid
import pytest
from datetime import date, timedelta


BASE = "/api/v1/installations"


async def _make_customer(client, headers):
    r = await client.post("/api/v1/customers",
                          json={"name": "Install Cust", "category": "commercial"},
                          headers=headers)
    return r.json()["id"]


def _payload(cid):
    return {
        "customer_id": cid,
        "target_completion_date": str(date.today() + timedelta(days=10)),
    }


@pytest.mark.asyncio
async def test_installations_requires_auth(client):
    r = await client.get(BASE)
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_installation(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    r = await client.post(BASE, json=_payload(cid), headers=auth_headers)
    assert r.status_code == 201, r.text
    assert r.json()["work_order_number"]


@pytest.mark.asyncio
async def test_list_installations(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    await client.post(BASE, json=_payload(cid), headers=auth_headers)
    r = await client.get(BASE, headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_get_installation_by_id(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    cr = await client.post(BASE, json=_payload(cid), headers=auth_headers)
    iid = cr.json()["id"]
    r = await client.get(f"{BASE}/{iid}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["id"] == iid


@pytest.mark.asyncio
async def test_record_survey(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    cr = await client.post(BASE, json=_payload(cid), headers=auth_headers)
    iid = cr.json()["id"]
    r = await client.post(f"{BASE}/{iid}/survey", json={
        "survey_date": str(date.today()),
        "survey_notes": "Need 6 cameras",
        "recommended_camera_count": 6,
    }, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["recommended_camera_count"] == 6


@pytest.mark.asyncio
async def test_handover_requires_correct_otp(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    cr = await client.post(BASE, json=_payload(cid), headers=auth_headers)
    iid = cr.json()["id"]
    await client.post(f"{BASE}/{iid}/handover-otp", headers=auth_headers)
    r = await client.post(f"{BASE}/{iid}/handover",
                          json={"otp": "000000", "amc_annual_amount": 12000},
                          headers=auth_headers)
    assert r.status_code in (400, 403, 422)


@pytest.mark.asyncio
async def test_handover_with_otp_creates_amc(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    cr = await client.post(BASE, json=_payload(cid), headers=auth_headers)
    iid = cr.json()["id"]
    otp_r = await client.post(f"{BASE}/{iid}/handover-otp", headers=auth_headers)
    otp = otp_r.json()["otp"]
    r = await client.post(f"{BASE}/{iid}/handover", json={
        "otp": otp, "amc_annual_amount": 12000, "amc_months": 12,
        "preventive_visits_per_year": 2,
    }, headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["amc_contract_id"] is not None
