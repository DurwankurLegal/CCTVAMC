"""Lead: category, interest_type, lost_reason (SRS 4.2).

Revision ID: 003
Revises: 002
Create Date: 2026-06-22
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("category", sa.String(50), nullable=True))
    op.add_column("leads", sa.Column("interest_type", sa.String(50), nullable=True))
    op.add_column("leads", sa.Column("lost_reason", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("leads", "lost_reason")
    op.drop_column("leads", "interest_type")
    op.drop_column("leads", "category")
