import os
import sys
from unittest.mock import MagicMock

# Mock weasyprint to prevent errors on environments missing GObject/Pango system libraries
mock_weasyprint = MagicMock()
mock_weasyprint.HTML = MagicMock()
sys.modules['weasyprint'] = mock_weasyprint

# Point Redis to localhost for test runs BEFORE importing app
import os
os.environ["REDIS_URL"] = "redis://:redis_dev_pass@localhost:6379/0"

from app.core.config import get_settings
get_settings.cache_clear()

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.core.security import hash_password, create_access_token
from app.models.tenant import Tenant
from app.models.user import User, TenantRole
import uuid

# Use a real Postgres when TEST_DATABASE_URL is set (CI / RLS tests); otherwise
# an in-memory SQLite for fast unit/integration runs.
TEST_DB_URL = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
IS_POSTGRES = TEST_DB_URL.startswith("postgresql")


@pytest_asyncio.fixture
async def engine():
    # Function-scoped so the async engine is created in each test's event loop
    # (required for asyncpg; harmless for SQLite). For SQLite this also yields a
    # fresh in-memory DB per test.
    if IS_POSTGRES:
        e = create_async_engine(TEST_DB_URL)
    else:
        e = create_async_engine(
            TEST_DB_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
    async with e.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield e
    await e.dispose()


@pytest_asyncio.fixture
async def db(engine):
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def tenant(db: AsyncSession):
    t = Tenant(id=uuid.uuid4(), name="Test Tenant", slug="test-tenant")
    db.add(t)
    await db.flush()
    return t


@pytest_asyncio.fixture
async def admin_user(db: AsyncSession, tenant: Tenant):
    u = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email="admin@test.com",
        full_name="Admin User",
        hashed_password=hash_password("password123"),
        role=TenantRole.ADMIN,
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
