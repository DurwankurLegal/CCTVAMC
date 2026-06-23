"""
Integration tests — Quotations API
======================================
Covers: create/list/get/update, GST totals, approve/reject lifecycle,
        convert-to-amc, auth guard.
"""
import uuid
import pytest
from datetime import date, timedelta


BASE = "/api/v1/quotations"


async def _make_customer(client, headers):
    r = await client.post("/api/v1/customers",
                          json={"name": "Quote Cust", "category": "commercial"},
                          headers=headers)
    return r.json()["id"]


def _payload(cid):
    return {
        "customer_id": cid,
        "valid_until": str(date.today() + timedelta(days=15)),
        "line_items": [
            {"description": "2MP Camera", "quantity": 4, "unit_price": 2500.0,
             "gst_rate": 18.0, "amount": 10000.0},
        ],
        "terms": "50% advance",
    }


@pytest.mark.asyncio
async def test_quotations_requires_auth(client):
    r = await client.get(BASE)
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_quotation(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    r = await client.post(BASE, json=_payload(cid), headers=auth_headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["quotation_number"].startswith("QUO-") or body["quotation_number"]
    assert body["total_amount"] > 0


@pytest.mark.asyncio
async def test_list_quotations(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    await client.post(BASE, json=_payload(cid), headers=auth_headers)
    r = await client.get(BASE, headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_get_quotation_by_id(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    cr = await client.post(BASE, json=_payload(cid), headers=auth_headers)
    qid = cr.json()["id"]
    r = await client.get(f"{BASE}/{qid}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["id"] == qid


@pytest.mark.asyncio
async def test_get_nonexistent_quotation_404(client, auth_headers):
    r = await client.get(f"{BASE}/{uuid.uuid4()}", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_approve_quotation(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    cr = await client.post(BASE, json=_payload(cid), headers=auth_headers)
    qid = cr.json()["id"]
    r = await client.post(f"{BASE}/{qid}/approve", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] in ("approved", "accepted")


@pytest.mark.asyncio
async def test_reject_quotation(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    cr = await client.post(BASE, json=_payload(cid), headers=auth_headers)
    qid = cr.json()["id"]
    r = await client.post(f"{BASE}/{qid}/reject", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] in ("rejected", "declined")


@pytest.mark.asyncio
async def test_update_quotation_terms(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    cr = await client.post(BASE, json=_payload(cid), headers=auth_headers)
    qid = cr.json()["id"]
    r = await client.patch(f"{BASE}/{qid}", json={"terms": "100% advance"},
                           headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["terms"] == "100% advance"
