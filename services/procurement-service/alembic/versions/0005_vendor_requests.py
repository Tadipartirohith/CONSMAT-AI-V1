"""vendor add/remove requests (ops requests, supervisor/manager approves)

Revision ID: 0005_vendor_requests
Revises: 0004_external_offers
Create Date: 2026-08-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_vendor_requests"
down_revision = "0004_external_offers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vendor_requests",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("action", sa.String(length=10), nullable=False),
        sa.Column("vendor_id", sa.String(length=48), nullable=False, server_default=""),
        sa.Column("name", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("city", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("phone", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("gstin", sa.String(length=24), nullable=False, server_default=""),
        sa.Column("is_hub_self", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("reason", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("requested_by_role", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("requested_by", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("decided_by_role", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("decided_by", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("vendor_requests")
