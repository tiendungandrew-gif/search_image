"""Mark explicitly provisioned demo accounts; existing accounts remain ordinary."""

import sqlalchemy as sa

from alembic import op

revision = "20261108_quick_login"
down_revision = "20261108_access_control"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users", sa.Column("is_demo", sa.Boolean(), nullable=False, server_default="false")
    )
    op.create_index(
        "uq_users_demo_role", "users", ["role"], unique=True, postgresql_where=sa.text("is_demo")
    )


def downgrade():
    op.drop_index("uq_users_demo_role", table_name="users")
    op.drop_column("users", "is_demo")
