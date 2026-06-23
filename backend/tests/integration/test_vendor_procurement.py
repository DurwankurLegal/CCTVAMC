"""Vendor PO + payables (SRS 4.4) and ticket comments (SRS 4.8)."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_purchase_order_and_vendor_payment(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    vend = await client.post("/api/v1/vendors", json={"name": "CamSupplier", "vendor_type": "supplier"}, headers=headers)
    assert vend.status_code == 201
    vid = vend.json()["id"]

    po = await client.post("/api/v1/vendors/purchase-orders",
                           json={"vendor_id": vid, "line_items": [{"qty": 5, "unit_cost": 1000}]},
                           headers=headers)
    assert po.status_code == 201
    assert po.json()["total_amount"] == 5000
    assert po.json()["po_number"].startswith("PO-")

    # vendor payable increased
    v = await client.get(f"/api/v1/vendors/{vid}", headers=headers)
    assert float(v.json()["outstanding_payable"]) == 5000

    # record a payment -> payable decreases
    pay = await client.post("/api/v1/vendors/payments",
                            json={"vendor_id": vid, "amount": 2000, "method": "bank"}, headers=headers)
    assert pay.status_code == 201
    v2 = await client.get(f"/api/v1/vendors/{vid}", headers=headers)
    assert float(v2.json()["outstanding_payable"]) == 3000

    pos = await client.get("/api/v1/vendors/purchase-orders", headers=headers)
    assert len(pos.json()) == 1


@pytest.mark.asyncio
async def test_ticket_comments(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    cust = await client.post("/api/v1/customers", json={"name": "TC Co", "category": "commercial"}, headers=headers)
    tk = await client.post("/api/v1/service-tickets",
                           json={"customer_id": cust.json()["id"], "complaint": "x", "priority": "low"},
                           headers=headers)
    tid = tk.json()["id"]
    c = await client.post(f"/api/v1/service-tickets/{tid}/comments", json={"body": "investigating"}, headers=headers)
    assert c.status_code == 201
    listed = await client.get(f"/api/v1/service-tickets/{tid}/comments", headers=headers)
    assert len(listed.json()) == 1 and listed.json()[0]["body"] == "investigating"
