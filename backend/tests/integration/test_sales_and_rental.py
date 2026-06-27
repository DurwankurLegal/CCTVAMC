import pytest
from httpx import AsyncClient
from datetime import date


async def _make_customer(client, token) -> str:
    r = await client.post(
        "/api/v1/customers",
        json={"name": "Sales Rental Cust", "category": "commercial",
              "gstin": "27AABCU9603R1ZX", "state_code": "27"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return r.json()["id"]


async def _make_company(client, token) -> str:
    r = await client.post(
        "/api/v1/companies",
        json={"name": "Test Leasing Corp", "gstin": "27AABCU9603R1ZX", "state_code": "27", "is_default": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    return r.json()["id"]


@pytest.mark.asyncio
async def test_products_crud(client: AsyncClient, admin_token: str):
    # 1. Create a product catalog entry
    p_resp = await client.post(
        "/api/v1/products",
        json={
            "sku": "CCTV-CAM-1080P",
            "name": "Dome Camera 1080P HD",
            "brand": "Hikvision",
            "model": "DS-2CE56D0T-IRPF",
            "category": "camera",
            "hsn_code": "85258900",
            "gst_rate": 18.0,
            "sale_price": 2500.0,
            "rental_price": 250.0,
            "is_serial_tracked": True,
            "is_sellable": True,
            "is_rentable": True
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert p_resp.status_code == 201
    prod = p_resp.json()
    assert prod["sku"] == "CCTV-CAM-1080P"
    assert prod["is_serial_tracked"] is True

    # 2. Get the product catalog list
    list_resp = await client.get(
        "/api/v1/products",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1


@pytest.mark.asyncio
async def test_sales_order_lifecycle(client: AsyncClient, admin_token: str):
    cid = await _make_customer(client, admin_token)

    # 1. Create a product
    p_resp = await client.post(
        "/api/v1/products",
        json={
            "sku": "CCTV-CAM-4K",
            "name": "Bullet Camera 4K UHD",
            "brand": "Dahua",
            "model": "DH-HAC-HFW1801RP",
            "category": "camera",
            "gst_rate": 18.0,
            "sale_price": 5000.0,
            "is_serial_tracked": True,
            "is_sellable": True,
            "is_rentable": False
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    prod = p_resp.json()

    # 2. Create a Sales Order in DRAFT status
    so_resp = await client.post(
        "/api/v1/sales-orders",
        json={
            "customer_id": cid,
            "order_date": str(date.today()),
            "supply_state_code": "27",
            "line_items": [
                {
                    "product_id": prod["id"],
                    "quantity": 1,
                    "unit_price": 5000.0
                }
            ],
            "notes": "Test Order"
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert so_resp.status_code == 201
    so = so_resp.json()
    assert so["status"] == "draft"
    # Either CGST/SGST or IGST should be non-zero depending on test tenant's resolved origin state
    assert (so["cgst_amount"] > 0 or so["igst_amount"] > 0)
    assert so["total_amount"] > 5000.0

    # 3. Confirm the Sales Order
    conf_resp = await client.post(
        f"/api/v1/sales-orders/{so['id']}/confirm",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert conf_resp.status_code == 200
    assert conf_resp.json()["status"] == "confirmed"

    # 4. Fulfil the Sales Order with Serial Numbers
    # Since the product is serial-tracked, we must supply serials matching quantity
    fulfil_err = await client.post(
        f"/api/v1/sales-orders/{so['id']}/fulfil",
        json={"line_items": [{"product_id": prod["id"], "quantity": 1, "serials": []}]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # Check that it returns HTTP 400 because serial number was missing for serial tracked product
    assert fulfil_err.status_code == 400

    fulfil_ok = await client.post(
        f"/api/v1/sales-orders/{so['id']}/fulfil",
        json={"line_items": [{"product_id": prod["id"], "quantity": 1, "serials": ["SN-BULLET-4K-999"]}]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert fulfil_ok.status_code == 200
    so_final = fulfil_ok.json()
    assert so_final["status"] == "fulfilled"
    assert so_final["fulfilled_at"] is not None

    # 5. Generate Tax Invoice from Sales Order
    inv_resp = await client.post(
        f"/api/v1/sales-orders/{so['id']}/invoice",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert inv_resp.status_code == 200
    assert inv_resp.json()["invoice_number"] != ""


@pytest.mark.asyncio
async def test_rentals_and_recurring_billing(client: AsyncClient, admin_token: str):
    cid = await _make_customer(client, admin_token)
    comp_id = await _make_company(client, admin_token)

    # 1. Create rentable product
    p_resp = await client.post(
        "/api/v1/products",
        json={
            "sku": "CCTV-RENT-1",
            "name": "Rental Camera Unit",
            "gst_rate": 18.0,
            "rental_price": 500.0,
            "is_serial_tracked": False,
            "is_sellable": False,
            "is_rentable": True
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    prod = p_resp.json()

    # 2. Create physical rental unit
    unit_resp = await client.post(
        "/api/v1/rentals/units",
        json={
            "product_id": prod["id"],
            "serial_number": "RENT-SN-001",
            "condition": "new",
            "status": "available"
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert unit_resp.status_code == 201
    unit = unit_resp.json()

    # 3. Create Rental Contract
    rc_resp = await client.post(
        "/api/v1/rentals/contracts",
        json={
            "customer_id": cid,
            "company_id": comp_id,
            "start_date": str(date.today()),
            "end_date": str(date.today()),
            "deposit_amount": 1000.0,
            "lines": [
                {
                    "product_id": prod["id"],
                    "quantity": 1,
                    "unit_price": 500.0,
                    "gst_rate": 18.0
                }
            ]
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert rc_resp.status_code == 201
    contract = rc_resp.json()

    # 4. Check out the equipment
    co_resp = await client.post(
        f"/api/v1/rentals/contracts/{contract['id']}/checkout",
        json={
            "rental_unit_id": unit["id"],
            "condition": "new",
            "notes": "Deploying rental unit"
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert co_resp.status_code == 200

    # 5. Activate Contract
    act_resp = await client.post(
        f"/api/v1/rentals/contracts/{contract['id']}/activate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert act_resp.status_code == 200
    assert act_resp.json()["status"] == "active"

    # 6. Check-in the unit back
    ci_resp = await client.post(
        f"/api/v1/rentals/contracts/{contract['id']}/checkin",
        json={
            "rental_unit_id": unit["id"],
            "condition": "good",
            "notes": "Unit returned"
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert ci_resp.status_code == 200

    # 7. Run Monthly Recurring Billing Trigger
    billing_resp = await client.post(
        "/api/v1/rentals/contracts/generate-billing",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert billing_resp.status_code == 200
    assert "invoices_generated" in billing_resp.json()
