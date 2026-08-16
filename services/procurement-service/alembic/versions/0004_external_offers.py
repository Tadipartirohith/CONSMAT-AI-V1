"""external offers (price-scout market intelligence)

Revision ID: 0004_external_offers
Revises: 0003_products
Create Date: 2026-08-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_external_offers"
down_revision = "0003_products"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "external_offers",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("material_id", sa.String(length=40), nullable=False),
        sa.Column("product_name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("source", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("seller", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("price", sa.Numeric(14, 4), nullable=False),
        sa.Column("url", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("confidence", sa.String(length=16), nullable=False, server_default="indicative"),
        sa.Column("note", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_extoffer_material", "external_offers", ["material_id"])


def downgrade() -> None:
    op.drop_index("ix_extoffer_material", table_name="external_offers")
    op.drop_table("external_offers")
