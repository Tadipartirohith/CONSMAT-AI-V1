"""consumer NBFC flag (captured at spoke onboarding)

Revision ID: 0008_consumer_nbfc
Revises: 0007_dispatch_received
Create Date: 2026-08-22
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_consumer_nbfc"
down_revision = "0007_dispatch_received"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("consumers", sa.Column("is_nbfc", sa.Boolean(), nullable=False,
                                         server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("consumers", "is_nbfc")
