import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quotation import Quotation
from app.models.customer import Customer
from app.models.lead import Lead


@pytest.mark.asyncio
async def test_lead_quotation_workflow(
    client: AsyncClient, db: AsyncSession, admin_token: str
):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Create a Lead with company name and category
    lead_resp = await client.post(
        "/api/v1/leads",
        json={
            "name": "Test Lead Person",
            "company_name": "ACME Lead Corp",
            "category": "office",
            "interest_type": "amc",
        },
        headers=headers,
    )
    assert lead_resp.status_code == 201, lead_resp.text
    lead = lead_resp.json()
    assert lead["company_name"] == "ACME Lead Corp"
    assert lead["category"] == "office"
    lid = lead["id"]

    # 2. Create a Quotation linked directly to the Lead (customer_id is None)
    quote_resp = await client.post(
        "/api/v1/quotations",
        json={
            "lead_id": lid,
            "customer_id": None,
            "line_items": [
                {"description": "CCTV Camera Installation", "quantity": 4, "unit_price": 4500.0, "gst_rate": 18.0, "amount": 18000.0}
            ],
            "terms": "Valid for 30 days"
        },
        headers=headers,
    )
    assert quote_resp.status_code == 201, quote_resp.text
    quotation = quote_resp.json()
    assert quotation["customer_id"] is None
    assert quotation["lead_id"] == lid
    qid = quotation["id"]

    # 3. Export PDF for the Lead quotation (should succeed via LeadAdapter fallback)
    pdf_resp = await client.get(f"/api/v1/quotations/{qid}/pdf", headers=headers)
    assert pdf_resp.status_code == 200
    assert "application/pdf" in pdf_resp.headers["content-type"]

    # 4. Approve the quotation
    approve_resp = await client.post(f"/api/v1/quotations/{qid}/approve", headers=headers)
    assert approve_resp.status_code == 200

    # 5. Convert lead-only quotation to AMC (should automatically convert Lead -> Customer first)
    amc_resp = await client.post(
        f"/api/v1/quotations/{qid}/convert-to-amc",
        json={
            "start_date": "2026-07-01",
            "end_date": "2027-06-30",
            "preventive_visits_per_year": 4,
        },
        headers=headers,
    )
    assert amc_resp.status_code == 200, amc_resp.text
    amc_data = amc_resp.json()
    assert "amc_contract_id" in amc_data

    # 6. Verify lead has been converted, quotation updated with customer_id
    db_quote = (await db.execute(
        select(Quotation).where(Quotation.id == uuid.UUID(qid))
    )).scalar_one()
    assert db_quote.customer_id is not None

    db_cust = (await db.execute(
        select(Customer).where(Customer.id == db_quote.customer_id)
    )).scalar_one()
    assert db_cust.name == "Test Lead Person"
    assert db_cust.category == "office"  # correctly maps the Lead category office -> Customer category office
