"""consumer email + coverage-area change requests

Revision ID: 0005_email_area_requests
Revises: 0004_notifications
Create Date: 2026-08-21
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_email_area_requests"
down_revision = "0004_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("consumers", sa.Column("email", sa.String(length=160), nullable=False, server_default=""))
    op.create_table(
        "area_requests",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("spoke_id", sa.String(length=48), sa.ForeignKey("spokes.id"), nullable=False),
        sa.Column("area", sa.String(length=80), nullable=False),
        sa.Column("action", sa.String(length=10), nullable=False, server_default="add"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("requested_by_role", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("requested_by", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("decided_by_role", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("decided_by", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_area_req_spoke", "area_requests", ["spoke_id"])


def downgrade() -> None:
    op.drop_index("ix_area_req_spoke", table_name="area_requests")
    op.drop_table("area_requests")
    op.drop_column("consumers", "email")
