"""add custom domain and email to tenants

Revision ID: 243eb39c8756
Revises: 014
Create Date: 2026-06-24 23:05:27.575544

"""
from alembic import op
import sqlalchemy as sa


revision = '243eb39c8756'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('tenants', sa.Column('custom_domain', sa.String(length=255), nullable=True))
    op.add_column('tenants', sa.Column('custom_email_sender', sa.String(length=255), nullable=True))
    op.add_column('tenants', sa.Column('email_templates', sa.JSON(), nullable=True))
    op.create_unique_constraint('uq_tenants_custom_domain', 'tenants', ['custom_domain'])


def downgrade() -> None:
    op.drop_constraint('uq_tenants_custom_domain', 'tenants', type_='unique')
    op.drop_column('tenants', 'email_templates')
    op.drop_column('tenants', 'custom_email_sender')
    op.drop_column('tenants', 'custom_domain')
