"""Account sessions and explicit operator-token compatibility; deny by default."""

import hashlib
import secrets
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from app.core.access import Principal, current_principal
from app.core.exceptions import AppError
from app.core.quick_login import quick_login_enabled
from app.db.models.access import AuthSession, AuthUsage, User
from app.services.dataset_access import accessible_datasets

bearer = HTTPBearer(auto_error=False)


def secret_digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def cookie_names(settings):
    prefix = "__Host-" if settings.auth_cookie_secure else ""
    return prefix + "lens_session", prefix + "lens_csrf"


def check_origin(request):
    origin = request.headers.get("origin")
    if (
        origin not in request.app.state.settings.cors_origins
        or request.headers.get("sec-fetch-site") == "cross-site"
    ):
        raise AppError(403, "CSRF_REJECTED", "Nguồn yêu cầu không được phép")


async def resolve_identity(request, credentials=None, *, optional=False):
    cached = getattr(request.state, "principal", None)
    if cached is not None:
        current_principal.set(cached)
        return cached
    settings = request.app.state.settings
    if credentials is not None:
        if settings.auth_legacy_tokens_enabled:
            for expected, role in [
                (settings.write_api_token, "service_write"),
                (settings.api_token, "service_read"),
            ]:
                if expected and secrets.compare_digest(
                    credentials.credentials.encode(), expected.get_secret_value().encode()
                ):
                    value = Principal(None, "operator", role)
                    request.state.principal = value
                    current_principal.set(value)
                    return value
        raise AppError(401, "UNAUTHENTICATED", "Thông tin xác thực không hợp lệ")
    session_name, _ = cookie_names(settings)
    raw = request.cookies.get(session_name, "")
    if len(raw) > 200:
        raw = ""
    identity = None
    if raw:
        try:
            async with request.app.state.services.database.sessions() as session:
                row = (
                    await session.execute(
                        select(AuthSession, User)
                        .join(User, User.id == AuthSession.user_id)
                        .where(
                            AuthSession.token_hash == secret_digest(raw),
                            AuthSession.expires_at > datetime.now(UTC),
                            User.is_active.is_(True),
                            (User.is_demo.is_(False) | quick_login_enabled(settings)),
                        )
                    )
                ).first()
                if row:
                    auth_session, user = row
                    datasets = (
                        list((await session.scalars(accessible_datasets(user))).all())
                        if user.role != "admin"
                        else []
                    )
                    identity = Principal(
                        user.id,
                        user.username,
                        user.role,
                        tuple(d.id for d in datasets),
                        tuple(d.key for d in datasets),
                    )
                    request.state.auth_session = auth_session
                    request.state.auth_user = user
        except SQLAlchemyError:
            raise AppError(
                503, "AUTH_NOT_READY", "Dịch vụ đăng nhập chưa sẵn sàng", retryable=True
            ) from None
    if identity is None:
        if optional:
            return None
        raise AppError(401, "UNAUTHENTICATED", "Vui lòng đăng nhập để tiếp tục")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        check_origin(request)
        csrf = request.headers.get("x-csrf-token", "")
        if not csrf or not secrets.compare_digest(
            secret_digest(csrf), request.state.auth_session.csrf_hash
        ):
            raise AppError(403, "CSRF_REJECTED", "Phiên bảo mật không hợp lệ; tải lại trang")
    request.state.principal = identity
    current_principal.set(identity)
    return identity


async def require_read_access(
    request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
):
    return await resolve_identity(request, credentials)


async def require_write_access(principal: Annotated[Principal, Depends(require_read_access)]):
    if not principal.is_admin:
        raise AppError(403, "FORBIDDEN", "Chức năng chỉ dành cho quản trị viên")
    return principal


require_admin_access = require_write_access


async def require_diagnostics_access(principal: Annotated[Principal, Depends(require_read_access)]):
    if not principal.unrestricted:
        raise AppError(403, "FORBIDDEN", "Chẩn đoán hệ thống chỉ dành cho quản trị viên")
    return principal


async def require_operator_probe(
    request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
):
    """Existing service secrets are scoped to health probes even when legacy data access is off."""
    settings = request.app.state.settings
    if credentials is not None and any(
        expected
        and secrets.compare_digest(
            credentials.credentials.encode(), expected.get_secret_value().encode()
        )
        for expected in [settings.api_token, settings.write_api_token]
    ):
        return
    principal = await resolve_identity(request, credentials)
    await require_diagnostics_access(principal)


async def charge_usage(request, kind):
    principal = getattr(request.state, "principal", None)
    if principal is None or principal.unrestricted:
        return
    settings = request.app.state.settings
    limit = getattr(
        settings,
        {
            "search": "user_search_per_minute",
            "rag": "user_rag_per_day",
            "agent": "user_agent_per_day",
        }[kind],
    )
    bucket = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M" if kind == "search" else "%Y-%m-%d")
    if limit == 0:
        raise AppError(429, "QUOTA_EXCEEDED", "Tính năng đã hết hạn mức sử dụng")
    async with request.app.state.services.database.sessions() as session, session.begin():
        query = insert(AuthUsage).values(
            user_id=principal.user_id, kind=kind, bucket=bucket, count=1
        )
        value = await session.scalar(
            query.on_conflict_do_update(
                index_elements=[AuthUsage.user_id, AuthUsage.kind, AuthUsage.bucket],
                set_={"count": AuthUsage.count + 1},
                where=AuthUsage.count < limit,
            ).returning(AuthUsage.count)
        )
    if value is None:
        raise AppError(429, "QUOTA_EXCEEDED", "Bạn đã dùng hết hạn mức; vui lòng thử lại sau")
