"""Opt-in public image scopes and atomic guest search throttling."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Request, Response
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import case
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from app.core.access import Principal, current_principal
from app.core.auth import bearer, check_origin, resolve_identity, secret_digest
from app.core.exceptions import AppError
from app.db.models.access import LoginThrottle
from app.services.dataset_access import public_datasets


async def require_guest_access(request: Request):
    if not request.app.state.settings.guest_search_enabled:
        raise AppError(401, "UNAUTHENTICATED", "Vui lòng đăng nhập để tiếp tục")
    try:
        async with request.app.state.services.database.sessions() as session:
            datasets = list((await session.scalars(public_datasets())).all())
    except SQLAlchemyError:
        raise AppError(
            503, "PUBLIC_SCOPE_UNAVAILABLE", "Chưa đọc được thư viện công khai", retryable=True
        ) from None
    principal = Principal(
        None, "guest", "guest", tuple(d.id for d in datasets), tuple(d.key for d in datasets)
    )
    request.state.public_datasets = [
        {"id": str(d.id), "key": d.key, "name": d.name} for d in datasets
    ]
    request.state.principal = principal
    current_principal.set(principal)
    return principal


async def require_search_access(
    request: Request,
    response: Response,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
):
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Cookie, Authorization"
    principal = await resolve_identity(request, credentials, optional=True)
    if principal is not None:
        return principal
    if not request.app.state.settings.guest_search_enabled:
        raise AppError(401, "UNAUTHENTICATED", "Vui lòng đăng nhập để tiếp tục")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        check_origin(request)
    return await require_guest_access(request)


async def charge_guest_search(request):
    # Use the server's peer address; never accept an arbitrary forwarded IP header.
    peer = request.client.host if request.client else "unknown"
    bucket = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M")
    limit = request.app.state.settings.guest_search_per_minute
    async with request.app.state.services.database.sessions() as session, session.begin():
        query = insert(LoginThrottle).values(
            key=secret_digest("guest-search:" + peer), bucket=bucket, count=1
        )
        count = await session.scalar(
            query.on_conflict_do_update(
                index_elements=[LoginThrottle.key],
                set_={
                    "bucket": bucket,
                    "count": case(
                        (LoginThrottle.bucket != bucket, 1), else_=LoginThrottle.count + 1
                    ),
                },
                where=(LoginThrottle.bucket != bucket) | (LoginThrottle.count < limit),
            ).returning(LoginThrottle.count)
        )
    if count is None:
        raise AppError(
            429,
            "GUEST_RATE_LIMITED",
            "Đã hết lượt tìm cho khách trong phút này. Vui lòng thử lại sau.",
        )
