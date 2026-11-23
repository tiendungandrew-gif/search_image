from datetime import datetime
from uuid import UUID

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


class ImageComment(Base):
    __tablename__ = "image_comments"
    __table_args__ = (
        UniqueConstraint("user_id", "client_id"),
        CheckConstraint("char_length(btrim(body)) BETWEEN 1 AND 2000", name="body_length"),
        Index("ix_image_comments_image_id_id", "image_id", "id"),
    )
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    image_id: Mapped[UUID] = mapped_column(ForeignKey("images.id", ondelete="CASCADE"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    client_id: Mapped[UUID] = mapped_column()
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
