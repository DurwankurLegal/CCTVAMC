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

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def engine():
    e = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
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
