"""Authenticated private chat. All reads and writes enforce conversation membership."""

import asyncio
import io
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import case, func, select
from sqlalchemy.dialects.postgresql import insert
from starlette.datastructures import UploadFile

from app.core.access import Principal
from app.core.auth import require_read_access
from app.core.exceptions import AppError
from app.db.models.access import LoginThrottle, User
from app.db.models.chat import ChatMessage, Conversation
from app.schemas.chat import ReadMessages, StartConversation
from app.services.chat import (
    MAX_CHAT_IMAGE,
    conversation_for,
    message_snapshot,
    participant_clause,
    prepare_chat_image,
)


async def require_chat_account(
    request: Request,
    response: Response,
    principal: Annotated[Principal, Depends(require_read_access)],
):
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Cookie, Authorization"
    if principal.user_id is None or getattr(request.state.auth_user, "is_demo", False):
        raise AppError(403, "CHAT_ACCOUNT_REQUIRED", "Dùng tài khoản cá nhân để nhắn tin")
    return principal


router = APIRouter(prefix="/chat", tags=["Chat"], dependencies=[Depends(require_chat_account)])


def account_snapshot(user):
    from app.services.profiles import avatar_url

    return {
        "id": str(user.id),
        "username": user.username,
        "display_name": user.display_name,
        "avatar_url": avatar_url(user),
    }


async def chat_throttle(request):
    key = f"chat:{request.state.principal.user_id}"
    bucket = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M")
    async with request.app.state.services.database.sessions() as session, session.begin():
        query = insert(LoginThrottle).values(key=key, bucket=bucket, count=1)
        value = await session.scalar(
            query.on_conflict_do_update(
                index_elements=[LoginThrottle.key],
                set_={
                    "bucket": bucket,
                    "count": case(
                        (LoginThrottle.bucket != bucket, 1), else_=LoginThrottle.count + 1
                    ),
                },
                where=(LoginThrottle.bucket != bucket) | (LoginThrottle.count < 60),
            ).returning(LoginThrottle.count)
        )
    if value is None:
        raise AppError(429, "CHAT_RATE_LIMITED", "Bạn gửi quá nhanh. Vui lòng đợi một chút.")


@router.get("/users")
async def users(request: Request, q: Annotated[str, Query(max_length=120)] = ""):
    user_id = request.state.principal.user_id
    statement = select(User).where(
        User.id != user_id, User.is_active.is_(True), User.is_demo.is_(False)
    )
    if q.strip():
        # Literal substring: user input is never a LIKE wildcard.
        from sqlalchemy import or_

        statement = statement.where(
            or_(
                User.username.ilike(
                    "%"
                    + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                    + "%",
                    escape="\\",
                ),
                User.display_name.ilike(
                    "%"
                    + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                    + "%",
                    escape="\\",
                ),
            )
        )
    async with request.app.state.services.database.sessions() as session:
        rows = (
            await session.scalars(statement.order_by(User.display_name, User.id).limit(20))
        ).all()
    return {"users": [account_snapshot(user) for user in rows]}


@router.post("/conversations")
async def start(body: StartConversation, request: Request):
    own = request.state.principal.user_id
    if body.user_id == own:
        raise AppError(422, "CHAT_SELF", "Chọn người khác để bắt đầu trò chuyện")
    await chat_throttle(request)
    a, b = sorted([own, body.user_id])
    async with request.app.state.services.database.sessions() as session, session.begin():
        peer = await session.scalar(
            select(User).where(
                User.id == body.user_id, User.is_active.is_(True), User.is_demo.is_(False)
            )
        )
        if peer is None:
            raise AppError(404, "CHAT_USER_NOT_FOUND", "Tài khoản không khả dụng")
        query = insert(Conversation).values(member_a=a, member_b=b)
        conversation_id = await session.scalar(
            query.on_conflict_do_update(
                index_elements=[Conversation.member_a, Conversation.member_b],
                set_={"member_a": a},
            ).returning(Conversation.id)
        )
    return {"id": str(conversation_id), "peer": account_snapshot(peer)}


@router.get("/conversations")
async def conversations(request: Request):
    own = request.state.principal.user_id
    read_id = case((Conversation.member_a == own, Conversation.read_a), else_=Conversation.read_b)
    unread = (
        select(func.count())
        .where(
            ChatMessage.conversation_id == Conversation.id,
            ChatMessage.sender_id != own,
            ChatMessage.id > read_id,
        )
        .correlate(Conversation)
        .scalar_subquery()
    )
    last_id = (
        select(func.max(ChatMessage.id))
        .where(ChatMessage.conversation_id == Conversation.id)
        .correlate(Conversation)
        .scalar_subquery()
    )
    statement = (
        select(Conversation, User, ChatMessage, unread.label("unread"))
        .join(
            User,
            User.id
            == case(
                (Conversation.member_a == own, Conversation.member_b), else_=Conversation.member_a
            ),
        )
        .outerjoin(ChatMessage, ChatMessage.id == last_id)
        .where(participant_clause(own))
        .order_by(Conversation.updated_at.desc(), Conversation.id)
        .limit(100)
    )
    async with request.app.state.services.database.sessions() as session:
        rows = (await session.execute(statement)).all()
    return {
        "conversations": [
            {
                "id": str(conv.id),
                "peer": account_snapshot(peer),
                "unread": count,
                "last_message": message_snapshot(last) if last else None,
                "updated_at": conv.updated_at.isoformat(),
            }
            for conv, peer, last, count in rows
        ]
    }


@router.get("/conversations/{conversation_id}/messages")
async def messages(
    conversation_id: UUID,
    request: Request,
    before: Annotated[int | None, Query(ge=1, le=9223372036854775807)] = None,
    after: Annotated[int | None, Query(ge=0, le=9223372036854775807)] = None,
):
    if before is not None and after is not None:
        raise AppError(422, "INVALID_INPUT", "Chỉ dùng một mốc tin nhắn")
    async with request.app.state.services.database.sessions() as session:
        await conversation_for(session, conversation_id, request.state.principal.user_id)
        statement = select(ChatMessage).where(ChatMessage.conversation_id == conversation_id)
        if before is not None:
            statement = statement.where(ChatMessage.id < before)
        if after is not None:
            statement = statement.where(ChatMessage.id > after).order_by(ChatMessage.id)
        else:
            statement = statement.order_by(ChatMessage.id.desc())
        rows = list((await session.scalars(statement.limit(51))).all())
    more = len(rows) > 50
    rows = rows[:50]
    if after is None:
        rows.reverse()
    return {"messages": [message_snapshot(message) for message in rows], "has_more": more}


@router.post("/conversations/{conversation_id}/read")
async def mark_read(conversation_id: UUID, body: ReadMessages, request: Request):
    own = request.state.principal.user_id
    async with request.app.state.services.database.sessions() as session, session.begin():
        conv = await conversation_for(session, conversation_id, own, lock=True)
        message = await session.scalar(
            select(ChatMessage.id).where(
                ChatMessage.conversation_id == conversation_id, ChatMessage.id == body.message_id
            )
        )
        if message is None:
            raise AppError(404, "CHAT_MESSAGE_NOT_FOUND", "Không tìm thấy tin nhắn")
        field = "read_a" if conv.member_a == own else "read_b"
        setattr(conv, field, max(getattr(conv, field), message))
    return {"status": "read"}


@router.post("/conversations/{conversation_id}/messages", status_code=201)
async def send(conversation_id: UUID, request: Request):
    own = request.state.principal.user_id
    services = request.app.state.services
    # Authorize before receiving/decoding an attachment.
    async with services.database.sessions() as session:
        await conversation_for(session, conversation_id, own)
    await chat_throttle(request)
    async with request.form(max_files=1, max_fields=2, max_part_size=16384) as form:
        if not set(form).issubset({"body", "client_id", "image"}) or any(
            len(form.getlist(k)) != 1 for k in form
        ):
            raise AppError(422, "INVALID_INPUT", "Nội dung tin nhắn không hợp lệ")
        try:
            client_id = UUID(str(form.get("client_id", "")))
        except ValueError:
            raise AppError(422, "INVALID_INPUT", "Thiếu mã tin nhắn") from None
        body = form.get("body", "")
        if not isinstance(body, str) or len(body) > 4000:
            raise AppError(422, "INVALID_INPUT", "Tin nhắn tối đa 4000 ký tự")
        body = body.strip()
        upload = form.get("image")
        if upload is not None and not isinstance(upload, UploadFile):
            raise AppError(422, "INVALID_INPUT", "Tệp ảnh không hợp lệ")
        if not body and upload is None:
            raise AppError(422, "EMPTY_MESSAGE", "Nhập tin nhắn hoặc chọn ảnh")
        data = await upload.read(MAX_CHAT_IMAGE + 1) if upload else None
    encoded = await asyncio.to_thread(prepare_chat_image, data) if data is not None else None
    async with services.database.sessions() as session, session.begin():
        conv = await conversation_for(session, conversation_id, own, lock=True)
        existing = await session.scalar(
            select(ChatMessage).where(
                ChatMessage.sender_id == own, ChatMessage.client_id == client_id
            )
        )
        if existing:
            if existing.conversation_id != conversation_id:
                raise AppError(409, "CHAT_MESSAGE_CONFLICT", "Mã tin nhắn đã được sử dụng")
            return message_snapshot(existing)
        peer_id = conv.member_b if conv.member_a == own else conv.member_a
        if not await session.scalar(
            select(User.id).where(User.id == peer_id, User.is_active.is_(True))
        ):
            raise AppError(409, "CHAT_USER_UNAVAILABLE", "Người nhận hiện không khả dụng")
        key = f"chat/{conversation_id}/{own}/{client_id}.jpg" if encoded else None
        if encoded:
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
                    503,
                    "CHAT_UPLOAD_FAILED",
                    "Chưa gửi được ảnh. Vui lòng thử lại.",
                    retryable=True,
                ) from None
        message = ChatMessage(
            conversation_id=conversation_id,
            sender_id=own,
            client_id=client_id,
            body=body,
            image_key=key,
        )
        session.add(message)
        conv.updated_at = datetime.now(UTC)
        await session.flush()
        result = message_snapshot(message)
    return result


@router.get("/attachments/{message_id}")
async def attachment(message_id: int, request: Request):
    own = request.state.principal.user_id
    services = request.app.state.services
    async with services.database.sessions() as session:
        message = await session.scalar(
            select(ChatMessage)
            .join(Conversation, Conversation.id == ChatMessage.conversation_id)
            .where(
                ChatMessage.id == message_id,
                participant_clause(own),
                ChatMessage.image_key.is_not(None),
            )
        )
        if message is None:
            raise AppError(404, "CHAT_IMAGE_NOT_FOUND", "Không tìm thấy ảnh")
        key = message.image_key

    def read():
        response = services.minio.client.get_object(services.minio.bucket, key)
        try:
            return response.read(MAX_CHAT_IMAGE + 1)
        finally:
            response.close()
            response.release_conn()

    try:
        data = await services.minio.run(read)
        if len(data) > MAX_CHAT_IMAGE:
            raise ValueError("oversized")
    except Exception:
        raise AppError(503, "CHAT_IMAGE_UNAVAILABLE", "Chưa tải được ảnh", retryable=True) from None
    return Response(
        data,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "private, no-store",
            "Vary": "Cookie, Authorization",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": 'inline; filename="chat-image.jpg"',
        },
    )
