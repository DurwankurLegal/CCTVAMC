"""
Integration tests — Engineer Visits API (field service)
==========================================================
Covers: create visit, list/get, geo check-in / check-out with work log,
        auth guard.
"""
import uuid
import pytest


BASE = "/api/v1/engineer-visits"


async def _make_ticket(client, headers):
    cr = await client.post("/api/v1/customers",
                           json={"name": "Visit Cust", "category": "commercial"},
                           headers=headers)
    cid = cr.json()["id"]
    tr = await client.post("/api/v1/service-tickets", json={
        "customer_id": cid, "complaint": "Camera offline", "priority": "high",
    }, headers=headers)
    return tr.json()["id"]


@pytest.mark.asyncio
async def test_visits_requires_auth(client):
    r = await client.get(BASE)
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_visit(client, auth_headers):
    tid = await _make_ticket(client, auth_headers)
    r = await client.post(BASE, json={"ticket_id": tid, "visit_type": "corrective"},
                          headers=auth_headers)
    assert r.status_code == 201, r.text
    assert r.json()["ticket_id"] == tid


@pytest.mark.asyncio
async def test_list_visits(client, auth_headers):
    tid = await _make_ticket(client, auth_headers)
    await client.post(BASE, json={"ticket_id": tid}, headers=auth_headers)
    r = await client.get(BASE, headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1


@pytest.mark.asyncio
async def test_get_visit_by_id(client, auth_headers):
    tid = await _make_ticket(client, auth_headers)
    cr = await client.post(BASE, json={"ticket_id": tid}, headers=auth_headers)
    vid = cr.json()["id"]
    r = await client.get(f"{BASE}/{vid}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["id"] == vid


@pytest.mark.asyncio
async def test_checkin_records_geo(client, auth_headers):
    tid = await _make_ticket(client, auth_headers)
    cr = await client.post(BASE, json={"ticket_id": tid}, headers=auth_headers)
    vid = cr.json()["id"]
    r = await client.post(f"{BASE}/{vid}/checkin",
                          json={"lat": 18.52, "lng": 73.85}, headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["checkin_at"] is not None
    assert r.json()["checkin_lat"] == 18.52


@pytest.mark.asyncio
async def test_checkout_records_work(client, auth_headers):
    tid = await _make_ticket(client, auth_headers)
    cr = await client.post(BASE, json={"ticket_id": tid}, headers=auth_headers)
    vid = cr.json()["id"]
    await client.post(f"{BASE}/{vid}/checkin",
                      json={"lat": 18.52, "lng": 73.85}, headers=auth_headers)
    r = await client.post(f"{BASE}/{vid}/checkout", json={
        "lat": 18.52, "lng": 73.85,
        "work_performed": "Replaced PSU",
        "customer_feedback": "Resolved",
    }, headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["checkout_at"] is not None
    assert r.json()["work_performed"] == "Replaced PSU"
