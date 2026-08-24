"""spoke order requests (spoke asks hub to procure stock; hub approves + sets vendor/rate)

Revision ID: 0007_order_requests
Revises: 0006_market_alerts
Create Date: 2026-08-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_order_requests"
down_revision = "0006_market_alerts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "order_requests",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("site_ref", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("note", sa.String(length=400), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("requested_by", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("requested_by_role", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("decided_by", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("order_id", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "order_request_lines",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("request_id", sa.Integer, sa.ForeignKey("order_requests.id"), nullable=False),
        sa.Column("product_id", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("material_id", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("product_name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("qty", sa.Numeric(16, 3), nullable=False),
    )
    op.create_index("ix_orderreqline_req", "order_request_lines", ["request_id"])


def downgrade() -> None:
    op.drop_index("ix_orderreqline_req", table_name="order_request_lines")
    op.drop_table("order_request_lines")
    op.drop_table("order_requests")
