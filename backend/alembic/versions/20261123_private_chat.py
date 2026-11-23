"""Private account chat with durable messages and read receipts."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261123_private_chat"
down_revision = "20261122_metadata_search"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "chat_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "member_a",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "member_b",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("read_a", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("read_b", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("member_a", "member_b"),
        sa.CheckConstraint("member_a < member_b", name="ordered_members"),
    )
    op.create_index(
        "ix_chat_conversations_a_updated", "chat_conversations", ["member_a", "updated_at"]
    )
    op.create_index(
        "ix_chat_conversations_b_updated", "chat_conversations", ["member_b", "updated_at"]
    )
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sender_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("body", sa.Text(), server_default="", nullable=False),
        sa.Column("image_key", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("sender_id", "client_id"),
        sa.CheckConstraint("char_length(body) <= 4000", name="body_length"),
        sa.CheckConstraint("body <> '' OR image_key IS NOT NULL", name="content_required"),
    )
    op.create_index("ix_chat_messages_conversation_id", "chat_messages", ["conversation_id", "id"])


def downgrade():
    op.drop_table("chat_messages")
    op.drop_table("chat_conversations")
