"""
Integration tests — Reports API
==================================
Covers: dashboard KPIs, lead conversion report, revenue by customer,
        technician productivity, inventory consumption, amc renewal pipeline,
        overdue receivables, payment collection, ticket SLA report.
"""
import pytest
from datetime import date, timedelta


BASE = "/api/v1/reports"
TODAY = str(date.today())
LAST_MONTH = str(date.today() - timedelta(days=30))


async def _make_customer(client, headers) -> str:
    r = await client.post("/api/v1/customers",
                          json={"name": "Report Customer", "category": "commercial"},
                          headers=headers)
    return r.json()["id"]


# ── Auth guard ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_kpis_requires_auth(client):
    r = await client.get(f"{BASE}/dashboard")
    assert r.status_code in (401, 403)


# ── Dashboard KPIs ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_kpis_structure(client, auth_headers):
    r = await client.get(f"{BASE}/dashboard", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    required_keys = {
        "open_tickets", "sla_breached_tickets", "active_amc_contracts",
        "revenue_mtd", "outstanding_receivables", "lead_pipeline",
    }
    assert required_keys.issubset(body.keys())


@pytest.mark.asyncio
async def test_dashboard_kpis_zero_values_on_empty_db(client, auth_headers):
    r = await client.get(f"{BASE}/dashboard", headers=auth_headers)
    body = r.json()
    assert body["open_tickets"] == 0
    assert body["revenue_mtd"] == 0.0
    assert body["active_amc_contracts"] == 0


@pytest.mark.asyncio
async def test_dashboard_kpis_open_tickets_increments(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    await client.post("/api/v1/service-tickets", json={
        "customer_id": cid, "complaint": "Camera down", "priority": "high", "status": "open",
    }, headers=auth_headers)
    r = await client.get(f"{BASE}/dashboard", headers=auth_headers)
    assert r.json()["open_tickets"] == 1


# ── Lead conversion ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_lead_conversion_report_structure(client, auth_headers):
    r = await client.get(f"{BASE}/lead-conversion", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert "total_leads" in body
    assert "converted" in body
    assert "conversion_pct" in body


@pytest.mark.asyncio
async def test_lead_conversion_zero_on_empty(client, auth_headers):
    r = await client.get(f"{BASE}/lead-conversion", headers=auth_headers)
    body = r.json()
    assert body["total_leads"] == 0
    assert body["conversion_pct"] == 0.0


@pytest.mark.asyncio
async def test_lead_conversion_pct_calculated_correctly(client, auth_headers):
    """Create 2 leads, convert 1 → 50% conversion."""
    for i in range(2):
        await client.post("/api/v1/leads", json={
            "name": f"Lead {i}", "phone": f"900000{i:04d}", "category": "commercial",
        }, headers=auth_headers)
    leads_r = await client.get("/api/v1/leads", headers=auth_headers)
    first_id = leads_r.json()[0]["id"]
    await client.post(f"/api/v1/leads/{first_id}/convert", headers=auth_headers)
    r = await client.get(f"{BASE}/lead-conversion", headers=auth_headers)
    assert r.json()["conversion_pct"] == 50.0


# ── Revenue by customer ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_revenue_by_customer_empty(client, auth_headers):
    r = await client.get(f"{BASE}/revenue-by-customer", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_revenue_by_customer_returns_entry(client, auth_headers):
    cid = await _make_customer(client, auth_headers)
    await client.post("/api/v1/invoices", json={
        "customer_id": cid, "invoice_type": "tax_invoice",
        "invoice_date": TODAY, "due_date": TODAY,
        "supply_state_code": "MH",
        "line_items": [{"description": "Svc", "amount": 5000, "gst_rate": 0}],
    }, headers=auth_headers)
    r = await client.get(f"{BASE}/revenue-by-customer", headers=auth_headers)
    entries = [e for e in r.json() if e["customer_id"] == cid]
    assert len(entries) == 1
    assert entries[0]["revenue"] == 5000.0


# ── SLA ticket report ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ticket_sla_report_structure(client, auth_headers):
    r = await client.get(
        f"{BASE}/sla?from_date={LAST_MONTH}&to_date={TODAY}",
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert "total_tickets" in body
    assert "sla_met" in body
    assert "sla_breached" in body
    assert "compliance_pct" in body


@pytest.mark.asyncio
async def test_ticket_sla_100_compliance_no_tickets(client, auth_headers):
    r = await client.get(
        f"{BASE}/sla?from_date={LAST_MONTH}&to_date={TODAY}",
        headers=auth_headers,
    )
    assert r.json()["compliance_pct"] == 100.0


@pytest.mark.asyncio
async def test_ticket_sla_counts_same_day_ticket(client, auth_headers):
    """Regression (BUG-2): a ticket created *today* must be counted when the
    range ends today. The old `created_at <= to_date` (midnight) dropped it."""
    cid = await _make_customer(client, auth_headers)
    tr = await client.post("/api/v1/service-tickets",
                           json={"customer_id": cid, "complaint": "Down", "priority": "high"},
                           headers=auth_headers)
    assert tr.status_code == 201, tr.text
    r = await client.get(
        f"{BASE}/sla?from_date={TODAY}&to_date={TODAY}",
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["total_tickets"] >= 1


# ── Inventory consumption ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_inventory_consumption_report_empty(client, auth_headers):
    r = await client.get(f"{BASE}/inventory-consumption", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


# ── AMC renewal pipeline ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_amc_renewal_pipeline_empty(client, auth_headers):
    r = await client.get(f"{BASE}/amc-renewal-pipeline", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ── Payment collection ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_payment_collection_report_empty(client, auth_headers):
    r = await client.get(f"{BASE}/payment-collection", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
