"""Step 8 — route authorization matrix.

Systematically asserts that high-risk endpoints reject:
  - unauthenticated requests (401),
  - authenticated-but-unauthorized roles (403).

Complements the per-module cross-tenant tests (test_tenant_isolation, etc.).
"""
import uuid
import pytest
from httpx import AsyncClient
from app.core.security import create_access_token


def _token(role: str, tenant_id, platform=False) -> str:
    return create_access_token({
        "sub": str(uuid.uuid4()), "tenant_id": str(tenant_id),
        "role": role, "is_platform_admin": platform,
    })


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


# (method, path) for write/admin endpoints that must be protected.
PROTECTED_WRITES = [
    ("post", "/api/v1/users", {"email": "a@b.com", "full_name": "A", "password": "password123", "role": "viewer"}),
    ("get", "/api/v1/users/roles", None),
    ("post", "/api/v1/vendors", {"name": "V"}),
    ("post", "/api/v1/inventory", {"name": "I", "reorder_level": 0}),
    ("post", "/api/v1/quotations", {"customer_id": str(uuid.uuid4()), "line_items": []}),
    ("get", "/api/v1/notifications/templates", None),
]


@pytest.mark.asyncio
async def test_unauthenticated_requests_rejected(client: AsyncClient):
    # No Authorization header → 401/403 (never 200) on protected reads & writes.
    for method, path, body in PROTECTED_WRITES:
        resp = await getattr(client, method)(path, json=body) if body else await getattr(client, method)(path)
        assert resp.status_code in (401, 403), f"{method.upper()} {path} returned {resp.status_code} unauthenticated"


@pytest.mark.asyncio
async def test_viewer_cannot_write_high_risk_modules(client: AsyncClient, tenant):
    viewer = _token("viewer", tenant.id)
    for method, path, body in PROTECTED_WRITES:
        if method == "get":
            continue
        resp = await getattr(client, method)(path, json=body, headers=_auth(viewer))
        assert resp.status_code == 403, f"viewer reached {method.upper()} {path} ({resp.status_code})"


@pytest.mark.asyncio
async def test_technician_scope_is_limited(client: AsyncClient, tenant):
    """Technician may write engineer visits but not manage users or vendors."""
    tech = _token("technician", tenant.id)
    # denied: user management + vendor creation
    assert (await client.post("/api/v1/users", headers=_auth(tech),
            json={"email": "x@y.com", "full_name": "X", "password": "password123", "role": "viewer"})).status_code == 403
    assert (await client.post("/api/v1/vendors", headers=_auth(tech), json={"name": "V"})).status_code == 403


@pytest.mark.asyncio
async def test_platform_admin_only_on_tenant_routes(client: AsyncClient, tenant):
    # A tenant admin (not platform) is denied platform tenant management.
    admin = _token("admin", tenant.id, platform=False)
    assert (await client.get("/api/v1/tenants", headers=_auth(admin))).status_code == 403
    # Platform admin allowed.
    plat = _token("admin", tenant.id, platform=True)
    assert (await client.get("/api/v1/tenants", headers=_auth(plat))).status_code == 200
