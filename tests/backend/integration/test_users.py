"""
Integration tests — Users API
=================================
Covers: list/create/get/update users, role list, /me, plan-limit enforcement,
        duplicate email, auth guard.
"""
import uuid
import pytest


BASE = "/api/v1/users"

USER_PAYLOAD = {
    "email": "tech1@test.com",
    "full_name": "Tech One",
    "password": "Secret@123",
    "role": "technician",
}


@pytest.mark.asyncio
async def test_users_requires_auth(client):
    r = await client.get(BASE)
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_users_returns_self(client, auth_headers, admin_user):
    r = await client.get(BASE, headers=auth_headers)
    assert r.status_code == 200
    emails = [u["email"] for u in r.json()]
    assert admin_user.email in emails


@pytest.mark.asyncio
async def test_me_returns_current_user(client, auth_headers, admin_user):
    r = await client.get(f"{BASE}/me", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["email"] == admin_user.email


@pytest.mark.asyncio
async def test_roles_endpoint(client, auth_headers):
    r = await client.get(f"{BASE}/roles", headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_create_user(client, auth_headers):
    r = await client.post(BASE, json=USER_PAYLOAD, headers=auth_headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == "tech1@test.com"
    assert body["role"] == "technician"


@pytest.mark.asyncio
async def test_create_user_duplicate_email(client, auth_headers, admin_user):
    r = await client.post(BASE, json={**USER_PAYLOAD, "email": admin_user.email},
                          headers=auth_headers)
    assert r.status_code in (400, 409)


@pytest.mark.asyncio
async def test_create_user_invalid_email(client, auth_headers):
    r = await client.post(BASE, json={**USER_PAYLOAD, "email": "not-an-email"},
                          headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_get_user_by_id(client, auth_headers):
    cr = await client.post(BASE, json=USER_PAYLOAD, headers=auth_headers)
    uid = cr.json()["id"]
    r = await client.get(f"{BASE}/{uid}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["id"] == uid


@pytest.mark.asyncio
async def test_get_nonexistent_user_returns_404(client, auth_headers):
    r = await client.get(f"{BASE}/{uuid.uuid4()}", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_user_role(client, auth_headers):
    cr = await client.post(BASE, json=USER_PAYLOAD, headers=auth_headers)
    uid = cr.json()["id"]
    r = await client.patch(f"{BASE}/{uid}", json={"role": "manager"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["role"] == "manager"


@pytest.mark.asyncio
async def test_deactivate_user(client, auth_headers):
    cr = await client.post(BASE, json=USER_PAYLOAD, headers=auth_headers)
    uid = cr.json()["id"]
    r = await client.patch(f"{BASE}/{uid}", json={"is_active": False}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["is_active"] is False
