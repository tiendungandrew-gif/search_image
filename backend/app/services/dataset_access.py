"""One live policy for account snapshots and request-local dataset scopes."""

from sqlalchemy import exists, or_, select

from app.db.models.access import AccessDataset, DatasetGrant


def accessible_datasets(user):
    statement = select(AccessDataset).where(AccessDataset.is_active.is_(True))
    if user.role != "admin":
        assigned = exists(
            select(DatasetGrant.user_id).where(
                DatasetGrant.user_id == user.id, DatasetGrant.dataset_id == AccessDataset.id
            )
        )
        statement = statement.where(
            or_(
                AccessDataset.is_public.is_(True),
                AccessDataset.shared_with_members.is_(True),
                assigned,
            )
        )
    return statement.order_by(AccessDataset.name, AccessDataset.id)


def public_datasets():
    return (
        select(AccessDataset)
        .where(AccessDataset.is_active.is_(True), AccessDataset.is_public.is_(True))
        .order_by(AccessDataset.name, AccessDataset.id)
    )
