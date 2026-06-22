"""Seed the database with a starter tenant and an admin user.

Idempotent: running it multiple times will not create duplicates.

Usage (from the backend/ directory, with venv active):

    python -m scripts.seed

Or via the running API container:

    docker compose exec api python -m scripts.seed

Default admin credentials (override with env vars):
    SEED_ADMIN_EMAIL    (default: admin@durwankur.ai)
    SEED_ADMIN_PASSWORD (default: Admin@1234)
    SEED_TENANT_NAME    (default: Durwankur)
"""

import asyncio
import os

from sqlalchemy import select, text

import app.core.database as db
from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import TenantRole, User

ADMIN_EMAIL = os.getenv("SEED_ADMIN_EMAIL", "admin@durwankur.ai")
ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD", "Admin@1234")
ADMIN_NAME = os.getenv("SEED_ADMIN_NAME", "Admin")
TENANT_NAME = os.getenv("SEED_TENANT_NAME", "Durwankur")
TENANT_SLUG = os.getenv("SEED_TENANT_SLUG", "durwankur")


async def seed() -> None:
    db._init_engine()
    async with db._AsyncSessionLocal() as session:
        # ── Tenant ────────────────────────────────────────────
        tenant = (
            await session.execute(select(Tenant).where(Tenant.slug == TENANT_SLUG))
        ).scalar_one_or_none()

        if tenant is None:
            tenant = Tenant(
                name=TENANT_NAME,
                slug=TENANT_SLUG,
                plan="starter",
                status="active",
                invoice_prefix="INV",
            )
            session.add(tenant)
            await session.flush()
            print(f"✔ Created tenant: {TENANT_NAME} ({tenant.id})")
        else:
            print(f"• Tenant already exists: {TENANT_NAME} ({tenant.id})")

        # RLS requires app.tenant_id to be set before touching tenant-scoped tables
        await session.execute(
            text("SELECT set_config('app.tenant_id', :tid, false)"),
            {"tid": str(tenant.id)},
        )

        # ── Admin user ────────────────────────────────────────
        admin = (
            await session.execute(select(User).where(User.email == ADMIN_EMAIL))
        ).scalar_one_or_none()

        if admin is None:
            admin = User(
                tenant_id=tenant.id,
                email=ADMIN_EMAIL,
                full_name=ADMIN_NAME,
                hashed_password=hash_password(ADMIN_PASSWORD),
                role=TenantRole.ADMIN,
                is_active=True,
            )
            session.add(admin)
            print(f"✔ Created admin user: {ADMIN_EMAIL}")
        else:
            print(f"• Admin user already exists: {ADMIN_EMAIL}")

        await session.commit()

    print("\nSeed complete.")
    print(f"  Login: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed())
