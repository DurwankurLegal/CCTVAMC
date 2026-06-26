"""add timestamps to cash collection logs

Revision ID: f20df19f65f5
Revises: 016
Create Date: 2026-06-26 22:09:55.843653

"""
from alembic import op
import sqlalchemy as sa


revision = 'f20df19f65f5'
down_revision = '016'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('cash_collection_logs', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    op.add_column('cash_collection_logs', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))


def downgrade() -> None:
    op.drop_column('cash_collection_logs', 'updated_at')
    op.drop_column('cash_collection_logs', 'created_at')
