"""open-market alerts (price-drop watch)

Revision ID: 0006_market_alerts
Revises: 0005_vendor_requests
Create Date: 2026-08-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_market_alerts"
down_revision = "0005_vendor_requests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_alerts",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("material_id", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("query", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("op", sa.String(length=4), nullable=False, server_default="lt"),
        sa.Column("value", sa.Numeric(14, 4), nullable=False),
        sa.Column("seller", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("location", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("market_alerts")
