"""Account-authored comments with image scopes, cursor pagination and idempotent sends."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "20261123_image_comments"
down_revision = "20261123_profiles_favorites"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "image_comments",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "image_id",
            UUID(as_uuid=True),
            sa.ForeignKey("images.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("client_id", UUID(as_uuid=True), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("user_id", "client_id"),
        sa.CheckConstraint("char_length(btrim(body)) BETWEEN 1 AND 2000", name="body_length"),
    )
    op.create_index("ix_image_comments_image_id_id", "image_comments", ["image_id", "id"])


def downgrade():
    op.drop_table("image_comments")
