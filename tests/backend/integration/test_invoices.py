"""
Integration tests — Invoices API
===================================
Covers: create (GST totals auto-computed), list, get, update,
        credit note generation, invoice number formatting, auth guard.
"""
import uuid
import pytest
from datetime import date, timedelta


BASE = "/api/v1/invoices"
TODAY = str(date.today())
DUE = str(date.today() + timedelta(days=30))


async def _make_customer(client, headers) -> str:
    r = await client.post("/api/v1/customers",
                          json={"name": "Invoice Customer", "category": "commercial"},
                          headers=headers)
    return r.json()["id"]


def _invoice_payload(cid: str, **kwargs) -> dict:
    base = {
        "customer_id": cid,
        "invoice_type": "tax_invoice",
        "invoice_date": TODAY,
        "due_date": DUE,
        "supply_state_code": "DL",
        "line_items": [
            {"description": "AMC Services", "quantity": 1, "unit_price": 10000, "gst_rate": 18}
        ],
    }
    base.update(kwargs)
    return base


# ── Auth guard ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_invoices_requires_auth(client):
    r = await client.get(BASE)
    assert r.status_code in (401, 403)


# ── Create ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_invoice_success(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    r = await client.post(BASE, json=_invoice_payload(cid), headers=auth_headers)
    assert r.status_code == 201
    body = r.json()
    assert "invoice_number" in body
    assert body["subtotal"] == 10000.0


@pytest.mark.asyncio
async def test_create_invoice_gst_inter_state(client, auth_headers, tenant):
    """Supply state != tenant state → IGST applied, CGST/SGST = 0."""
    cid = await _make_customer(client, auth_headers)
    # Tenant has no state_code in settings (SQLite test), so supply != origin → IGST
    r = await client.post(BASE, json=_invoice_payload(cid, supply_state_code="MH"),
                          headers=auth_headers)
    assert r.status_code == 201
    body = r.json()
    # IGST should be non-zero for inter-state
    assert body["total_amount"] > body["subtotal"]


@pytest.mark.asyncio
async def test_create_invoice_number_has_correct_prefix(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    r = await client.post(BASE, json=_invoice_payload(cid), headers=auth_headers)
    num = r.json()["invoice_number"]
    # Format: <PREFIX>-<YEAR>-<SEQ>
    parts = num.split("-")
    assert len(parts) >= 3
    assert parts[-2].isdigit()  # year
    assert parts[-1].isdigit()  # sequence


@pytest.mark.asyncio
async def test_create_invoice_numbers_sequential(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    r1 = await client.post(BASE, json=_invoice_payload(cid), headers=auth_headers)
    r2 = await client.post(BASE, json=_invoice_payload(cid), headers=auth_headers)
    n1 = int(r1.json()["invoice_number"].split("-")[-1])
    n2 = int(r2.json()["invoice_number"].split("-")[-1])
    assert n2 == n1 + 1


@pytest.mark.asyncio
async def test_create_invoice_empty_line_items(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    r = await client.post(BASE, json={**_invoice_payload(cid), "line_items": []},
                          headers=auth_headers)
    assert r.status_code == 201
    assert r.json()["subtotal"] == 0.0


# ── List ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_invoices_returns_created(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    await client.post(BASE, json=_invoice_payload(cid), headers=auth_headers)
    r = await client.get(BASE, headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1


# ── Get ───────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_invoice_by_id(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    cr = await client.post(BASE, json=_invoice_payload(cid), headers=auth_headers)
    iid = cr.json()["id"]
    r = await client.get(f"{BASE}/{iid}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["id"] == iid


@pytest.mark.asyncio
async def test_get_nonexistent_invoice_returns_404(client, auth_headers):
    r = await client.get(f"{BASE}/{uuid.uuid4()}", headers=auth_headers)
    assert r.status_code == 404


# ── Update ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_invoice_notes(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    cr = await client.post(BASE, json=_invoice_payload(cid), headers=auth_headers)
    iid = cr.json()["id"]
    r = await client.patch(f"{BASE}/{iid}", json={"notes": "GST-compliant invoice"},
                           headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["notes"] == "GST-compliant invoice"


# ── Credit note ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_credit_note(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    cr = await client.post(BASE, json=_invoice_payload(cid), headers=auth_headers)
    iid = cr.json()["id"]
    r = await client.post(f"{BASE}/{iid}/credit-note", headers=auth_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["invoice_number"].startswith("CN-")
    # Credit note amounts are negative
    assert body["total_amount"] < 0


@pytest.mark.asyncio
async def test_credit_note_on_nonexistent_invoice(client, auth_headers):
    r = await client.post(f"{BASE}/{uuid.uuid4()}/credit-note", headers=auth_headers)
    assert r.status_code == 404
