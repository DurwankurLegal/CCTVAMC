"""
Integration tests — Operating Companies & Templates API
======================================================
Covers: create company, list companies, update company,
        default company toggles (exclusivity), soft-delete,
        and company template upserts and lists.
"""
import uuid
import pytest

BASE_COMPANIES = "/api/v1/companies"
BASE_TEMPLATES = "/api/v1/company-templates"

COMPANY_PAYLOAD = {
    "name": "Acme Systems GST",
    "gst_status": "GST",
    "gstin": "27ABCDE1234F1Z5",
    "address": "123 Business Park, Mumbai",
    "contact_details": {"phone": "9999999999", "email": "info@acme.com"},
    "bank_details": {"bank_name": "State Bank of India", "account_number": "1234567890"},
    "authorized_signatory": {"name": "John Doe", "designation": "Director"},
    "is_default": False,
    "is_active": True,
}

@pytest.mark.asyncio
async def test_create_company_requires_auth(client):
    r = await client.post(BASE_COMPANIES, json=COMPANY_PAYLOAD)
    assert r.status_code in (401, 403)

@pytest.mark.asyncio
async def test_create_company_success(client, auth_headers):
    # First company should automatically default to True
    r = await client.post(BASE_COMPANIES, json=COMPANY_PAYLOAD, headers=auth_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Acme Systems GST"
    assert body["is_default"] is True  # Auto-promoted to default
    assert "id" in body

@pytest.mark.asyncio
async def test_list_companies(client, auth_headers):
    await client.post(BASE_COMPANIES, json=COMPANY_PAYLOAD, headers=auth_headers)
    r = await client.get(BASE_COMPANIES, headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1

@pytest.mark.asyncio
async def test_single_default_company_exclusivity(client, auth_headers):
    # Create first company (automatically becomes default)
    r1 = await client.post(BASE_COMPANIES, json=COMPANY_PAYLOAD, headers=auth_headers)
    c1_id = r1.json()["id"]

    # Create second company and set is_default = True
    payload2 = {**COMPANY_PAYLOAD, "name": "Acme Non-GST", "gst_status": "NON_GST", "is_default": True}
    r2 = await client.post(BASE_COMPANIES, json=payload2, headers=auth_headers)
    c2_id = r2.json()["id"]
    assert r2.json()["is_default"] is True

    # Re-fetch first company and check it is no longer default
    r1_check = await client.get(f"{BASE_COMPANIES}/{c1_id}", headers=auth_headers)
    assert r1_check.json()["is_default"] is False

@pytest.mark.asyncio
async def test_update_company(client, auth_headers):
    r = await client.post(BASE_COMPANIES, json=COMPANY_PAYLOAD, headers=auth_headers)
    cid = r.json()["id"]

    r_upd = await client.put(f"{BASE_COMPANIES}/{cid}", json={"name": "Acme Systems Revised"}, headers=auth_headers)
    assert r_upd.status_code == 200
    assert r_upd.json()["name"] == "Acme Systems Revised"

@pytest.mark.asyncio
async def test_delete_company_is_soft_delete(client, auth_headers):
    r = await client.post(BASE_COMPANIES, json=COMPANY_PAYLOAD, headers=auth_headers)
    cid = r.json()["id"]

    r_del = await client.delete(f"{BASE_COMPANIES}/{cid}", headers=auth_headers)
    assert r_del.status_code == 200
    assert r_del.json()["is_active"] is False

# ── Templates ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upsert_company_template(client, auth_headers):
    # Create company
    r_comp = await client.post(BASE_COMPANIES, json=COMPANY_PAYLOAD, headers=auth_headers)
    cid = r_comp.json()["id"]

    template_payload = {
        "company_id": cid,
        "document_type": "invoice",
        "template_html": "<html><body>Invoice {{ invoice_number }}</body></html>",
        "header_html": "Header",
        "footer_html": "Footer",
        "is_active": True,
    }

    # Upsert template (insert)
    r_tmpl = await client.post(BASE_TEMPLATES, json=template_payload, headers=auth_headers)
    assert r_tmpl.status_code == 200
    body = r_tmpl.json()
    assert body["document_type"] == "invoice"
    assert "id" in body
    tmpl_id = body["id"]

    # List templates for company
    r_list = await client.get(f"{BASE_TEMPLATES}?company_id={cid}", headers=auth_headers)
    assert r_list.status_code == 200
    assert len(r_list.json()) == 1

    # Upsert same type to check update logic
    template_payload["template_html"] = "<html><body>Updated Invoice</body></html>"
    r_upd = await client.post(BASE_TEMPLATES, json=template_payload, headers=auth_headers)
    assert r_upd.status_code == 200
    assert r_upd.json()["id"] == tmpl_id
    assert r_upd.json()["template_html"] == "<html><body>Updated Invoice</body></html>"
