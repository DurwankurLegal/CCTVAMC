import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, admin_user, tenant):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "password123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, admin_user):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "wrongpass",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, admin_user, tenant):
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "password123",
    })
    refresh_token = login_resp.json()["refresh_token"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()
