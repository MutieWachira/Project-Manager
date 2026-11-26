"""enforce active primary project environments

Revision ID: 2026196a7c01
Revises: 329f5a783cf4
Create Date: 2026-11-25 12:05:24.417946

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2026196a7c01'
down_revision: Union[str, Sequence[str], None] = '329f5a783cf4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_check_constraint(
        "ck_project_environments_primary_requires_active",
        "project_environments",
        sa.text("NOT is_primary OR is_active"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "ck_project_environments_primary_requires_active",
        "project_environments",
        type_="check",
    )
