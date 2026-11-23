from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request
from pydantic import Field, field_validator
from sqlalchemy import case, delete, func, select
from sqlalchemy.dialects.postgresql import insert

from app.api.v1.profiles import personal_account
from app.core.exceptions import AppError
from app.core.guest import require_search_access
from app.db.models import Image
from app.db.models.access import LoginThrottle, User
from app.db.models.comments import ImageComment
from app.schemas.access import StrictInput
from app.services.profiles import avatar_url, eligible_images

router = APIRouter(prefix="/images", tags=["Comments"])


class CommentInput(StrictInput):
    body: str = Field(min_length=1, max_length=2000)
    client_id: UUID

    @field_validator("body")
    @classmethod
    def nonempty_body(cls, value):
        if not value.strip():
            raise ValueError("empty_comment")
        return value.strip()


async def require_visible_image(session, image_id):
    if (
        await session.scalar(
            eligible_images().where(Image.id == image_id).with_only_columns(Image.id)
        )
        is None
    ):
        raise AppError(404, "IMAGE_NOT_FOUND", "Không tìm thấy ảnh")


def snapshot(comment, author, principal):
    return {
        "id": str(comment.id),
        "body": comment.body,
        "created_at": comment.created_at.isoformat(),
        "author": {
            "id": str(author.id),
            "display_name": author.display_name,
            "avatar_url": avatar_url(author) if principal.user_id else None,
        },
        "can_delete": bool(
            principal.user_id and (principal.user_id == comment.user_id or principal.is_admin)
        ),
    }


async def throttle(request):
    bucket = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M")
    async with request.app.state.services.database.sessions() as session, session.begin():
        query = insert(LoginThrottle).values(
            key=f"comments:{request.state.principal.user_id}", bucket=bucket, count=1
        )
        result = await session.scalar(
            query.on_conflict_do_update(
                index_elements=[LoginThrottle.key],
                set_={
                    "bucket": bucket,
                    "count": case(
                        (LoginThrottle.bucket != bucket, 1), else_=LoginThrottle.count + 1
                    ),
                },
                where=(LoginThrottle.bucket != bucket) | (LoginThrottle.count < 30),
            ).returning(LoginThrottle.count)
        )
    if result is None:
        raise AppError(
            429, "COMMENT_RATE_LIMITED", "Bạn gửi bình luận quá nhanh. Vui lòng đợi một chút."
        )


@router.get("/{image_id}/comments", dependencies=[Depends(require_search_access)])
async def comments(
    image_id: UUID,
    request: Request,
    before: Annotated[int | None, Query(ge=1, le=9223372036854775807)] = None,
):
    async with request.app.state.services.database.sessions() as session:
        await require_visible_image(session, image_id)
        total = await session.scalar(
            select(func.count()).select_from(ImageComment).where(ImageComment.image_id == image_id)
        )
        statement = (
            select(ImageComment, User)
            .join(User, User.id == ImageComment.user_id)
            .where(ImageComment.image_id == image_id)
        )
        if before is not None:
            statement = statement.where(ImageComment.id < before)
        rows = (await session.execute(statement.order_by(ImageComment.id.desc()).limit(21))).all()
    more = len(rows) > 20
    rows = rows[:20]
    return {
        "comments": [
            snapshot(comment, author, request.state.principal) for comment, author in rows
        ],
        "total": total,
        "has_more": more,
        "next_cursor": str(rows[-1][0].id) if more else None,
    }


@router.post("/{image_id}/comments", dependencies=[Depends(personal_account)], status_code=201)
async def add_comment(image_id: UUID, body: CommentInput, request: Request):
    own = request.state.principal.user_id
    async with request.app.state.services.database.sessions() as session:
        await require_visible_image(session, image_id)
    await throttle(request)
    async with request.app.state.services.database.sessions() as session, session.begin():
        # Check again in the write transaction, so all write paths share image eligibility.
        await require_visible_image(session, image_id)
        query = insert(ImageComment).values(
            image_id=image_id, user_id=own, client_id=body.client_id, body=body.body
        )
        comment = await session.scalar(
            query.on_conflict_do_nothing(
                index_elements=[ImageComment.user_id, ImageComment.client_id]
            ).returning(ImageComment)
        )
        if comment is None:
            comment = await session.scalar(
                select(ImageComment).where(
                    ImageComment.user_id == own, ImageComment.client_id == body.client_id
                )
            )
            if comment.image_id != image_id or comment.body != body.body:
                raise AppError(409, "COMMENT_CONFLICT", "Bình luận đã thay đổi. Vui lòng gửi lại.")
    return snapshot(comment, request.state.auth_user, request.state.principal)


@router.delete("/{image_id}/comments/{comment_id}", dependencies=[Depends(personal_account)])
async def remove_comment(
    image_id: UUID,
    comment_id: Annotated[int, Path(ge=1, le=9223372036854775807)],
    request: Request,
):
    async with request.app.state.services.database.sessions() as session, session.begin():
        await require_visible_image(session, image_id)
        statement = delete(ImageComment).where(
            ImageComment.id == comment_id, ImageComment.image_id == image_id
        )
        if not request.state.principal.is_admin:
            statement = statement.where(ImageComment.user_id == request.state.principal.user_id)
        removed = await session.scalar(statement.returning(ImageComment.id))
        if removed is None:
            raise AppError(404, "COMMENT_NOT_FOUND", "Không tìm thấy bình luận có thể xóa")
    return {"status": "deleted"}
