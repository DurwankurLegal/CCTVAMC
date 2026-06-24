"""Tenant trial expiry timestamp (Phase 1 lifecycle enforcement).

Adds ``trial_ends_at`` so login/refresh and the daily trial-expiry job can block
tenants whose trial window has elapsed. Backfills existing TRIAL tenants with a
14-day window from migration time.

Revision ID: 013
Revises: 012
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True))
    # Backfill: existing trial tenants get a window from now; active/suspended/cancelled stay null.
    op.execute(
        "UPDATE tenants SET trial_ends_at = now() + interval '14 days' "
        "WHERE status = 'trial' AND trial_ends_at IS NULL"
    )


def downgrade() -> None:
    op.drop_column("tenants", "trial_ends_at")
