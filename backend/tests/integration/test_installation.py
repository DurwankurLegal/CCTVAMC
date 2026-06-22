"""New installation: survey -> handover auto-creates AMC + registers warranty (SRS 4.5)."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_installation_handover_creates_amc(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}

    cust = await client.post(
        "/api/v1/customers", json={"name": "Install Co", "category": "commercial"}, headers=headers,
    )
    cid = cust.json()["id"]

    inst = await client.post(
        "/api/v1/installations", json={"customer_id": cid}, headers=headers,
    )
    assert inst.status_code == 201
    iid = inst.json()["id"]
    assert inst.json()["status"] == "survey_pending"
    assert inst.json()["work_order_number"].startswith("WO-")

    # survey
    sv = await client.post(
        f"/api/v1/installations/{iid}/survey",
        json={"survey_notes": "10 cameras feasible", "recommended_camera_count": 10},
        headers=headers,
    )
    assert sv.status_code == 200 and sv.json()["status"] == "survey_done"

    # bad OTP rejected
    bad = await client.post(f"/api/v1/installations/{iid}/handover",
                            json={"otp": "000000", "amc_annual_amount": 5000}, headers=headers)
    assert bad.status_code == 400

    # request OTP then hand over
    otp = (await client.post(f"/api/v1/installations/{iid}/handover-otp", headers=headers)).json()["otp"]
    ho = await client.post(f"/api/v1/installations/{iid}/handover",
                           json={"otp": otp, "amc_annual_amount": 5000, "preventive_visits_per_year": 2},
                           headers=headers)
    assert ho.status_code == 200
    body = ho.json()
    assert body["status"] == "handed_over"
    assert body["amc_contract_id"] is not None
