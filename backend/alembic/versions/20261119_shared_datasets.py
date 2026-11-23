"""Opt-in read access to selected libraries for authenticated members."""

import sqlalchemy as sa

from alembic import op

revision = "20261119_shared_datasets"
down_revision = "20261108_quick_login"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "access_datasets",
        sa.Column("shared_with_members", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade():
    op.drop_column("access_datasets", "shared_with_members")
