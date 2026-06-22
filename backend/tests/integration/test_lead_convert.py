"""Lead conversion carries category and creates an initial quotation (SRS 4.2)."""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quotation import Quotation


@pytest.mark.asyncio
async def test_convert_preserves_category_and_creates_quotation(
    client: AsyncClient, db: AsyncSession, admin_token: str, tenant
):
    headers = {"Authorization": f"Bearer {admin_token}"}
    lead = await client.post(
        "/api/v1/leads",
        json={"name": "Green CHS", "category": "chs", "interest_type": "amc"},
        headers=headers,
    )
    assert lead.status_code == 201
    lead_id = lead.json()["id"]

    conv = await client.post(f"/api/v1/leads/{lead_id}/convert", headers=headers)
    assert conv.status_code == 200
    customer = conv.json()
    assert customer["category"] == "chs"  # category carried over, not hardcoded

    # An initial quotation must exist for the new customer.
    quotes = (await db.execute(
        select(Quotation).where(Quotation.customer_id == uuid.UUID(customer["id"]))
    )).scalars().all()
    assert len(quotes) == 1
    assert quotes[0].lead_id is not None

    # Re-converting the same lead is rejected.
    again = await client.post(f"/api/v1/leads/{lead_id}/convert", headers=headers)
    assert again.status_code == 409
