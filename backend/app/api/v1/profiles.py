import asyncio
import io
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import Field
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from starlette.datastructures import UploadFile

from app.core.access import Principal
from app.core.auth import require_read_access
from app.core.exceptions import AppError
from app.db.models import Image
from app.db.models.access import User
from app.db.models.profile import ImageFavorite
from app.schemas.access import StrictInput
from app.schemas.search import SearchResult
from app.services.accounts import user_snapshot
from app.services.profiles import eligible_images, prepare_avatar


async def personal_account(
    request: Request,
    response: Response,
    principal: Annotated[Principal, Depends(require_read_access)],
):
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Cookie, Authorization"
    if principal.user_id is None or request.state.auth_user.is_demo:
        raise AppError(
            403, "PERSONAL_ACCOUNT_REQUIRED", "Dùng tài khoản cá nhân để sử dụng tính năng này"
        )
    return principal


router = APIRouter(tags=["Profiles"])
private = APIRouter(prefix="/profile", dependencies=[Depends(personal_account)])


class ProfileUpdate(StrictInput):
    display_name: str = Field(min_length=1, max_length=120)
    bio: str = Field(default="", max_length=500)


async def profile_snapshot(request, user):
    services = request.app.state.services
    statement = (
        eligible_images()
        .join(ImageFavorite, ImageFavorite.image_id == Image.id)
        .where(ImageFavorite.user_id == user.id)
    )
    async with services.database.sessions() as session:
        count = await session.scalar(select(func.count()).select_from(statement.subquery()))
    return {
        "user": await user_snapshot(services, user),
        "bio": user.bio,
        "created_at": user.created_at.isoformat(),
        "favorite_count": count,
    }


@private.get("")
async def me(request: Request):
    return await profile_snapshot(request, request.state.auth_user)


@private.patch("")
async def update(body: ProfileUpdate, request: Request):
    async with request.app.state.services.database.sessions() as session, session.begin():
        user = await session.get(User, request.state.principal.user_id, with_for_update=True)
        user.display_name = body.display_name
        user.bio = body.bio.strip()
    return await profile_snapshot(request, user)


@private.post("/avatar")
async def upload_avatar(request: Request):
    async with request.form(max_files=1, max_fields=0) as form:
        upload = form.get("image")
        if (
            set(form) != {"image"}
            or len(form.getlist("image")) != 1
            or not isinstance(upload, UploadFile)
        ):
            raise AppError(422, "INVALID_INPUT", "Chọn một ảnh đại diện")
        data = await upload.read(5 * 1024**2 + 1)
    if len(data) > 5 * 1024**2:
        raise AppError(413, "AVATAR_TOO_LARGE", "Ảnh đại diện tối đa 5 MB")
    encoded = await asyncio.to_thread(prepare_avatar, data)
    services = request.app.state.services
    own = request.state.principal.user_id
    key = f"avatars/{own}/{uuid4().hex}.jpg"
    try:
        await services.minio.run(
            lambda: services.minio.client.put_object(
                services.minio.bucket,
                key,
                io.BytesIO(encoded),
                len(encoded),
                content_type="image/jpeg",
            )
        )
    except Exception:
        raise AppError(
            503, "AVATAR_UPLOAD_FAILED", "Chưa cập nhật được ảnh đại diện", retryable=True
        ) from None
    async with services.database.sessions() as session, session.begin():
        user = await session.get(User, own, with_for_update=True)
        previous_key = user.avatar_key
        user.avatar_key = key
    if previous_key:
        try:
            await services.minio.run(
                lambda: services.minio.client.remove_object(services.minio.bucket, previous_key)
            )
        except Exception:
            pass  # The committed new avatar remains usable if old-object cleanup is unavailable.
    return await profile_snapshot(request, user)


@router.get("/profiles/{user_id}/avatar", dependencies=[Depends(require_read_access)])
async def avatar(user_id: UUID, request: Request):
    if request.state.principal.user_id is None:
        raise AppError(403, "PERSONAL_ACCOUNT_REQUIRED", "Vui lòng đăng nhập")
    services = request.app.state.services
    async with services.database.sessions() as session:
        user = await session.scalar(
            select(User).where(User.id == user_id, User.is_active.is_(True))
        )
        if user is None or not user.avatar_key:
            raise AppError(404, "AVATAR_NOT_FOUND", "Chưa có ảnh đại diện")
        key = user.avatar_key

    def read():
        response = services.minio.client.get_object(services.minio.bucket, key)
        try:
            return response.read(1024**2)
        finally:
            response.close()
            response.release_conn()

    try:
        data = await services.minio.run(read)
    except Exception:
        raise AppError(
            503, "AVATAR_UNAVAILABLE", "Chưa tải được ảnh đại diện", retryable=True
        ) from None
    return Response(
        data,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "private, no-store",
            "Vary": "Cookie, Authorization",
            "X-Content-Type-Options": "nosniff",
        },
    )


@private.get("/favorites/status")
async def favorites_status(request: Request, ids: Annotated[list[UUID], Query(max_length=50)]):
    statement = (
        eligible_images()
        .join(ImageFavorite, ImageFavorite.image_id == Image.id)
        .where(ImageFavorite.user_id == request.state.principal.user_id, Image.id.in_(ids))
    )
    async with request.app.state.services.database.sessions() as session:
        rows = (await session.scalars(statement.with_only_columns(Image.id))).all()
    return {"ids": [str(image_id) for image_id in rows]}


@private.put("/favorites/{image_id}")
async def save_favorite(image_id: UUID, request: Request):
    async with request.app.state.services.database.sessions() as session, session.begin():
        if (
            await session.scalar(
                eligible_images().where(Image.id == image_id).with_only_columns(Image.id)
            )
            is None
        ):
            raise AppError(404, "IMAGE_NOT_FOUND", "Không tìm thấy ảnh")
        await session.execute(
            insert(ImageFavorite)
            .values(user_id=request.state.principal.user_id, image_id=image_id)
            .on_conflict_do_nothing(index_elements=[ImageFavorite.user_id, ImageFavorite.image_id])
        )
    return {"saved": True}


@private.delete("/favorites/{image_id}")
async def remove_favorite(image_id: UUID, request: Request):
    async with request.app.state.services.database.sessions() as session, session.begin():
        await session.execute(
            delete(ImageFavorite).where(
                ImageFavorite.user_id == request.state.principal.user_id,
                ImageFavorite.image_id == image_id,
            )
        )
    return {"saved": False}


@private.get("/favorites")
async def favorites(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=50)] = 24,
    before: Annotated[int | None, Query(ge=1, le=9223372036854775807)] = None,
):
    statement = (
        eligible_images()
        .join(ImageFavorite, ImageFavorite.image_id == Image.id)
        .where(ImageFavorite.user_id == request.state.principal.user_id)
    )
    async with request.app.state.services.database.sessions() as session:
        total = await session.scalar(select(func.count()).select_from(statement.subquery()))
        if before is not None:
            statement = statement.where(ImageFavorite.id < before)
        rows = (
            await session.execute(
                statement.add_columns(ImageFavorite.id)
                .order_by(ImageFavorite.id.desc())
                .limit(limit + 1)
            )
        ).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    results = []
    for rank, (image, meta, _) in enumerate(rows, 1):
        url = f"/api/v1/images/{image.id}/content"
        results.append(
            SearchResult(
                image_id=image.id,
                rank=rank,
                score=0,
                image_url=url + "?variant=original",
                thumbnail_url=url + "?variant=thumbnail",
                metadata={
                    "title": meta.title if meta else None,
                    "caption": meta.caption if meta else None,
                    "width": image.width,
                    "height": image.height,
                    "media_type": image.media_type,
                    "tags": [],
                    "source_dataset": meta.source_dataset if meta else None,
                    "city": meta.city if meta else None,
                    "license": meta.license if meta else None,
                },
            )
        )
    return {
        "results": results,
        "total_results": len(results),
        "total_saved": total,
        "has_more": has_more,
        "next_cursor": str(rows[-1][2]) if has_more else None,
    }


router.include_router(private)
