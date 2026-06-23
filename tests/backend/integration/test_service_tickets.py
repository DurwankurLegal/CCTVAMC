"""
Integration tests — Service Tickets API
==========================================
Covers: create, list, get, update, close, SLA timestamps,
        comments CRUD, priority/status validation, auth guard.
"""
import uuid
import pytest


BASE = "/api/v1/service-tickets"

TICKET_PAYLOAD = {
    "complaint": "CCTV camera not recording",
    "priority": "high",
    "status": "open",
}


async def _make_customer(client, auth_headers) -> str:
    r = await client.post("/api/v1/customers", json={
        "name": "Test Customer",
        "category": "commercial",
    }, headers=auth_headers)
    return r.json()["id"]


# ── Auth guard ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_tickets_requires_auth(client):
    r = await client.get(BASE)
    assert r.status_code in (401, 403)


# ── Create ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_ticket_success(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    r = await client.post(BASE, json={**TICKET_PAYLOAD, "customer_id": cid},
                          headers=auth_headers)
    assert r.status_code == 201
    body = r.json()
    assert "ticket_number" in body
    assert body["ticket_number"].startswith("TKT-")
    assert "sla_due_at" in body


@pytest.mark.asyncio
async def test_create_ticket_sla_set_for_high_priority(client, auth_headers):
    """High priority → SLA due in 8 hours."""
    from datetime import datetime, timezone, timedelta
    cid = await _make_customer(client, auth_headers)
    r = await client.post(BASE, json={**TICKET_PAYLOAD, "customer_id": cid, "priority": "high"},
                          headers=auth_headers)
    assert r.status_code == 201
    sla = datetime.fromisoformat(r.json()["sla_due_at"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    # SQLite drops tz info, so sla_due_at may deserialize as naive — normalise.
    if sla.tzinfo is None:
        now = now.replace(tzinfo=None)
    diff_hours = (sla - now).total_seconds() / 3600
    assert 7 < diff_hours < 9


@pytest.mark.asyncio
async def test_create_ticket_sla_set_for_critical_priority(client, auth_headers):
    """Critical → SLA in 4 hours."""
    from datetime import datetime, timezone
    cid = await _make_customer(client, auth_headers)
    r = await client.post(BASE, json={**TICKET_PAYLOAD, "customer_id": cid, "priority": "critical"},
                          headers=auth_headers)
    assert r.status_code == 201
    sla = datetime.fromisoformat(r.json()["sla_due_at"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    if sla.tzinfo is None:
        now = now.replace(tzinfo=None)
    diff = (sla - now).total_seconds() / 3600
    assert 3 < diff < 5


@pytest.mark.asyncio
async def test_create_ticket_ticket_numbers_are_unique(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    r1 = await client.post(BASE, json={**TICKET_PAYLOAD, "customer_id": cid},
                           headers=auth_headers)
    r2 = await client.post(BASE, json={**TICKET_PAYLOAD, "customer_id": cid},
                           headers=auth_headers)
    assert r1.json()["ticket_number"] != r2.json()["ticket_number"]


@pytest.mark.asyncio
async def test_create_ticket_invalid_priority(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    r = await client.post(BASE,
                          json={**TICKET_PAYLOAD, "customer_id": cid, "priority": "super-critical"},
                          headers=auth_headers)
    assert r.status_code == 422


# ── List ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_tickets_empty_initially(client, auth_headers):
    r = await client.get(BASE, headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_tickets_returns_created(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    await client.post(BASE, json={**TICKET_PAYLOAD, "customer_id": cid}, headers=auth_headers)
    r = await client.get(BASE, headers=auth_headers)
    assert len(r.json()) == 1


# ── Get single ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_ticket_by_id(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    cr = await client.post(BASE, json={**TICKET_PAYLOAD, "customer_id": cid},
                           headers=auth_headers)
    tid = cr.json()["id"]
    r = await client.get(f"{BASE}/{tid}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["id"] == tid


@pytest.mark.asyncio
async def test_get_nonexistent_ticket_returns_404(client, auth_headers):
    r = await client.get(f"{BASE}/{uuid.uuid4()}", headers=auth_headers)
    assert r.status_code == 404


# ── Update / status transitions ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_resolve_ticket_sets_resolved_at(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    cr = await client.post(BASE, json={**TICKET_PAYLOAD, "customer_id": cid},
                           headers=auth_headers)
    tid = cr.json()["id"]
    r = await client.patch(f"{BASE}/{tid}", json={"status": "resolved"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["resolved_at"] is not None


@pytest.mark.asyncio
async def test_close_ticket_sets_closed_at(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    cr = await client.post(BASE, json={**TICKET_PAYLOAD, "customer_id": cid},
                           headers=auth_headers)
    tid = cr.json()["id"]
    r = await client.patch(f"{BASE}/{tid}", json={"status": "closed"}, headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "closed"
    # Regression (BUG-3): closure timestamp must be exposed by the API.
    assert body["closed_at"] is not None


@pytest.mark.asyncio
async def test_update_ticket_resolution_notes(client, auth_headers):
    """ServiceTicketUpdate allows status/priority/assigned_to/resolution_notes
    (complaint is immutable after creation)."""
    cid = await _make_customer(client, auth_headers)
    cr = await client.post(BASE, json={**TICKET_PAYLOAD, "customer_id": cid},
                           headers=auth_headers)
    tid = cr.json()["id"]
    r = await client.patch(f"{BASE}/{tid}",
                           json={"resolution_notes": "Replaced faulty cable"},
                           headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["resolution_notes"] == "Replaced faulty cable"


# ── Comments ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_comment_to_ticket(client, auth_headers, admin_user):
    cid = await _make_customer(client, auth_headers)
    cr = await client.post(BASE, json={**TICKET_PAYLOAD, "customer_id": cid},
                           headers=auth_headers)
    tid = cr.json()["id"]
    r = await client.post(f"{BASE}/{tid}/comments",
                          json={"body": "Technician has been dispatched."},
                          headers=auth_headers)
    assert r.status_code == 201
    assert r.json()["body"] == "Technician has been dispatched."


@pytest.mark.asyncio
async def test_list_comments_for_ticket(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    cr = await client.post(BASE, json={**TICKET_PAYLOAD, "customer_id": cid},
                           headers=auth_headers)
    tid = cr.json()["id"]
    await client.post(f"{BASE}/{tid}/comments", json={"body": "Comment 1"},
                      headers=auth_headers)
    await client.post(f"{BASE}/{tid}/comments", json={"body": "Comment 2"},
                      headers=auth_headers)
    r = await client.get(f"{BASE}/{tid}/comments", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 2


@pytest.mark.asyncio
async def test_add_comment_to_nonexistent_ticket(client, auth_headers):
    r = await client.post(f"{BASE}/{uuid.uuid4()}/comments",
                          json={"body": "Orphan comment"},
                          headers=auth_headers)
    assert r.status_code == 404
