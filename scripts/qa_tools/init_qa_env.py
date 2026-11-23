"""Create isolated QA credentials without reading or changing the user's .env."""

import os
import secrets
from pathlib import Path
from uuid import uuid4


def initialize(root: Path) -> Path:
    target = root / ".env.qa"
    if not target.exists():
        password = secrets.token_hex(24)
        values = {
            "QA_PROJECT_NAME": "phase11-qa-" + uuid4().hex[:12],
            "QA_POSTGRES_PASSWORD": password,
            "APP_ENV": "test",
            "DEBUG": "false",
            "LOG_LEVEL": "WARNING",
            "DATABASE_URL": f"postgresql+psycopg://image_search_qa:{password}@qa-postgres:5432/image_search_qa",
            "QDRANT_URL": "http://qa-qdrant:6333",
            "QDRANT_API_KEY": secrets.token_hex(24),
            "MINIO_ENDPOINT": "qa-minio:9000",
            "MINIO_ACCESS_KEY": "qa" + secrets.token_hex(10),
            "MINIO_SECRET_KEY": secrets.token_hex(24),
            "MINIO_BUCKET": "image-search-qa",
            "MINIO_AUTO_CREATE_BUCKET": "true",
            "API_TOKEN": secrets.token_hex(24),
            "WRITE_API_TOKEN": secrets.token_hex(24),
            "QA_ISOLATED": "1",
            "SEARCH_ENABLED": "false",
            "RAG_ENABLED": "false",
            "AGENT_ENABLED": "false",
            "AGENT_LLM_PLANNING_ENABLED": "false",
            "AGENT_ALLOW_FIXTURE_KNOWLEDGE": "true",
            "MULTIMODAL_ENABLED": "true",
            "MULTI_INTENT_ENABLED": "true",
            "RERANKING_ENABLED": "true",
            "DATASET_ROOT": "/qa-fixtures",
            "EMBEDDING_CACHE_DIR": "/models/clip",
            "EMBEDDING_DEVICE": "cpu",
            "EMBEDDING_CPU_THREADS": "1",
            "DEPENDENCY_TIMEOUT_SECONDS": "3",
            "REQUEST_TIMEOUT_SECONDS": "5",
            "EVALUATION_RESULTS_DIR": "/qa-results/no-benchmarks",
            "CORS_ORIGINS": '["http://127.0.0.1:5175"]',
        }
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as handle:
            handle.write("\n".join(f"{key}={value}" for key, value in values.items()) + "\n")
    for name in ["fixtures", "results"]:
        directory = root / ".cache/qa" / name
        directory.mkdir(parents=True, exist_ok=True)
        directory.chmod(0o777)  # Only disposable synthetic fixtures/results, no credentials.
    (root / ".cache/clip").mkdir(parents=True, exist_ok=True)
    return target


if __name__ == "__main__":
    initialize(Path(__file__).resolve().parents[2])
    print("QA environment ready; credentials kept in .env.qa (0600).")
