"""per-product (brand) margin rules

Revision ID: 0002_product_margin
Revises: 0001_initial
Create Date: 2026-08-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_product_margin"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("margin_rules", sa.Column("product_id", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("margin_rules", "product_id")
