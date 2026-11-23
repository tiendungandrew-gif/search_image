"""Explicit public library access, opt-in and separate from membership."""

import sqlalchemy as sa

from alembic import op

revision = "20261120_public_datasets"
down_revision = "20261119_shared_datasets"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "access_datasets",
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade():
    op.drop_column("access_datasets", "is_public")
