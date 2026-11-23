"""Accounts, revocable sessions and dataset-scoped application permissions."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('user','admin')", name="role"),
        Index("uq_users_demo_role", "role", unique=True, postgresql_where=text("is_demo")),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(Text, unique=True)
    display_name: Mapped[str] = mapped_column(Text)
    bio: Mapped[str] = mapped_column(Text, default="", server_default="")
    avatar_key: Mapped[str | None] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(default=False, server_default="false")
    role: Mapped[str] = mapped_column(Text, default="user", server_default="user")
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    token_hash: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    csrf_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class AccessDataset(Base):
    __tablename__ = "access_datasets"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    key: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")
    shared_with_members: Mapped[bool] = mapped_column(default=False, server_default="false")
    is_public: Mapped[bool] = mapped_column(default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DatasetGrant(Base):
    __tablename__ = "dataset_grants"
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    dataset_id: Mapped[UUID] = mapped_column(
        ForeignKey("access_datasets.id", ondelete="CASCADE"), primary_key=True
    )


class EntityDataset(Base):
    __tablename__ = "entity_datasets"
    dataset_id: Mapped[UUID] = mapped_column(
        ForeignKey("access_datasets.id", ondelete="CASCADE"), primary_key=True
    )
    entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True
    )


class RelationDataset(Base):
    __tablename__ = "relation_datasets"
    dataset_id: Mapped[UUID] = mapped_column(
        ForeignKey("access_datasets.id", ondelete="CASCADE"), primary_key=True
    )
    relation_id: Mapped[UUID] = mapped_column(
        ForeignKey("entity_relationships.id", ondelete="CASCADE"), primary_key=True
    )


class ImageModeration(Base):
    __tablename__ = "image_moderation"
    image_id: Mapped[UUID] = mapped_column(
        ForeignKey("images.id", ondelete="CASCADE"), primary_key=True
    )
    hidden: Mapped[bool] = mapped_column(default=False, server_default="false")


class AuthUsage(Base):
    __tablename__ = "auth_usage"
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    kind: Mapped[str] = mapped_column(Text, primary_key=True)
    bucket: Mapped[str] = mapped_column(Text, primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class LoginThrottle(Base):
    __tablename__ = "login_throttles"
    key: Mapped[str] = mapped_column(Text, primary_key=True)
    bucket: Mapped[str] = mapped_column(Text)
    count: Mapped[int] = mapped_column(Integer)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_events_created_id", "created_at", "id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(Text)
    resource_id: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
