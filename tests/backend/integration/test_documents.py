"""
Integration tests — Documents API
=====================================
Covers: list documents for an entity, upload validation, auth guard.

The upload route is multipart (entity_type/entity_id/file). Listing requires
entity_type + entity_id query params.
"""
import uuid
import pytest


BASE = "/api/v1/documents"


@pytest.mark.asyncio
async def test_documents_requires_auth(client):
    r = await client.get(f"{BASE}?entity_type=customer&entity_id={uuid.uuid4()}")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_documents_requires_entity_params(client, auth_headers):
    r = await client.get(BASE, headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_list_documents_empty_for_entity(client, auth_headers):
    r = await client.get(f"{BASE}?entity_type=customer&entity_id={uuid.uuid4()}",
                         headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_upload_requires_file(client, auth_headers):
    """entity_type/entity_id/file are all required form fields."""
    r = await client.post(BASE, data={"entity_type": "customer",
                                      "entity_id": str(uuid.uuid4())},
                          headers=auth_headers)
    assert r.status_code == 422
