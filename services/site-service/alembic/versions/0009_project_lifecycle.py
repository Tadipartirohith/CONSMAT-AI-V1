"""project lifecycle: per-project type/stage/budget, drop consumer NBFC flag

Revision ID: 0009_project_lifecycle
Revises: 0008_consumer_nbfc
Create Date: 2026-08-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_project_lifecycle"
down_revision = "0008_consumer_nbfc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sites", sa.Column("project_type", sa.String(length=12), nullable=False, server_default=""))
    op.add_column("sites", sa.Column("stage", sa.String(length=24), nullable=False, server_default="onboarded"))
    op.add_column("sites", sa.Column("budget", sa.Numeric(16, 2), nullable=True))
    op.add_column("sites", sa.Column("payment_received", sa.Boolean(), nullable=False, server_default=sa.false()))
    # NBFC flag is replaced by the per-project captive/client type
    op.drop_column("consumers", "is_nbfc")


def downgrade() -> None:
    op.add_column("consumers", sa.Column("is_nbfc", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.drop_column("sites", "payment_received")
    op.drop_column("sites", "budget")
    op.drop_column("sites", "stage")
    op.drop_column("sites", "project_type")
