import secrets
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import AppError

bearer = HTTPBearer(auto_error=False)


def require_read_access(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> None:
    # Token local của operator có quyền read. Không có user/multi-tenant management ở phase này.
    settings = request.app.state.settings
    expected = [settings.api_token, settings.write_api_token]
    if credentials is None or not any(
        secret
        and secrets.compare_digest(
            credentials.credentials.encode(), secret.get_secret_value().encode()
        )
        for secret in expected
    ):
        raise AppError(401, "UNAUTHENTICATED", "Cần Bearer token hợp lệ")


def require_write_access(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> None:
    expected = request.app.state.settings.write_api_token
    if expected is None:
        raise AppError(409, "FEATURE_DISABLED", "Chưa cấu hình WRITE_API_TOKEN")
    if credentials is None or not secrets.compare_digest(
        credentials.credentials.encode(), expected.get_secret_value().encode()
    ):
        raise AppError(403, "FORBIDDEN", "Cần operator write token")
