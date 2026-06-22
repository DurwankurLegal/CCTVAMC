import pytest
from uuid import uuid4
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_ticket_sets_sla(client: AsyncClient, admin_token: str):
    # First create a customer
    cust_resp = await client.post(
        "/api/v1/customers",
        json={"name": "Test Society", "category": "chs"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    customer_id = cust_resp.json()["id"]

    resp = await client.post(
        "/api/v1/service-tickets",
        json={
            "customer_id": customer_id,
            "priority": "high",
            "complaint": "DVR not recording",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "open"
    assert data["sla_due_at"] is not None
    assert data["sla_breached"] is False
    assert data["ticket_number"].startswith("TKT-")


@pytest.mark.asyncio
async def test_update_ticket_status(client: AsyncClient, admin_token: str):
    cust_resp = await client.post(
        "/api/v1/customers",
        json={"name": "Test Shop", "category": "single_shop"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    customer_id = cust_resp.json()["id"]

    ticket_resp = await client.post(
        "/api/v1/service-tickets",
        json={"customer_id": customer_id, "priority": "medium", "complaint": "Camera offline"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    ticket_id = ticket_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/service-tickets/{ticket_id}",
        json={"status": "resolved", "resolution_notes": "Replaced power adapter"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "resolved"
    assert data["resolved_at"] is not None
