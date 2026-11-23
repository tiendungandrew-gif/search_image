"""Private two-person conversations; attachments never enter the image search corpus."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Conversation(Base):
    __tablename__ = "chat_conversations"
    __table_args__ = (
        UniqueConstraint("member_a", "member_b"),
        CheckConstraint("member_a < member_b", name="ordered_members"),
        Index("ix_chat_conversations_a_updated", "member_a", "updated_at"),
        Index("ix_chat_conversations_b_updated", "member_b", "updated_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    member_a: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    member_b: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    read_a: Mapped[int] = mapped_column(BigInteger, server_default="0")
    read_b: Mapped[int] = mapped_column(BigInteger, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        UniqueConstraint("sender_id", "client_id"),
        CheckConstraint("char_length(body) <= 4000", name="body_length"),
        CheckConstraint("body <> '' OR image_key IS NOT NULL", name="content_required"),
        Index("ix_chat_messages_conversation_id", "conversation_id", "id"),
    )
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("chat_conversations.id", ondelete="CASCADE")
    )
    sender_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    client_id: Mapped[UUID] = mapped_column()
    body: Mapped[str] = mapped_column(Text, server_default="")
    image_key: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
