"""add selected_style to company_templates

Revision ID: 017
Revises: f20df19f65f5
Create Date: 2026-06-30 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '017'
down_revision = 'f20df19f65f5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('company_templates', sa.Column('selected_style', sa.String(50), nullable=True, server_default='style1'))


def downgrade() -> None:
    op.drop_column('company_templates', 'selected_style')
