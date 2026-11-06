from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException


class AppError(Exception):
    def __init__(self, status: int, code: str, message: str, *, retryable: bool = False):
        self.status = status
        self.code = code
        self.message = message
        self.retryable = retryable


def error_body(request_id: str, code: str, message: str, *, retryable=False, details=None):
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
            "retryable": retryable,
            "details": details or [],
        }
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error(request: Request, exc: AppError):
        request.state.error_category = exc.code
        headers = {"WWW-Authenticate": "Bearer"} if exc.status == 401 else None
        if exc.code == "IDEMPOTENCY_IN_PROGRESS":
            headers = {"Retry-After": "1"}
        return JSONResponse(
            error_body(request.state.request_id, exc.code, exc.message, retryable=exc.retryable),
            status_code=exc.status,
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        request.state.error_category = "INVALID_INPUT"
        details = [
            {"field": ".".join(map(str, e["loc"])), "reason": e["type"]} for e in exc.errors()
        ]
        return JSONResponse(
            error_body(
                request.state.request_id, "INVALID_INPUT", "Tham số không hợp lệ", details=details
            ),
            status_code=422,
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, _exc: SQLAlchemyError):
        request.state.error_category = "DEPENDENCY_UNAVAILABLE"
        return JSONResponse(
            error_body(
                request.state.request_id,
                "DEPENDENCY_UNAVAILABLE",
                "Dịch vụ dữ liệu tạm thời không khả dụng",
                retryable=True,
            ),
            status_code=503,
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "HTTP_ERROR")
        request.state.error_category = code
        return JSONResponse(
            error_body(request.state.request_id, code, "Yêu cầu không được xử lý"),
            status_code=exc.status_code,
            headers=exc.headers,
        )
