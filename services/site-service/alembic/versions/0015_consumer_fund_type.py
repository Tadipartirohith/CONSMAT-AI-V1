"""consumer fund type (captive/client chosen at onboarding)

Revision ID: 0015_consumer_fund_type
Revises: 0014_enquiries
Create Date: 2026-08-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0015_consumer_fund_type"
down_revision = "0014_enquiries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("consumers", sa.Column("fund_type", sa.String(length=12), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("consumers", "fund_type")
