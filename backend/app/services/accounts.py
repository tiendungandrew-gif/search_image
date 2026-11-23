"""Session lifecycle and account operations; secrets never appear in response DTOs."""

import asyncio
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import case, delete, select
from sqlalchemy.dialects.postgresql import insert

from app.core.auth import cookie_names, secret_digest
from app.core.exceptions import AppError
from app.core.passwords import hash_password, verify_password
from app.db.models.access import (
    AuditEvent,
    AuthSession,
    LoginThrottle,
    User,
)
from app.services.dataset_access import accessible_datasets


def audit(session, principal, action, resource_id=None, **details):
    session.add(
        AuditEvent(
            id=uuid4(),
            actor_id=principal.user_id if principal else None,
            action=action,
            resource_id=str(resource_id) if resource_id is not None else None,
            details=details,
        )
    )


def public_user(user):
    from app.services.profiles import avatar_url

    return {
        "id": str(user.id),
        "username": user.username,
        "display_name": user.display_name,
        "avatar_url": avatar_url(user),
        "role": user.role,
        "is_active": user.is_active,
        "is_demo": user.is_demo,
    }


async def user_snapshot(services, user):
    async with services.database.sessions() as session:
        datasets = list((await session.scalars(accessible_datasets(user))).all())
    return {
        **public_user(user),
        "datasets": [
            {
                "id": str(d.id),
                "key": d.key,
                "name": d.name,
                "shared_with_members": d.shared_with_members,
                "is_public": d.is_public,
            }
            for d in datasets
        ],
    }


async def password_work(request, function, *args):
    slots = request.app.state.password_slots
    try:
        await asyncio.wait_for(slots.acquire(), timeout=0.1)
    except TimeoutError:
        raise AppError(429, "AUTH_BUSY", "Đăng nhập đang bận; vui lòng thử lại") from None
    task = asyncio.create_task(asyncio.to_thread(function, *args))

    def finished(value):
        slots.release()
        if not value.cancelled():
            value.exception()

    task.add_done_callback(finished)
    return await asyncio.shield(task)


async def throttle_login(request, username):
    bucket = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M")
    ip = request.client.host if request.client else "unknown"
    limit = request.app.state.settings.auth_login_attempts_per_minute
    accepted = True
    async with request.app.state.services.database.sessions() as session, session.begin():
        for key, cap in [("ip:" + ip, limit * 3), ("user:" + username, limit)]:
            query = insert(LoginThrottle).values(key=secret_digest(key), bucket=bucket, count=1)
            value = await session.scalar(
                query.on_conflict_do_update(
                    index_elements=[LoginThrottle.key],
                    set_={
                        "bucket": bucket,
                        "count": case(
                            (LoginThrottle.bucket != bucket, 1), else_=LoginThrottle.count + 1
                        ),
                    },
                    where=(LoginThrottle.bucket != bucket) | (LoginThrottle.count < cap),
                ).returning(LoginThrottle.count)
            )
            accepted &= value is not None
    if not accepted:
        raise AppError(
            429, "LOGIN_RATE_LIMITED", "Quá nhiều lần đăng nhập; vui lòng thử lại sau một phút"
        )


def set_cookies(response, settings, session_token, csrf):
    session_name, csrf_name = cookie_names(settings)
    common = {
        "secure": settings.auth_cookie_secure,
        "samesite": "strict",
        "path": "/",
        "max_age": settings.auth_session_hours * 3600,
    }
    response.set_cookie(session_name, session_token, httponly=True, **common)
    response.set_cookie(csrf_name, csrf, httponly=False, **common)
    response.headers["Cache-Control"] = "no-store"


def clear_cookies(response, settings):
    for name in cookie_names(settings):
        response.delete_cookie(
            name, path="/", secure=settings.auth_cookie_secure, samesite="strict"
        )
    response.headers["Cache-Control"] = "no-store"


async def issue_session(services, user, *, quick_role=None):
    token, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    async with services.database.sessions() as session, session.begin():
        locked = await session.get(User, user.id, with_for_update=True)
        if not locked or not locked.is_active or locked.password_hash != user.password_hash:
            raise AppError(401, "LOGIN_FAILED", "Tên đăng nhập hoặc mật khẩu không đúng")
        if quick_role is not None and (not locked.is_demo or locked.role != quick_role):
            raise AppError(401, "LOGIN_FAILED", "Tài khoản trải nghiệm không còn khả dụng")
        user.role, user.display_name = locked.role, locked.display_name
        # Fresh login always creates new IDs; expired rows never authenticate.
        await session.execute(
            delete(AuthSession).where(
                AuthSession.user_id == user.id, AuthSession.expires_at <= datetime.now(UTC)
            )
        )
        session.add(
            AuthSession(
                token_hash=secret_digest(token),
                csrf_hash=secret_digest(csrf),
                user_id=user.id,
                expires_at=datetime.now(UTC)
                + timedelta(hours=services.settings.auth_session_hours),
            )
        )
        session.add(
            AuditEvent(
                id=uuid4(),
                actor_id=user.id,
                action="auth.quick_login" if quick_role else "auth.login",
                details={},
            )
        )
    return token, csrf


def dummy_password_hash():
    return f"scrypt${2**17}$8$1$" + "0" * 32 + "$" + "0" * 64


async def check_password(request, password, encoded):
    return await password_work(request, verify_password, password, encoded)


async def make_password(request, password):
    return await password_work(request, hash_password, password)


async def quick_login_roles(services):
    from app.core.quick_login import DEMO_ACCOUNTS, quick_login_enabled

    if not quick_login_enabled(services.settings):
        return []
    async with services.database.sessions() as session:
        rows = (
            await session.scalars(
                select(User).where(User.is_demo.is_(True), User.is_active.is_(True))
            )
        ).all()
    return [
        role
        for role, (username, _) in DEMO_ACCOUNTS.items()
        if any(u.role == role and u.username == username for u in rows)
    ]
