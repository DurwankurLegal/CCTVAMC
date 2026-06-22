"""Assigning a ticket produces an in-app notification the assignee can read."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ticket_assignment_creates_in_app_notification(client: AsyncClient, admin_token, admin_user):
    headers = {"Authorization": f"Bearer {admin_token}"}

    customer = await client.post(
        "/api/v1/customers", json={"name": "Notif Co", "category": "commercial"}, headers=headers,
    )
    customer_id = customer.json()["id"]

    ticket = await client.post(
        "/api/v1/service-tickets",
        json={"customer_id": customer_id, "complaint": "Camera down", "priority": "high"},
        headers=headers,
    )
    assert ticket.status_code == 201
    ticket_id = ticket.json()["id"]

    # Assign to the admin user → triggers TICKET_ASSIGNED in-app notification.
    upd = await client.patch(
        f"/api/v1/service-tickets/{ticket_id}",
        json={"assigned_to": str(admin_user.id), "status": "assigned"},
        headers=headers,
    )
    assert upd.status_code == 200

    inbox = await client.get("/api/v1/notifications?unread_only=true", headers=headers)
    assert inbox.status_code == 200
    items = inbox.json()
    assert len(items) >= 1
    notif_id = items[0]["id"]

    read = await client.post(f"/api/v1/notifications/{notif_id}/read", headers=headers)
    assert read.status_code == 200
