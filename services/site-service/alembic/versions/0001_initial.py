"""initial site schema: spokes, consumers, sites, phases, bom_lines, phase_progress, dispatches

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "spokes",
        sa.Column("id", sa.String(length=48), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("geofence", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "consumers",
        sa.Column("id", sa.String(length=48), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("tier", sa.String(length=20), nullable=False, server_default="individual"),
        sa.Column("phone", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("spoke_id", sa.String(length=48), sa.ForeignKey("spokes.id"), nullable=False),
    )
    op.create_index("ix_consumer_spoke", "consumers", ["spoke_id"])
    op.create_table(
        "phases",
        sa.Column("seq", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("repeats_per_floor", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "sites",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("consumer_id", sa.String(length=48), sa.ForeignKey("consumers.id"), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("location", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("area_sqft", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("floors", sa.Integer, nullable=False, server_default="1"),
        sa.Column("construction_type", sa.String(length=20), nullable=False, server_default="standard"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="planning"),
        sa.Column("total_area", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_site_consumer", "sites", ["consumer_id"])
    op.create_table(
        "bom_lines",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("site_id", sa.Integer, sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("material_id", sa.String(length=40), nullable=False),
        sa.Column("total_qty", sa.Numeric(16, 3), nullable=False),
    )
    op.create_index("ix_bom_site", "bom_lines", ["site_id"])
    op.create_table(
        "phase_progress",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("site_id", sa.Integer, sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("phase_seq", sa.Integer, nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("site_id", "phase_seq", name="uq_site_phase"),
    )
    op.create_index("ix_pp_site", "phase_progress", ["site_id"])
    op.create_table(
        "dispatches",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("site_id", sa.Integer, sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("phase_seq", sa.Integer, nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="dispatched"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_dispatch_site", "dispatches", ["site_id"])
    op.create_table(
        "dispatch_lines",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("dispatch_id", sa.Integer, sa.ForeignKey("dispatches.id"), nullable=False),
        sa.Column("material_id", sa.String(length=40), nullable=False),
        sa.Column("qty", sa.Numeric(16, 3), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="dispatched"),
    )
    op.create_index("ix_dline_dispatch", "dispatch_lines", ["dispatch_id"])


def downgrade() -> None:
    for ix, tbl in [
        ("ix_dline_dispatch", "dispatch_lines"), (None, "dispatch_lines"),
        ("ix_dispatch_site", "dispatches"), (None, "dispatches"),
        ("ix_pp_site", "phase_progress"), (None, "phase_progress"),
        ("ix_bom_site", "bom_lines"), (None, "bom_lines"),
        ("ix_site_consumer", "sites"), (None, "sites"),
        (None, "phases"),
        ("ix_consumer_spoke", "consumers"), (None, "consumers"),
        (None, "spokes"),
    ]:
        if ix:
            op.drop_index(ix, table_name=tbl)
        else:
            op.drop_table(tbl)
