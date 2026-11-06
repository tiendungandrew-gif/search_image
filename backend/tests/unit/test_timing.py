from unittest.mock import Mock

from app.core.middleware import RequestContextMiddleware


async def test_full_timer_ends_after_final_send_and_excludes_post_response_work(monkeypatch):
    # Controlled clock để kiểm tra boundary, không phải benchmark latency.
    clock = [1.0]
    monkeypatch.setattr("app.core.middleware.perf_counter", lambda: clock[0])
    log = Mock()
    monkeypatch.setattr("app.core.middleware.logger", log)

    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})
        clock[0] = 100.0  # Công việc sau response không được cộng vào full response metric.

    async def send(message):
        if message["type"] == "http.response.body":
            clock[0] = 1.025

    async def receive():
        return {"type": "http.request", "body": b""}

    await RequestContextMiddleware(app, timeout=2, cors_origins=[])(
        {"type": "http", "method": "GET", "path": "/timing", "headers": []},
        receive,
        send,
    )
    event = log.info.call_args.kwargs["extra"]
    assert event["duration_ms"] == 25.0
    assert event["status_code"] == 200
