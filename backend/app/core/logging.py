import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime

request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", request_id_context.get()),
            "event": record.getMessage(),
        }
        for key in (
            "method",
            "path",
            "status_code",
            "duration_ms",
            "error_category",
            "dependency",
            "job_id",
            "item_id",
            "image_id",
            "index_id",
            "stage",
            "attempt_no",
            "batch_size",
        ):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    # Các SDK có thể log URL/headers; chỉ log access events đã allowlist của ứng dụng.
    for name in ("httpx", "httpcore", "urllib3", "sqlalchemy.engine", "qdrant_client"):
        logging.getLogger(name).setLevel(logging.CRITICAL)
