"""Personal profiles, private avatar objects and permission-scoped image favorites."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "20261123_profiles_favorites"
down_revision = "20261123_private_chat"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("bio", sa.Text(), nullable=False, server_default=""))
    op.add_column("users", sa.Column("avatar_key", sa.Text(), nullable=True))
    op.create_table(
        "image_favorites",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "image_id",
            UUID(as_uuid=True),
            sa.ForeignKey("images.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("user_id", "image_id"),
    )
    op.create_index("ix_image_favorites_user_id_id", "image_favorites", ["user_id", "id"])


def downgrade():
    op.drop_table("image_favorites")
    op.drop_column("users", "avatar_key")
    op.drop_column("users", "bio")
