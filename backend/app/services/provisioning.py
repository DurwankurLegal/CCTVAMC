"""Tenant provisioning automation (Phase 2).

Composes a ready-to-use workspace in one transaction: tenant row (with trial
window + audit, via ``tenant_service.create_tenant``), default branding/settings,
the company's first admin user (with one-time credentials), and seeded
notification templates. Sales-led only — invoked by a platform admin, never via
public signup.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.tenant import Tenant
from app.models.user import User, TenantRole
from app.models.notification import NotificationTemplate
from app.core.security import hash_password
from app.services import audit as audit_service
from app.services.tenant import create_tenant, _set_rls
from app.services.notification_templates import DEFAULT_TEMPLATES

# Sensible workspace defaults; only fill what the admin didn't already set.
DEFAULT_BRANDING = {"primary_color": "#1677ff", "logo_url": None, "theme_key": "dark_professional"}
DEFAULT_SETTINGS = {"timezone": "Asia/Kolkata", "currency": "INR"}

TEMP_PASSWORD_BYTES = 12


def generate_temp_password() -> str:
    """One-time password for a provisioned admin (URL-safe, ~16 chars)."""
    return secrets.token_urlsafe(TEMP_PASSWORD_BYTES)


def apply_workspace_defaults(branding: Optional[dict], settings: Optional[dict]) -> tuple[dict, dict]:
    """Merge default branding/settings under any admin-supplied values (pure).
    Admin-set keys win; missing keys are filled from the defaults."""
    return (
        {**DEFAULT_BRANDING, **(branding or {})},
        {**DEFAULT_SETTINGS, **(settings or {})},
    )


@dataclass
class ProvisionResult:
    tenant: Tenant
    first_admin: Optional[User]
    temp_password: Optional[str]  # returned ONCE; never persisted/audited in clear


async def provision_tenant(db: AsyncSession, payload, actor_user_id: Optional[UUID]) -> ProvisionResult:
    # 1. Tenant — reuses create_tenant (slug uniqueness, trial_ends_at, audit).
    tenant = await create_tenant(db, payload.tenant, actor_user_id=actor_user_id)

    # 2. Default branding/settings without clobbering admin-supplied values.
    tenant.branding, tenant.settings = apply_workspace_defaults(tenant.branding, tenant.settings)
    await db.flush()

    # Required before inserting further tenant-scoped rows so they pass RLS.
    await _set_rls(db, tenant.id)

    # 3. First admin user (optional — preserves back-compat when omitted).
    first_admin: Optional[User] = None
    temp_password: Optional[str] = None
    if payload.admin_email:
        exists = (await db.execute(
            select(User).where(User.tenant_id == tenant.id, User.email == payload.admin_email)
        )).scalar_one_or_none()
        if exists:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Admin email already exists for this tenant")
        temp_password = payload.admin_password or generate_temp_password()
        first_admin = User(
            tenant_id=tenant.id,
            email=payload.admin_email,
            full_name=payload.admin_full_name or payload.admin_email,
            hashed_password=hash_password(temp_password),
            role=TenantRole.ADMIN,
            is_active=True,
            # Force a reset only when WE generated the password.
            must_change_password=(payload.admin_password is None),
        )
        db.add(first_admin)
        await db.flush()
        await db.refresh(first_admin)
        await audit_service.write_audit(
            db, tenant.id, "user", first_admin.id, "create",
            before=None,
            after={"email": first_admin.email, "role": "admin"},  # never the password
            actor_user_id=actor_user_id)

    # 4. Seed default notification templates (idempotent).
    await seed_templates(db, tenant.id)

    return ProvisionResult(tenant=tenant, first_admin=first_admin, temp_password=temp_password)


async def seed_templates(db: AsyncSession, tenant_id: UUID) -> int:
    """Insert any default templates the tenant is missing. Returns count inserted.
    Idempotent: existing (event_type, channel) pairs are skipped."""
    existing = {
        (t.event_type, t.channel)
        for t in (await db.execute(
            select(NotificationTemplate).where(NotificationTemplate.tenant_id == tenant_id)
        )).scalars().all()
    }
    inserted = 0
    for event_type, channel, subject, body in DEFAULT_TEMPLATES:
        if (event_type, channel) in existing:
            continue
        db.add(NotificationTemplate(
            tenant_id=tenant_id, event_type=event_type, channel=channel,
            subject=subject, body=body, is_active=True))
        inserted += 1
    await db.flush()
    return inserted
