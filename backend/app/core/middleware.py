import logging
from time import perf_counter
from uuid import UUID, uuid4

import anyio
from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.exceptions import AppError, error_body
from app.core.logging import request_id_context

logger = logging.getLogger("app.access")


class RequestContextMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        timeout: float,
        cors_origins: list[str],
        ingestion_timeout: float = 30,
        rag_timeout: float = 6,
    ):
        self.app = app
        self.timeout = timeout
        self.cors_origins = cors_origins
        self.ingestion_timeout = ingestion_timeout
        self.rag_timeout = rag_timeout

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        start = perf_counter()
        supplied_id = Headers(scope=scope).get("x-request-id", "")
        try:
            request_id = str(UUID(supplied_id))
        except ValueError:
            request_id = str(uuid4())
        state = scope.setdefault("state", {})
        state["request_id"] = request_id
        token = request_id_context.set(request_id)
        status, started, complete = 500, False, False
        completed_at: float | None = None

        async def tracked_send(message: Message) -> None:
            nonlocal status, started, complete, completed_at
            if message["type"] == "http.response.start":
                status, started = message["status"], True
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
            await send(message)
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                complete = True
                completed_at = perf_counter()

        async def send_error(code: str, message: str, error_status: int) -> None:
            state["error_category"] = code
            response = JSONResponse(
                error_body(request_id, code, message, retryable=error_status in (503, 504)),
                status_code=error_status,
            )
            origin = Headers(scope=scope).get("origin")
            if origin in self.cors_origins:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Vary"] = "Origin"
                response.headers["Access-Control-Expose-Headers"] = "X-Request-ID"
            await response(scope, receive, tracked_send)

        body_size = 0
        is_upload = scope["path"] == "/api/v1/images" and scope["method"] == "POST"
        is_search = scope["path"] in {"/api/v1/search", "/api/v1/search/multimodal"}
        is_rag = scope["path"] in {"/api/v1/rag/explain", "/api/v1/rag/explain/stream"}
        multipart = Headers(scope=scope).get("content-type", "").startswith("multipart/form-data")
        max_body = 21 * 1024**2 if is_upload or (is_search and multipart) else 65536

        async def bounded_receive():
            nonlocal body_size
            message = await receive()
            body_size += len(message.get("body", b""))
            if body_size > max_body:
                raise AppError(413, "PAYLOAD_TOO_LARGE", "Request vượt giới hạn dung lượng")
            return message

        try:
            with anyio.fail_after(
                self.ingestion_timeout
                if is_upload
                else self.rag_timeout
                if is_rag
                else self.timeout
            ):
                length = Headers(scope=scope).get("content-length")
                if length and (not length.isdigit() or int(length) > max_body):
                    raise AppError(413, "PAYLOAD_TOO_LARGE", "Request vượt giới hạn dung lượng")
                await self.app(scope, bounded_receive, tracked_send)
        except AppError as exc:
            if not started:
                await send_error(exc.code, exc.message, exc.status)
            else:
                raise
        except TimeoutError:
            state["error_category"] = "DEADLINE_EXCEEDED"
            if not started:
                await send_error("DEADLINE_EXCEEDED", "Yêu cầu đã hết thời gian xử lý", 504)
            elif not complete:
                raise RuntimeError("response_timeout_after_headers") from None
        except Exception:
            state["error_category"] = "INTERNAL_ERROR"
            if not started:
                await send_error("INTERNAL_ERROR", "Đã xảy ra lỗi xử lý nội bộ", 500)
            elif not complete:
                raise RuntimeError("response_failed_after_headers") from None
        finally:
            if is_search:
                app = scope.get("app")
                sink = getattr(getattr(app, "state", None), "search_metrics", None)
                if sink is not None:
                    final_time = completed_at if completed_at is not None else perf_counter()
                    sink.append(
                        {
                            "request_id": request_id,
                            "status_code": status,
                            "complete": complete,
                            "server_response_ms": (final_time - start) * 1000,
                            "serialization_send_ms": (final_time - state["result_ready_at"]) * 1000
                            if state.get("result_ready_at")
                            else None,
                            **state.get("search_trace", {}),
                        }
                    )
            # Log khi final send đã hoàn tất hoặc lỗi/ngắt kết nối; không log query string/headers.
            route = scope.get("route")
            logger.info(
                "http_request",
                extra={
                    "method": scope["method"],
                    "path": getattr(route, "path", "<unmatched>"),
                    "status_code": status,
                    "duration_ms": round(
                        ((completed_at if completed_at is not None else perf_counter()) - start)
                        * 1000,
                        3,
                    ),
                    "error_category": state.get("error_category")
                    or (None if complete else "INCOMPLETE"),
                },
            )
            request_id_context.reset(token)
