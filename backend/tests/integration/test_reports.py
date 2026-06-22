"""Standard report set + CSV/Excel export (SRS 4.16)."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_standard_reports_and_export(client: AsyncClient, admin_token: str):
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
