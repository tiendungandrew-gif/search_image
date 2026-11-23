from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ImageFavorite(Base):
    __tablename__ = "image_favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "image_id"),
        Index("ix_image_favorites_user_id_id", "user_id", "id"),
    )
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    image_id: Mapped[UUID] = mapped_column(ForeignKey("images.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
