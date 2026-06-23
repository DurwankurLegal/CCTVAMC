"""Step 7 — business events create notification log rows automatically."""
import pytest
from httpx import AsyncClient


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


async def _events_in_logs(client, token):
    logs = await client.get("/api/v1/notifications/logs", headers=_auth(token))
    assert logs.status_code == 200
    return {row["event_type"] for row in logs.json()}


@pytest.mark.asyncio
async def test_quote_approval_emits_notification(client: AsyncClient, admin_token: str):
    cust = await client.post("/api/v1/customers", json={"name": "Notif Cust", "category": "commercial"}, headers=_auth(admin_token))
    cid = cust.json()["id"]
    q = await client.post("/api/v1/quotations", headers=_auth(admin_token),
                          json={"customer_id": cid, "line_items": [
                              {"description": "Cam", "quantity": 1, "unit_price": 1000, "gst_rate": 18, "amount": 1000}]})
    qid = q.json()["id"]
    await client.post(f"/api/v1/quotations/{qid}/approve", headers=_auth(admin_token))
    assert "quote_approved" in await _events_in_logs(client, admin_token)


@pytest.mark.asyncio
async def test_low_stock_emits_notification(client: AsyncClient, admin_token: str):
    item = await client.post("/api/v1/inventory", headers=_auth(admin_token),
                             json={"name": "Connector", "reorder_level": 5})
    iid = item.json()["id"]
    # Stock in 10, then consume 8 -> 2, below reorder level 5.
    await client.post("/api/v1/inventory/adjust", headers=_auth(admin_token),
                      json={"item_id": iid, "quantity": 10, "movement_type": "purchase"})
    await client.post("/api/v1/inventory/adjust", headers=_auth(admin_token),
                      json={"item_id": iid, "quantity": -8, "movement_type": "consumption"})
    assert "low_stock" in await _events_in_logs(client, admin_token)


@pytest.mark.asyncio
async def test_purchase_order_emits_notification(client: AsyncClient, admin_token: str):
    v = await client.post("/api/v1/vendors", json={"name": "Notif Vendor"}, headers=_auth(admin_token))
    vid = v.json()["id"]
    await client.post("/api/v1/vendors/purchase-orders", headers=_auth(admin_token),
                      json={"vendor_id": vid, "line_items": [{"qty": 2, "unit_cost": 500}]})
    assert "purchase_order_created" in await _events_in_logs(client, admin_token)
