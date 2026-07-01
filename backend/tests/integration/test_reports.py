"""Standard report set + CSV/Excel/PDF export tests (SRS 4.16).
Tests cover: standard report data, CSV/XLSX/PDF exports, quotation PDF,
AMC contract PDF, SLA XLSX, Service Consolidated XLSX, AMC Consolidated XLSX.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_standard_reports_and_export(client, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # seed a converted lead so conversion report is non-trivial
    lead = await client.post("/api/v1/leads", json={"name": "Rep Lead", "category": "commercial"}, headers=headers)
    await client.post(f"/api/v1/leads/{lead.json()['id']}/convert", headers=headers)

    conv = await client.get("/api/v1/reports/lead-conversion", headers=headers)
    assert conv.status_code == 200
    assert conv.json()["converted"] >= 1

    # revenue-by-customer report
    rev = await client.get("/api/v1/reports/revenue-by-customer", headers=headers)
    assert rev.status_code == 200 and isinstance(rev.json(), list)

    # CSV export
    csv = await client.get("/api/v1/reports/lead-conversion/export?fmt=csv", headers=headers)
    assert csv.status_code == 200
    assert "text/csv" in csv.headers["content-type"]
    assert b"conversion_pct" in csv.content

    # Excel export
    xlsx = await client.get("/api/v1/reports/lead-conversion/export?fmt=xlsx", headers=headers)
    assert xlsx.status_code == 200
    assert xlsx.content[:2] == b"PK"  # xlsx is a zip

    # unknown report
    assert (await client.get("/api/v1/reports/nope", headers=headers)).status_code == 404


@pytest.mark.asyncio
async def test_report_catalogue_and_new_reports(client, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}

    cat = await client.get("/api/v1/reports/catalogue", headers=headers)
    assert cat.status_code == 200
    keys = {r["key"] for r in cat.json()["reports"]}
    # New Step 5 reports must be discoverable
    for k in ("amc-renewal-pipeline", "overdue-receivables", "payment-collection",
              "installation-pipeline", "purchase-orders", "inventory-valuation"):
        assert k in keys, f"missing report {k}"
        resp = await client.get(f"/api/v1/reports/{k}", headers=headers)
        assert resp.status_code == 200 and isinstance(resp.json(), list)

    # A new report exports cleanly to xlsx
    xlsx = await client.get("/api/v1/reports/inventory-valuation/export?fmt=xlsx", headers=headers)
    assert xlsx.status_code == 200 and xlsx.content[:2] == b"PK"


# ── PDF / XLSX Download Tests ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_quotation_pdf_export(client, admin_token: str):
    """Quotation PDF endpoint returns application/pdf with content-disposition."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create a minimal quotation
    customer = await client.post(
        "/api/v1/customers",
        json={"name": "PDF Test Customer", "email": "pdf@test.com", "category": "commercial"},
        headers=headers,
    )
    assert customer.status_code == 201, customer.text
    cid = customer.json()["id"]

    quote = await client.post(
        "/api/v1/quotations",
        json={
            "customer_id": cid,
            "items": [{"description": "Camera", "quantity": 1, "unit_price": 5000.0}],
        },
        headers=headers,
    )
    assert quote.status_code == 201, quote.text
    qid = quote.json()["id"]

    pdf_resp = await client.get(f"/api/v1/quotations/{qid}/pdf", headers=headers)
    assert pdf_resp.status_code == 200
    assert "application/pdf" in pdf_resp.headers["content-type"]
    assert "content-disposition" in pdf_resp.headers
    assert "attachment" in pdf_resp.headers["content-disposition"]


@pytest.mark.asyncio
async def test_amc_contract_pdf_export(client, admin_token: str):
    """AMC contract PDF endpoint returns application/pdf."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    customer = await client.post(
        "/api/v1/customers",
        json={"name": "AMC PDF Customer", "email": "amcpdf@test.com", "category": "commercial"},
        headers=headers,
    )
    assert customer.status_code == 201, customer.text
    cid = customer.json()["id"]

    amc = await client.post(
        "/api/v1/amc",
        json={
            "customer_id": cid,
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "annual_amount": 60000.0,
            "preventive_visits_per_year": 4,
        },
        headers=headers,
    )
    assert amc.status_code == 201, amc.text
    amc_id = amc.json()["id"]

    pdf_resp = await client.get(f"/api/v1/amc/{amc_id}/pdf", headers=headers)
    assert pdf_resp.status_code == 200
    assert "application/pdf" in pdf_resp.headers["content-type"]
    assert "attachment" in pdf_resp.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_sla_report_export_xlsx(client, admin_token: str):
    """SLA report XLSX export returns a valid Excel file (PK header)."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    xlsx = await client.get(
        "/api/v1/reports/sla/export?from_date=2026-01-01&to_date=2026-12-31&fmt=xlsx",
        headers=headers,
    )
    assert xlsx.status_code == 200
    assert "spreadsheetml" in xlsx.headers["content-type"]
    assert xlsx.content[:2] == b"PK"  # XLSX is a ZIP archive


@pytest.mark.asyncio
async def test_service_consolidated_report_export_xlsx(client, admin_token: str):
    """Consolidated Service Report XLSX export returns a valid Excel file."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    xlsx = await client.get(
        "/api/v1/reports/service-consolidated/export?from_date=2026-01-01&to_date=2026-12-31&fmt=xlsx",
        headers=headers,
    )
    assert xlsx.status_code == 200
    assert "spreadsheetml" in xlsx.headers["content-type"]
    assert xlsx.content[:2] == b"PK"


@pytest.mark.asyncio
async def test_amc_consolidated_report_export_xlsx(client, admin_token: str):
    """AMC consolidated report XLSX export for any valid UUID returns 404 or valid XLSX."""
    import uuid as _uuid
    headers = {"Authorization": f"Bearer {admin_token}"}

    # A random UUID will produce a 404 (no contract found), which is the correct behaviour
    random_amc_id = str(_uuid.uuid4())
    resp = await client.get(
        f"/api/v1/reports/amc-consolidated/export?amc_id={random_amc_id}&from_date=2026-01-01&to_date=2026-12-31&fmt=xlsx",
        headers=headers,
    )
    # Either 404 (no such AMC) or 200 with XLSX are both acceptable
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        assert resp.content[:2] == b"PK"


@pytest.mark.asyncio
async def test_require_module_any_dependency(db: AsyncSession):
    """Directly test that require_module_any dependency checker works as expected."""
    from app.core.deps import require_module_any
    from fastapi import HTTPException
    from unittest.mock import AsyncMock, MagicMock, patch

    checker = require_module_any(["sales", "rental", "amc"])
    
    # 1. Platform admin bypasses check
    plat_user = MagicMock()
    plat_user.is_platform_admin = True
    res = await checker(current_user=plat_user, db=db)
    assert res == plat_user

    # 2. Regular user check with active modules
    reg_user = MagicMock()
    reg_user.is_platform_admin = False
    reg_user.tenant_id = MagicMock()
    
    # Mock active modules function call
    with patch("app.core.deps.get_tenant_active_modules", AsyncMock(return_value={"amc"})) as mock_active:
        res = await checker(current_user=reg_user, db=db)
        assert res == reg_user
        mock_active.assert_called_once_with(db, reg_user.tenant_id)

    # 3. Regular user check with none of modules active -> raises 402
    with patch("app.core.deps.get_tenant_active_modules", AsyncMock(return_value={"inventory"})):
        with pytest.raises(HTTPException) as excinfo:
            await checker(current_user=reg_user, db=db)
        assert excinfo.value.status_code == 402

