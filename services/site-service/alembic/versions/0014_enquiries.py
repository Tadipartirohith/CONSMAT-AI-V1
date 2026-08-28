"""public customer enquiries (geofence-routed to spoke or hub)

Revision ID: 0014_enquiries
Revises: 0013_phase_change_remarks
Create Date: 2026-08-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_enquiries"
down_revision = "0013_phase_change_remarks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "enquiries",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("email", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("location", sa.String(length=160), nullable=False),
        sa.Column("message", sa.String(length=600), nullable=False, server_default=""),
        sa.Column("spoke_id", sa.String(length=48), nullable=False, server_default=""),
        sa.Column("routed_to", sa.String(length=8), nullable=False, server_default="hub"),
        sa.Column("status", sa.String(length=12), nullable=False, server_default="new"),
        sa.Column("handled_by", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_enquiry_spoke", "enquiries", ["spoke_id"])


def downgrade() -> None:
    op.drop_index("ix_enquiry_spoke", table_name="enquiries")
    op.drop_table("enquiries")
