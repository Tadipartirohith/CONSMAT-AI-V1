"""notifications (JIT scheduler messages to the field team)

Revision ID: 0004_notifications
Revises: 0003_bom_phase_dates
Create Date: 2026-08-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_notifications"
down_revision = "0003_bom_phase_dates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("site_id", sa.Integer, sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("spoke_id", sa.String(length=48), nullable=False, server_default=""),
        sa.Column("audience", sa.String(length=24), nullable=False, server_default="field"),
        sa.Column("phase_seq", sa.Integer, nullable=False, server_default="0"),
        sa.Column("kind", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("message", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("read", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_notif_site", "notifications", ["site_id"])
    op.create_index("ix_notif_spoke", "notifications", ["spoke_id"])


def downgrade() -> None:
    op.drop_index("ix_notif_spoke", table_name="notifications")
    op.drop_index("ix_notif_site", table_name="notifications")
    op.drop_table("notifications")
