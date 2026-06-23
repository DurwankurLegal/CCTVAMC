"""
Integration tests — Notifications API
=========================================
Covers: template CRUD, logs, in-app notification center, mark-read, auth guard.
"""
import uuid
import pytest


BASE = "/api/v1/notifications"

TEMPLATE_PAYLOAD = {
    "event_type": "ticket_created",
    "channel": "in_app",
    "subject": "New ticket",
    "body": "Ticket {{ticket_number}} created",
}


@pytest.mark.asyncio
async def test_notifications_requires_auth(client):
    r = await client.get(BASE)
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_template(client, auth_headers):
    r = await client.post(f"{BASE}/templates", json=TEMPLATE_PAYLOAD, headers=auth_headers)
    assert r.status_code == 201, r.text
    assert r.json()["event_type"] == "ticket_created"


@pytest.mark.asyncio
async def test_list_templates(client, auth_headers):
    await client.post(f"{BASE}/templates", json=TEMPLATE_PAYLOAD, headers=auth_headers)
    r = await client.get(f"{BASE}/templates", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_list_logs_empty(client, auth_headers):
    r = await client.get(f"{BASE}/logs", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_my_notifications_empty(client, auth_headers):
    r = await client.get(BASE, headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_mark_nonexistent_notification_read_404(client, auth_headers):
    r = await client.post(f"{BASE}/{uuid.uuid4()}/read", headers=auth_headers)
    assert r.status_code == 404
