"""
Shared pytest fixtures for backend tests.

Uses aiosqlite in-memory so tests run without a real Postgres instance.
RLS is not available on SQLite but application-layer tenant_id filtering
in every query still provides isolation (see TenantRepository).
"""
from __future__ import annotations

import os
import sys
import uuid
from typing import AsyncGenerator
from unittest.mock import MagicMock

# Mock weasyprint to prevent errors on environments missing GObject/Pango system libraries
mock_weasyprint = MagicMock()
mock_weasyprint.HTML = MagicMock()
sys.modules['weasyprint'] = mock_weasyprint

import pytest
import pytest_asyncio

# Make the backend package importable regardless of pytest rootdir/invocation.
_BACKEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "backend")
)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ── Point settings at an in-memory SQLite database before importing app ──────
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["DATABASE_URL_SYNC"] = "sqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://:redis_dev_pass@localhost:6379/0"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-pytest-only"
os.environ["JWT_ALGORITHM"] = "HS256"

# ── Imports AFTER env is set ─────────────────────────────────────────────────
from app.core.config import get_settings          # noqa: E402  (order matters)
from app.core.database import Base                # noqa: E402
from app.core.security import (                   # noqa: E402
    hash_password, create_access_token, create_refresh_token,
)
from app.main import app                          # noqa: E402

get_settings.cache_clear()                        # bust the lru_cache


# ── Engine / session factory for tests ───────────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

_test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
_TestSessionLocal = async_sessionmaker(_test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """Create all tables once per test session."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture()
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a DB session that rolls back after each test for isolation."""
    async with _TestSessionLocal() as session:
        yield session
        await session.rollback()


# ── Canonical test identities ─────────────────────────────────────────────────
TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
ADMIN_USER_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
VIEWER_USER_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
CUSTOMER_ID = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")


@pytest_asyncio.fixture()
async def tenant(db: AsyncSession):
    from app.models.tenant import Tenant
    t = Tenant(
        id=TENANT_ID, name="Test Corp", slug="test-corp",
        plan="growth", status="active",
    )
    db.add(t)
    await db.flush()
    return t


@pytest_asyncio.fixture()
async def admin_user(db: AsyncSession, tenant):
    from app.models.user import User
    u = User(
        id=ADMIN_USER_ID, tenant_id=TENANT_ID,
        email="admin@test.com", full_name="Test Admin",
        hashed_password=hash_password("secret123"),
        role="admin", is_active=True, is_platform_admin=False,
    )
    db.add(u)
    await db.flush()
    return u


@pytest_asyncio.fixture()
async def viewer_user(db: AsyncSession, tenant):
    from app.models.user import User
    u = User(
        id=VIEWER_USER_ID, tenant_id=TENANT_ID,
        email="viewer@test.com", full_name="Test Viewer",
        hashed_password=hash_password("secret123"),
        role="viewer", is_active=True, is_platform_admin=False,
    )
    db.add(u)
    await db.flush()
    return u


@pytest_asyncio.fixture()
async def platform_user(db: AsyncSession):
    from app.models.user import User
    uid = uuid.uuid4()
    u = User(
        id=uid, tenant_id=TENANT_ID,
        email="platform@test.com", full_name="Platform Admin",
        hashed_password=hash_password("secret123"),
        role="admin", is_active=True, is_platform_admin=True,
    )
    db.add(u)
    await db.flush()
    return u


@pytest_asyncio.fixture()
async def customer(db: AsyncSession, tenant):
    from app.models.customer import Customer
    c = Customer(
        id=CUSTOMER_ID, tenant_id=TENANT_ID,
        name="Test Customer", category="commercial",
        gstin="29ABCDE1234F1Z5", state_code="29",
    )
    db.add(c)
    await db.flush()
    return c


SITE_ID = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")


@pytest_asyncio.fixture()
async def site(db: AsyncSession, customer):
    """A customer site — required to anchor CCTV assets."""
    from app.models.customer import CustomerSite
    s = CustomerSite(
        id=SITE_ID, tenant_id=TENANT_ID, customer_id=CUSTOMER_ID,
        name="Main Branch", address="12 MG Road, Pune",
    )
    db.add(s)
    await db.flush()
    return s


# ── JWT token helpers ─────────────────────────────────────────────────────────
def _make_token(user_id, tenant_id, role, is_platform_admin=False) -> str:
    return create_access_token({
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role,
        "is_platform_admin": is_platform_admin,
    })


@pytest.fixture()
def admin_token(admin_user) -> str:
    return _make_token(ADMIN_USER_ID, TENANT_ID, "admin")


@pytest.fixture()
def viewer_token(viewer_user) -> str:
    return _make_token(VIEWER_USER_ID, TENANT_ID, "viewer")


@pytest.fixture()
def platform_token(platform_user) -> str:
    return _make_token(platform_user.id, TENANT_ID, "admin", is_platform_admin=True)


# ── Header helpers (used by integration tests) ────────────────────────────────
@pytest.fixture()
def auth_headers(admin_token) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture()
def viewer_headers(viewer_token) -> dict:
    return {"Authorization": f"Bearer {viewer_token}"}


@pytest.fixture()
def platform_headers(platform_token) -> dict:
    return {"Authorization": f"Bearer {platform_token}"}


# ── HTTP client that overrides the DB dependency ──────────────────────────────
@pytest_asyncio.fixture()
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient wired to the FastAPI app with the test DB session injected."""
    from app.core.database import get_db

    async def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def auth_client(db: AsyncSession, admin_user) -> AsyncGenerator[AsyncClient, None]:
    """Client pre-authenticated as the admin user."""
    from app.core.database import get_db

    async def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    token = _make_token(ADMIN_USER_ID, TENANT_ID, "admin")
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
