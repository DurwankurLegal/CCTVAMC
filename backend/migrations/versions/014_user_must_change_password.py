"""User forced-password-reset flag (Phase 2 provisioning automation).

Adds ``must_change_password`` so a provisioned first admin (or any temp-password
account) is forced to reset its password at first login.

Revision ID: 014
Revises: 013
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("users", "must_change_password")
