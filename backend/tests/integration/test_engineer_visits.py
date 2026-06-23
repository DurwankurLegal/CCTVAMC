import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_and_edit_engineer_visit(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # 1. Create engineer visit
    create_resp = await client.post(
        "/api/v1/engineer-visits",
        json={"visit_type": "corrective"},
        headers=headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    visit_data = create_resp.json()
    visit_id = visit_data["id"]
    
    # 2. Patch (edit) engineer visit
    patch_resp = await client.patch(
        f"/api/v1/engineer-visits/{visit_id}",
        json={"work_performed": "Fixed DVR power issue", "customer_feedback": "Excellent work"},
        headers=headers,
    )
    assert patch_resp.status_code == 200, patch_resp.text
    updated_data = patch_resp.json()
    assert updated_data["work_performed"] == "Fixed DVR power issue"
    assert updated_data["customer_feedback"] == "Excellent work"

    # 3. Put (edit) engineer visit
    put_resp = await client.put(
        f"/api/v1/engineer-visits/{visit_id}",
        json={"work_performed": "Fixed DVR power issue v2"},
        headers=headers,
    )
    assert put_resp.status_code == 200, put_resp.text
    updated_data_v2 = put_resp.json()
    assert updated_data_v2["work_performed"] == "Fixed DVR power issue v2"
