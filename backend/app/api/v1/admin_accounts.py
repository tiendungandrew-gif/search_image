"""Admin accounts, dataset grants and safe audit views."""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError

from app.core.auth import require_admin_access
from app.core.exceptions import AppError
from app.db.models import Image, ImageMetadata
from app.db.models.access import AccessDataset, AuditEvent, AuthSession, DatasetGrant, User
from app.schemas.access import (
    CreateUser,
    DatasetInput,
    DatasetUpdate,
    GrantInput,
    ResetPassword,
    UpdateUser,
)
from app.services.accounts import audit, make_password, public_user
from app.services.catalog import sync_catalog

router = APIRouter(
    prefix="/admin", tags=["Administration"], dependencies=[Depends(require_admin_access)]
)


@router.get("/users")
async def users(
    request: Request, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)
):
    async with request.app.state.services.database.sessions() as session:
        rows = list(
            (
                await session.scalars(
                    select(User).order_by(User.created_at, User.id).offset(offset).limit(limit)
                )
            ).all()
        )
        grants = (
            await session.execute(
                select(DatasetGrant.user_id, DatasetGrant.dataset_id).where(
                    DatasetGrant.user_id.in_([u.id for u in rows])
                )
            )
        ).all()
        total = await session.scalar(select(func.count()).select_from(User))
    return {
        "total": total,
        "users": [
            {**public_user(u), "dataset_ids": [str(d) for uid, d in grants if uid == u.id]}
            for u in rows
        ],
    }


@router.post("/users", status_code=201)
async def create_user(body: CreateUser, request: Request):
    encoded = await make_password(request, body.password.get_secret_value())
    try:
        async with request.app.state.services.database.sessions() as session, session.begin():
            user = User(
                id=uuid4(),
                username=body.username,
                display_name=body.display_name,
                password_hash=encoded,
                role=body.role,
                is_active=True,
            )
            session.add(user)
            await session.flush()
            audit(session, request.state.principal, "user.created", user.id, role=user.role)
        return public_user(user)
    except IntegrityError:
        raise AppError(409, "USERNAME_EXISTS", "Tên đăng nhập đã được sử dụng") from None


@router.patch("/users/{user_id}")
async def update_user(user_id: UUID, body: UpdateUser, request: Request):
    async with request.app.state.services.database.sessions() as session, session.begin():
        await session.execute(text("SELECT pg_advisory_xact_lock(731208122)"))
        user = await session.get(User, user_id, with_for_update=True)
        if user is None:
            raise AppError(404, "USER_NOT_FOUND", "Không tìm thấy tài khoản")
        values = body.model_dump(exclude_unset=True)
        if user.is_demo and "role" in values and values["role"] != user.role:
            raise AppError(409, "DEMO_ROLE_FIXED", "Vai trò tài khoản trải nghiệm được cố định")
        if any(v is None for v in values.values()):
            raise AppError(422, "INVALID_INPUT", "Giá trị tài khoản không hợp lệ")
        if (
            user.role == "admin"
            and not user.is_demo
            and user.is_active
            and (values.get("role", "admin") != "admin" or values.get("is_active") is False)
        ):
            admins = await session.scalar(
                select(func.count())
                .select_from(User)
                .where(User.role == "admin", User.is_active.is_(True), User.is_demo.is_(False))
            )
            if admins <= 1:
                raise AppError(
                    409, "LAST_ADMIN", "Phải giữ ít nhất một quản trị viên đang hoạt động"
                )
        for key, value in values.items():
            setattr(user, key, value)
        if "role" in values or values.get("is_active") is False:
            await session.execute(delete(AuthSession).where(AuthSession.user_id == user_id))
        audit(session, request.state.principal, "user.updated", user_id, fields=sorted(values))
    return public_user(user)


@router.post("/users/{user_id}/password")
async def reset_password(user_id: UUID, body: ResetPassword, request: Request):
    encoded = await make_password(request, body.password.get_secret_value())
    async with request.app.state.services.database.sessions() as session, session.begin():
        user = await session.get(User, user_id, with_for_update=True)
        if user is None:
            raise AppError(404, "USER_NOT_FOUND", "Không tìm thấy tài khoản")
        user.password_hash = encoded
        await session.execute(delete(AuthSession).where(AuthSession.user_id == user_id))
        audit(session, request.state.principal, "user.password_reset", user_id)
    return {"status": "password_reset_sessions_revoked"}


@router.post("/users/{user_id}/sessions/revoke")
async def revoke_sessions(user_id: UUID, request: Request):
    async with request.app.state.services.database.sessions() as session, session.begin():
        user = await session.get(User, user_id, with_for_update=True)
        if user is None:
            raise AppError(404, "USER_NOT_FOUND", "Không tìm thấy tài khoản")
        await session.execute(delete(AuthSession).where(AuthSession.user_id == user_id))
        audit(session, request.state.principal, "user.sessions_revoked", user_id)
    return {"status": "sessions_revoked"}


@router.put("/users/{user_id}/datasets")
async def grants(user_id: UUID, body: GrantInput, request: Request):
    ids = set(body.dataset_ids)
    async with request.app.state.services.database.sessions() as session, session.begin():
        user = await session.get(User, user_id, with_for_update=True)
        if user is None:
            raise AppError(404, "USER_NOT_FOUND", "Không tìm thấy tài khoản")
        found = set(
            (await session.scalars(select(AccessDataset.id).where(AccessDataset.id.in_(ids)))).all()
        )
        if found != ids:
            raise AppError(422, "DATASET_NOT_FOUND", "Dataset được chọn không tồn tại")
        await session.execute(delete(DatasetGrant).where(DatasetGrant.user_id == user_id))
        session.add_all(DatasetGrant(user_id=user_id, dataset_id=identity) for identity in ids)
        audit(
            session,
            request.state.principal,
            "user.datasets_changed",
            user_id,
            dataset_ids=sorted(map(str, ids)),
        )
    return {"status": "updated", "dataset_ids": sorted(map(str, ids))}


@router.get("/datasets")
async def datasets(request: Request):
    async with request.app.state.services.database.sessions() as session, session.begin():
        await sync_catalog(session)
        rows = list(
            (
                await session.scalars(
                    select(AccessDataset).order_by(AccessDataset.name).limit(1000)
                )
            ).all()
        )
        counts = dict(
            (
                await session.execute(
                    select(
                        func.coalesce(ImageMetadata.source_dataset, "__unassigned__"), func.count()
                    )
                    .select_from(Image)
                    .outerjoin(ImageMetadata, ImageMetadata.image_id == Image.id)
                    .where(Image.status.not_in(["deleted", "deleting"]))
                    .group_by(ImageMetadata.source_dataset)
                )
            ).all()
        )
    return {
        "datasets": [
            {
                "id": str(d.id),
                "key": d.key,
                "name": d.name,
                "description": d.description,
                "is_active": d.is_active,
                "shared_with_members": d.shared_with_members,
                "is_public": d.is_public,
                "images": counts.get(d.key, 0),
            }
            for d in rows
        ]
    }


@router.post("/datasets", status_code=201)
async def create_dataset(body: DatasetInput, request: Request):
    try:
        async with request.app.state.services.database.sessions() as session, session.begin():
            value = AccessDataset(id=uuid4(), **body.model_dump(), is_active=True)
            session.add(value)
            await session.flush()
            audit(session, request.state.principal, "dataset.created", value.id)
        return {"id": str(value.id), **body.model_dump(), "is_active": True, "images": 0}
    except IntegrityError:
        raise AppError(409, "DATASET_EXISTS", "Mã dataset đã tồn tại") from None


@router.patch("/datasets/{dataset_id}")
async def update_dataset(dataset_id: UUID, body: DatasetUpdate, request: Request):
    async with request.app.state.services.database.sessions() as session, session.begin():
        value = await session.get(AccessDataset, dataset_id, with_for_update=True)
        if value is None:
            raise AppError(404, "DATASET_NOT_FOUND", "Không tìm thấy dataset")
        for key, field in body.model_dump(exclude_unset=True).items():
            setattr(value, key, field)
        audit(
            session,
            request.state.principal,
            "dataset.updated",
            dataset_id,
            shared_with_members=value.shared_with_members,
            is_public=value.is_public,
            is_active=value.is_active,
        )
    return {"status": "updated"}


@router.get("/audit")
async def audit_events(
    request: Request, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)
):
    async with request.app.state.services.database.sessions() as session:
        rows = (
            await session.execute(
                select(AuditEvent, User.username)
                .outerjoin(User, User.id == AuditEvent.actor_id)
                .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
                .offset(offset)
                .limit(limit)
            )
        ).all()
    return {
        "events": [
            {
                "id": str(e.id),
                "actor": username or "operator",
                "action": e.action,
                "resource_id": e.resource_id,
                "details": e.details,
                "created_at": e.created_at.isoformat(),
            }
            for e, username in rows
        ]
    }
