"""Baseline migration placeholder to satisfy revision history

Revision ID: 839dce997838
Revises: 
Create Date: 2024-09-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '839dce997838'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Existing production schema already matches this baseline."""
    pass


def downgrade() -> None:
    """Downgrade is not supported for the baseline."""
    pass
