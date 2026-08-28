"""project finance eligibility (financier tracks the customer's funding eligibility)

Revision ID: 0016_finance_eligibility
Revises: 0015_consumer_fund_type
Create Date: 2026-08-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0016_finance_eligibility"
down_revision = "0015_consumer_fund_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("project_finance", sa.Column("eligibility", sa.String(length=16), nullable=False,
                                               server_default="pending"))


def downgrade() -> None:
    op.drop_column("project_finance", "eligibility")
