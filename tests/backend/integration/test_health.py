"""
Integration tests — /health endpoint
"""
import pytest


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_no_auth_required(client):
    """Health endpoint must be publicly accessible."""
    r = await client.get("/health")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_health_content_type_is_json(client):
    r = await client.get("/health")
    assert "application/json" in r.headers["content-type"]
