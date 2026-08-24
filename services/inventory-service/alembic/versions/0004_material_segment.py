"""material segment (ConSmat page-3 business vertical)

Revision ID: 0004_material_segment
Revises: 0003_product_stock
Create Date: 2026-08-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_material_segment"
down_revision = "0003_product_stock"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("materials", sa.Column("segment", sa.String(length=16), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("materials", "segment")
