"""User 2FA (TOTP) + technician profile fields (SRS 4.21, 4.10).

Revision ID: 011
Revises: 010
Create Date: 2026-06-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("totp_secret", sa.String(64), nullable=True))
    op.add_column("users", sa.Column("totp_enabled", sa.Boolean, nullable=False, server_default="false"))
    op.add_column("users", sa.Column("skills", postgresql.JSONB, server_default="[]"))
    op.add_column("users", sa.Column("certifications", postgresql.JSONB, server_default="[]"))
    op.add_column("users", sa.Column("territory", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("availability", sa.String(50), nullable=True))


def downgrade() -> None:
    for col in ("availability", "territory", "certifications", "skills", "totp_enabled", "totp_secret"):
        op.drop_column("users", col)
