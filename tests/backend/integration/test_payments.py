"""
Integration tests — Payments API
====================================
Covers: record payment, list, update (amount delta adjusts invoice),
        invoice status transitions (partial → paid), ageing buckets, auth guard.

Notes on the real API contract (verified against app/api/v1/payments.py):
  * POST /payments requires BOTH invoice_id and customer_id (PaymentCreate).
  * There is no GET /payments/{id}; single payments are read via the list
    endpoint or the /{id}/receipt PDF route.
"""
import uuid
import pytest
from datetime import date, timedelta


BASE_PAY = "/api/v1/payments"
BASE_INV = "/api/v1/invoices"
TODAY = str(date.today())


async def _setup_invoice(client, headers, amount=5000.0) -> tuple[str, str]:
    """Create a customer + invoice. Returns (customer_id, invoice_id)."""
    cr = await client.post("/api/v1/customers",
                           json={"name": "Pay Customer", "category": "commercial"},
                           headers=headers)
    assert cr.status_code == 201, cr.text
    cid = cr.json()["id"]
    ir = await client.post(BASE_INV, json={
        "customer_id": cid,
        "invoice_type": "tax_invoice",
        "invoice_date": TODAY,
        "due_date": str(date.today() + timedelta(days=30)),
        "supply_state_code": "27",
        "line_items": [{"description": "Svc", "amount": amount, "gst_rate": 0}],
    }, headers=headers)
    assert ir.status_code == 201, ir.text
    return cid, ir.json()["id"]


def _pay_body(cid, iid, amount, mode="cash"):
    return {
        "invoice_id": iid,
        "customer_id": cid,
        "amount": amount,
        "mode": mode,
        "payment_date": TODAY,
    }


# ── Auth guard ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_payments_requires_auth(client):
    r = await client.get(BASE_PAY)
    assert r.status_code in (401, 403)


# ── Record payment ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_record_partial_payment_sets_partially_paid(client, auth_headers):
    cid, iid = await _setup_invoice(client, auth_headers, amount=5000.0)
    r = await client.post(BASE_PAY, json=_pay_body(cid, iid, 2500.0, "neft"),
                          headers=auth_headers)
    assert r.status_code == 201, r.text
    inv_r = await client.get(f"{BASE_INV}/{iid}", headers=auth_headers)
    assert inv_r.json()["status"] == "partially_paid"
    assert inv_r.json()["amount_paid"] == 2500.0


@pytest.mark.asyncio
async def test_record_full_payment_sets_paid(client, auth_headers):
    cid, iid = await _setup_invoice(client, auth_headers, amount=5000.0)
    r = await client.post(BASE_PAY, json=_pay_body(cid, iid, 5000.0, "upi"),
                          headers=auth_headers)
    assert r.status_code == 201, r.text
    inv_r = await client.get(f"{BASE_INV}/{iid}", headers=auth_headers)
    assert inv_r.json()["status"] == "paid"


@pytest.mark.asyncio
async def test_record_payment_on_nonexistent_invoice(client, auth_headers):
    r = await client.post(BASE_PAY, json=_pay_body(
        str(uuid.uuid4()), str(uuid.uuid4()), 100.0), headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_record_payment_missing_customer_id_is_422(client, auth_headers):
    """customer_id is required by PaymentCreate."""
    _, iid = await _setup_invoice(client, auth_headers)
    r = await client.post(BASE_PAY, json={
        "invoice_id": iid, "amount": 100.0, "mode": "cash", "payment_date": TODAY,
    }, headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_multiple_partial_payments_accumulate(client, auth_headers):
    cid, iid = await _setup_invoice(client, auth_headers, amount=3000.0)
    for _ in range(3):
        r = await client.post(BASE_PAY, json=_pay_body(cid, iid, 1000.0),
                              headers=auth_headers)
        assert r.status_code == 201, r.text
    inv_r = await client.get(f"{BASE_INV}/{iid}", headers=auth_headers)
    assert inv_r.json()["status"] == "paid"
    assert inv_r.json()["amount_paid"] == 3000.0


# ── List payments ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recorded_payment_appears_in_list(client, auth_headers):
    cid, iid = await _setup_invoice(client, auth_headers)
    pr = await client.post(BASE_PAY, json=_pay_body(cid, iid, 100.0),
                           headers=auth_headers)
    assert pr.status_code == 201, pr.text
    pid = pr.json()["id"]
    r = await client.get(BASE_PAY, headers=auth_headers)
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()]
    assert pid in ids


# ── Update payment ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_payment_amount_adjusts_invoice(client, auth_headers):
    """Increasing a payment amount must increase invoice.amount_paid by delta."""
    cid, iid = await _setup_invoice(client, auth_headers, amount=5000.0)
    pr = await client.post(BASE_PAY, json=_pay_body(cid, iid, 1000.0),
                           headers=auth_headers)
    pid = pr.json()["id"]
    r = await client.patch(f"{BASE_PAY}/{pid}", json={"amount": 2000.0},
                           headers=auth_headers)
    assert r.status_code == 200, r.text
    inv_r = await client.get(f"{BASE_INV}/{iid}", headers=auth_headers)
    assert inv_r.json()["amount_paid"] == 2000.0


@pytest.mark.asyncio
async def test_update_nonexistent_payment_returns_404(client, auth_headers):
    r = await client.patch(f"{BASE_PAY}/{uuid.uuid4()}", json={"amount": 5.0},
                           headers=auth_headers)
    assert r.status_code == 404


# ── Ageing ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_payment_ageing_returns_buckets(client, auth_headers):
    r = await client.get("/api/v1/payments/ageing", headers=auth_headers)
    assert r.status_code == 200
    buckets = {b["bucket"] for b in r.json()}
    assert {"current", "30d", "60d", "90d_plus"} == buckets
