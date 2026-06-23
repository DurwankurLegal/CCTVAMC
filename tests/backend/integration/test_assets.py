"""
Integration tests — Assets API (CCTV assets)
=================================================
Covers: create/list/get/update asset, validation, auth guard.
Assets are anchored to a CustomerSite (the `site` fixture).
"""
import uuid
import pytest


BASE = "/api/v1/assets"


def _payload(site_id, **overrides):
    return {
        "site_id": str(site_id),
        "serial_number": "SN-0001",
        "make": "Hikvision",
        "model": "DS-2CD2042",
        "asset_type": "dome_camera",
        **overrides,
    }


@pytest.mark.asyncio
async def test_assets_requires_auth(client):
    r = await client.get(BASE)
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_asset(client, auth_headers, site):
    r = await client.post(BASE, json=_payload(site.id), headers=auth_headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["serial_number"] == "SN-0001"
    assert body["site_id"] == str(site.id)


@pytest.mark.asyncio
async def test_create_asset_missing_site_is_422(client, auth_headers):
    r = await client.post(BASE, json={"serial_number": "X"}, headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_list_assets(client, auth_headers, site):
    await client.post(BASE, json=_payload(site.id), headers=auth_headers)
    r = await client.get(BASE, headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_get_asset_by_id(client, auth_headers, site):
    cr = await client.post(BASE, json=_payload(site.id), headers=auth_headers)
    aid = cr.json()["id"]
    r = await client.get(f"{BASE}/{aid}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["id"] == aid


@pytest.mark.asyncio
async def test_get_nonexistent_asset_returns_404(client, auth_headers):
    r = await client.get(f"{BASE}/{uuid.uuid4()}", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_asset_status(client, auth_headers, site):
    cr = await client.post(BASE, json=_payload(site.id), headers=auth_headers)
    aid = cr.json()["id"]
    r = await client.patch(f"{BASE}/{aid}", json={"location_description": "Lobby"},
                           headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["location_description"] == "Lobby"
