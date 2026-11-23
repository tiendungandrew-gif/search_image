"""Request-local access scope shared by HTTP, retrieval, evidence and Agent tools."""

from contextvars import ContextVar
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import exists, false, or_, select, true

from app.db.models import ImageMetadata
from app.db.models.access import EntityDataset, ImageModeration, RelationDataset

UNASSIGNED = "__unassigned__"


@dataclass(frozen=True)
class Principal:
    user_id: UUID | None
    username: str
    role: str
    dataset_ids: tuple[UUID, ...] = ()
    dataset_keys: tuple[str, ...] = ()

    @property
    def is_admin(self):
        return self.role in {"admin", "service_write"}

    @property
    def unrestricted(self):
        return self.role in {"admin", "service_read", "service_write"}


current_principal: ContextVar[Principal | None] = ContextVar("lens_principal", default=None)


class AccessContextMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        token = current_principal.set(None)
        try:
            await self.app(scope, receive, send)
        finally:
            current_principal.reset(token)


def restricted():
    principal = current_principal.get()
    return principal is not None and not principal.unrestricted


def source_clause(column=ImageMetadata.source_dataset):
    principal = current_principal.get()
    if principal is None or principal.unrestricted:
        return true()
    keys = [key for key in principal.dataset_keys if key != UNASSIGNED]
    clauses = [column.in_(keys)] if keys else []
    if UNASSIGNED in principal.dataset_keys:
        clauses.append(column.is_(None))
    return or_(*clauses) if clauses else false()


def visible_image_clause(image_id):
    return ~exists(
        select(ImageModeration.image_id).where(
            ImageModeration.image_id == image_id, ImageModeration.hidden.is_(True)
        )
    )


def entity_clause(entity_id):
    principal = current_principal.get()
    if principal is None or principal.unrestricted:
        return true()
    return exists(
        select(EntityDataset.entity_id).where(
            EntityDataset.entity_id == entity_id,
            EntityDataset.dataset_id.in_(principal.dataset_ids),
        )
    )


def relation_clause(relation_id):
    principal = current_principal.get()
    if principal is None or principal.unrestricted:
        return true()
    return exists(
        select(RelationDataset.relation_id).where(
            RelationDataset.relation_id == relation_id,
            RelationDataset.dataset_id.in_(principal.dataset_ids),
        )
    )


def source_allowed(key):
    principal = current_principal.get()
    return (
        principal is None
        or principal.unrestricted
        or (key if key is not None else UNASSIGNED) in principal.dataset_keys
    )
