"""Same-origin account registration and sessions; no public admin bootstrap."""

import secrets

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from app.core.auth import (
    bearer,
    check_origin,
    cookie_names,
    require_read_access,
    resolve_identity,
    secret_digest,
)
from app.core.exceptions import AppError
from app.core.quick_login import DEMO_ACCOUNTS, quick_login_enabled
from app.db.models.access import AuthSession, User
from app.schemas.access import ChangePassword, LoginInput, QuickLoginInput, RegistrationInput
from app.services.accounts import (
    audit,
    check_password,
    clear_cookies,
    dummy_password_hash,
    issue_session,
    make_password,
    quick_login_roles,
    set_cookies,
    throttle_login,
    user_snapshot,
)

router = APIRouter(prefix="/auth", tags=["Accounts"])


@router.post("/register", status_code=201)
async def register(body: RegistrationInput, request: Request, response: Response):
    check_origin(request)
    response.headers["Cache-Control"] = "no-store"
    try:
        await throttle_login(request, body.username)
        if body.username in {name for name, _ in DEMO_ACCOUNTS.values()}:
            raise AppError(409, "USERNAME_TAKEN", "Tên đăng nhập này không khả dụng")
        encoded = await make_password(request, body.password.get_secret_value())
        async with request.app.state.services.database.sessions() as session, session.begin():
            user = await session.scalar(
                insert(User)
                .values(
                    username=body.username,
                    display_name=body.display_name,
                    password_hash=encoded,
                    role="user",
                    is_active=True,
                    is_demo=False,
                )
                .on_conflict_do_nothing(index_elements=[User.username])
                .returning(User)
            )
            if user is None:
                raise AppError(409, "USERNAME_TAKEN", "Tên đăng nhập này không khả dụng")
            audit(session, None, "auth.registered", user.id)
        return {"status": "registered"}
    except SQLAlchemyError:
        raise AppError(
            503, "AUTH_NOT_READY", "Dịch vụ đăng ký chưa sẵn sàng", retryable=True
        ) from None


@router.get("/me")
async def me(request: Request, response: Response):
    principal = await resolve_identity(request, await bearer(request), optional=True)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Vary"] = "Cookie, Authorization"
    if principal is None or principal.user_id is None:
        if principal is None:
            clear_cookies(response, request.app.state.settings)
        return {
            "user": None,
            "legacy_enabled": request.app.state.settings.auth_legacy_tokens_enabled,
            "quick_login_roles": await quick_login_roles(request.app.state.services),
        }
    settings = request.app.state.settings
    csrf = request.cookies.get(cookie_names(settings)[1], "")
    if not csrf or not secrets.compare_digest(
        secret_digest(csrf), request.state.auth_session.csrf_hash
    ):
        csrf = secrets.token_urlsafe(32)
        async with request.app.state.services.database.sessions() as session, session.begin():
            row = await session.get(AuthSession, request.state.auth_session.token_hash)
            if row is None:
                raise AppError(401, "UNAUTHENTICATED", "Phiên đăng nhập đã kết thúc")
            row.csrf_hash = secret_digest(csrf)
        response.set_cookie(
            cookie_names(settings)[1],
            csrf,
            secure=settings.auth_cookie_secure,
            httponly=False,
            samesite="strict",
            path="/",
            max_age=settings.auth_session_hours * 3600,
        )
    return {
        "user": await user_snapshot(request.app.state.services, request.state.auth_user),
        "legacy_enabled": settings.auth_legacy_tokens_enabled,
        "quick_login_roles": await quick_login_roles(request.app.state.services),
    }


@router.post("/login")
async def login(body: LoginInput, request: Request, response: Response):
    check_origin(request)
    try:
        await throttle_login(request, body.username)
        async with request.app.state.services.database.sessions() as session:
            user = await session.scalar(select(User).where(User.username == body.username))
        valid = await check_password(
            request,
            body.password.get_secret_value(),
            user.password_hash if user else dummy_password_hash(),
        )
        if not valid or user is None or not user.is_active or user.is_demo:
            raise AppError(401, "LOGIN_FAILED", "Tên đăng nhập hoặc mật khẩu không đúng")
        # Re-check after password work so a concurrent lock/reset cannot mint a stale session.
        async with request.app.state.services.database.sessions() as session:
            fresh = await session.get(User, user.id)
            if not fresh or not fresh.is_active or fresh.password_hash != user.password_hash:
                raise AppError(401, "LOGIN_FAILED", "Tên đăng nhập hoặc mật khẩu không đúng")
        token, csrf = await issue_session(request.app.state.services, user)
        set_cookies(response, request.app.state.settings, token, csrf)
        return {
            "user": await user_snapshot(request.app.state.services, user),
            "legacy_enabled": request.app.state.settings.auth_legacy_tokens_enabled,
            "quick_login_roles": await quick_login_roles(request.app.state.services),
        }
    except SQLAlchemyError:
        raise AppError(
            503, "AUTH_NOT_READY", "Dịch vụ đăng nhập chưa sẵn sàng", retryable=True
        ) from None


@router.post("/logout", dependencies=[Depends(require_read_access)])
async def logout(request: Request, response: Response):
    if getattr(request.state, "auth_session", None):
        async with request.app.state.services.database.sessions() as session, session.begin():
            await session.execute(
                delete(AuthSession).where(
                    AuthSession.token_hash == request.state.auth_session.token_hash
                )
            )
            audit(session, request.state.principal, "auth.logout")
    clear_cookies(response, request.app.state.settings)
    return {"status": "signed_out"}


@router.post("/password", dependencies=[Depends(require_read_access)])
async def change_password(body: ChangePassword, request: Request, response: Response):
    user = getattr(request.state, "auth_user", None)
    if user is None or not await check_password(
        request, body.current_password.get_secret_value(), user.password_hash
    ):
        raise AppError(403, "PASSWORD_INCORRECT", "Mật khẩu hiện tại không đúng")
    if secrets.compare_digest(
        body.current_password.get_secret_value().encode("utf-8"),
        body.password.get_secret_value().encode("utf-8"),
    ):
        raise AppError(422, "PASSWORD_UNCHANGED", "Mật khẩu mới phải khác mật khẩu hiện tại")
    encoded = await make_password(request, body.password.get_secret_value())
    async with request.app.state.services.database.sessions() as session, session.begin():
        locked = await session.get(User, user.id, with_for_update=True)
        if locked is None or not locked.is_active or locked.password_hash != user.password_hash:
            raise AppError(409, "ACCOUNT_CHANGED", "Tài khoản vừa thay đổi; vui lòng đăng nhập lại")
        locked.password_hash = encoded
        await session.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
        audit(session, request.state.principal, "auth.password_changed", user.id)
    clear_cookies(response, request.app.state.settings)
    return {"status": "sign_in_again"}


@router.post("/quick-login")
async def quick_login(body: QuickLoginInput, request: Request, response: Response):
    settings = request.app.state.settings
    if not quick_login_enabled(settings):
        raise AppError(404, "NOT_FOUND", "Đăng nhập nhanh chưa được bật")
    check_origin(request)
    username = DEMO_ACCOUNTS[body.role][0]
    try:
        await throttle_login(request, username)
        async with request.app.state.services.database.sessions() as session:
            user = await session.scalar(
                select(User).where(
                    User.username == username,
                    User.role == body.role,
                    User.is_demo.is_(True),
                    User.is_active.is_(True),
                )
            )
        if user is None:
            raise AppError(409, "QUICK_LOGIN_NOT_READY", "Tài khoản trải nghiệm chưa sẵn sàng")
        token, csrf = await issue_session(request.app.state.services, user, quick_role=body.role)
        set_cookies(response, settings, token, csrf)
        return {
            "user": await user_snapshot(request.app.state.services, user),
            "legacy_enabled": settings.auth_legacy_tokens_enabled,
            "quick_login_roles": await quick_login_roles(request.app.state.services),
        }
    except SQLAlchemyError:
        raise AppError(
            503, "AUTH_NOT_READY", "Dịch vụ đăng nhập chưa sẵn sàng", retryable=True
        ) from None
