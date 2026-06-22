"""Activating an AMC contract auto-generates a preventive-maintenance schedule (SRS 4.9)."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_amc_activation_generates_pm_schedule(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}

    cust = await client.post(
        "/api/v1/customers", json={"name": "AMC Co", "category": "commercial"}, headers=headers,
    )
    cid = cust.json()["id"]

    amc = await client.post(
        "/api/v1/amc",
        json={"customer_id": cid, "start_date": "2026-01-01", "end_date": "2026-12-31",
              "annual_amount": 12000, "preventive_visits_per_year": 4},
        headers=headers,
    )
    assert amc.status_code == 201
    amc_id = amc.json()["id"]

    act = await client.post(f"/api/v1/amc/{amc_id}/activate", headers=headers)
    assert act.status_code == 200
    assert act.json()["status"] == "active"

    sched = await client.get(f"/api/v1/amc/{amc_id}/pm-schedule", headers=headers)
    assert sched.status_code == 200
    body = sched.json()
    assert body["summary"]["committed"] == 4
    assert len(body["visits"]) == 4

    # reschedule and skip
    first = body["visits"][0]["id"]
    second = body["visits"][1]["id"]
    r = await client.post(f"/api/v1/amc/pm-schedule/{first}/reschedule",
                          json={"new_date": "2026-04-15", "reason": "customer request"}, headers=headers)
    assert r.status_code == 200 and r.json()["status"] == "rescheduled"
    s = await client.post(f"/api/v1/amc/pm-schedule/{second}/skip",
                          json={"reason": "site closed"}, headers=headers)
    assert s.status_code == 200 and s.json()["status"] == "skipped"
