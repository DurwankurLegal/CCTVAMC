import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_customer(client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/api/v1/customers",
        json={"name": "Sunita Society", "category": "chs"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Sunita Society"
    assert data["category"] == "chs"


@pytest.mark.asyncio
async def test_list_customers(client: AsyncClient, admin_token: str):
    resp = await client.get(
        "/api/v1/customers",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_unauthenticated_returns_401(client: AsyncClient):
    resp = await client.get("/api/v1/customers")
    assert resp.status_code == 403  # HTTPBearer returns 403 when no credentials
