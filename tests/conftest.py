"""
Project-root conftest.py
========================
Shared fixtures available to all tests under tests/backend/.

The backend package is added to sys.path so imports like
    from app.core.security import hash_password
work without installing the package.
"""
import sys
import os

# Make the backend package importable from the project root.
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, os.path.abspath(BACKEND_DIR))

import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

# Provide minimal env vars so Settings() doesn't raise at import time.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:///")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-tests-only")

from app.main import app
from app.core.database import Base, get_db
from app.core.security import hash_password, create_access_token
from app.models.tenant import Tenant
from app.models.user import User, TenantRole

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def engine():
    """Fresh in-memory SQLite engine per test (fast, isolated)."""
    e = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with e.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield e
    await e.dispose()


@pytest_asyncio.fixture
async def db(engine):
    """Async DB session scoped to each test; rolls back after."""
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db):
    """Async HTTPX test client wired to the FastAPI app with the test DB."""
    async def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def tenant(db: AsyncSession) -> Tenant:
    t = Tenant(id=uuid.uuid4(), name="Acme Security", slug="acme-security")
    db.add(t)
    await db.flush()
    return t


@pytest_asyncio.fixture
async def admin_user(db: AsyncSession, tenant: Tenant) -> User:
    u = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email="admin@acme.com",
        full_name="Admin User",
        hashed_password=hash_password("Admin@1234"),
        role=TenantRole.ADMIN,
        is_active=True,
    )
    db.add(u)
    await db.flush()
    return u


@pytest_asyncio.fixture
async def manager_user(db: AsyncSession, tenant: Tenant) -> User:
    u = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email="manager@acme.com",
        full_name="Manager User",
        hashed_password=hash_password("Mgr@1234"),
        role=TenantRole.MANAGER,
        is_active=True,
    )
    db.add(u)
    await db.flush()
    return u


@pytest_asyncio.fixture
async def tech_user(db: AsyncSession, tenant: Tenant) -> User:
    u = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email="tech@acme.com",
        full_name="Tech User",
        hashed_password=hash_password("Tech@1234"),
        role=TenantRole.TECHNICIAN,
        is_active=True,
    )
    db.add(u)
    await db.flush()
    return u


@pytest.fixture
def admin_token(admin_user: User, tenant: Tenant) -> str:
    return create_access_token({
        "sub": str(admin_user.id),
        "tenant_id": str(tenant.id),
        "role": admin_user.role,
        "is_platform_admin": False,
    })


@pytest.fixture
def manager_token(manager_user: User, tenant: Tenant) -> str:
    return create_access_token({
        "sub": str(manager_user.id),
        "tenant_id": str(tenant.id),
        "role": manager_user.role,
        "is_platform_admin": False,
    })


@pytest.fixture
def auth_headers(admin_token: str) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def manager_headers(manager_token: str) -> dict:
    return {"Authorization": f"Bearer {manager_token}"}
