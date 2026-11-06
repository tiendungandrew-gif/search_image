from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import AnyHttpUrl, Field, SecretStr, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_name: str = Field(default="image-search-api", min_length=1, max_length=80)
    app_env: Literal["development", "test", "production"] = "development"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    api_prefix: str = "/api/v1"
    database_url: SecretStr
    qdrant_url: AnyHttpUrl
    qdrant_api_key: SecretStr | None = None
    minio_endpoint: str
    minio_access_key: SecretStr
    minio_secret_key: SecretStr
    minio_bucket: str = Field(default="image-search", pattern=r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")
    minio_secure: bool = False
    minio_auto_create_bucket: bool = False
    api_token: SecretStr
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    request_timeout_seconds: float = Field(default=2, ge=0.05, le=30)
    dependency_timeout_seconds: float = Field(default=0.75, ge=0.02, le=10)
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=5, ge=0, le=50)
    database_pool_timeout_seconds: float = Field(default=0.5, gt=0, le=10)
    write_api_token: SecretStr | None = None
    embedding_model_id: str = "openai/clip-vit-base-patch32"
    embedding_model_revision: str = Field(
        default="3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268", pattern=r"^[0-9a-f]{40}$"
    )
    embedding_cache_dir: str = "/models/clip"
    embedding_device: Literal["auto", "cpu", "cuda"] = "auto"
    embedding_batch_size: int = Field(default=4, ge=1, le=32)
    embedding_cpu_threads: int = Field(default=4, ge=1, le=32)
    ingestion_index_id: str | None = None
    image_max_upload_mb: int = Field(default=20, ge=1, le=20)
    image_max_pixels: int = Field(default=25_000_000, ge=1, le=40_000_000)
    image_max_side: int = Field(default=10_000, ge=1, le=20_000)
    image_decode_timeout_seconds: float = Field(default=2, gt=0, le=15)
    ingestion_timeout_seconds: float = Field(default=30, ge=2, le=60)
    indexing_max_retries: int = Field(default=3, ge=1, le=10)
    indexing_lease_seconds: int = Field(default=120, ge=10, le=3600)
    indexing_job_timeout_seconds: int = Field(default=600, ge=10, le=3600)
    dataset_root: str = "/datasets"
    search_enabled: bool = False
    search_max_top_k: int = Field(default=50, ge=1, le=100)
    search_default_candidates: int = Field(default=50, ge=1, le=1000)
    search_max_text_length: int = Field(default=2000, ge=1, le=2000)
    search_enable_basic_filters: bool = True
    search_queue_capacity: int = Field(default=8, ge=1, le=64)
    search_queue_wait_seconds: float = Field(default=0.05, gt=0, le=1)
    search_vector_timeout_seconds: int = Field(default=1, ge=1, le=10)
    search_object_check_concurrency: int = Field(default=1, ge=1, le=2)
    multi_intent_enabled: bool = True
    multimodal_enabled: bool = True
    query_decomposition_enabled: bool = True
    search_max_constraints: int = Field(default=8, ge=1, le=8)
    search_max_branches: int = Field(default=4, ge=2, le=4)
    search_advanced_candidate_limit: int = Field(default=100, ge=1, le=1000)
    multimodal_fusion_strategy: Literal["rrf", "weighted_rrf", "weighted_score"] = "rrf"
    multimodal_text_weight: float = Field(default=0.5, ge=0, le=1, allow_inf_nan=False)
    multimodal_image_weight: float = Field(default=0.5, ge=0, le=1, allow_inf_nan=False)
    fusion_rrf_k: int = Field(default=60, ge=1, le=1000)
    reranking_enabled: bool = True
    reranking_max_candidates: int = Field(default=50, ge=1, le=100)
    reranking_timeout_ms: int = Field(default=200, ge=1, le=1000)
    rerank_whole_weight: float = Field(default=0.4, ge=0, le=1, allow_inf_nan=False)
    rerank_constraint_weight: float = Field(default=0.4, ge=0, le=1, allow_inf_nan=False)
    rerank_metadata_weight: float = Field(default=0.2, ge=0, le=1, allow_inf_nan=False)
    rerank_unknown_penalty: float = Field(default=0.02, ge=0, le=1, allow_inf_nan=False)
    rerank_required_penalty: float = Field(default=0.25, ge=0, le=1, allow_inf_nan=False)
    rerank_optional_weight: float = Field(default=0.1, ge=0, le=1, allow_inf_nan=False)
    rag_enabled: bool = False
    rag_model_provider: Literal["openai", "gemini", "openai_compatible"] = "gemini"
    rag_model_id: str = Field(default="", max_length=160)
    rag_model_revision: str = Field(default="provider_managed", max_length=160)
    rag_model_endpoint: str = "https://generativelanguage.googleapis.com/v1beta"
    rag_gemini_api_style: Literal["native", "openai_compatible"] = "native"
    rag_api_key: SecretStr | None = None
    gemini_api_key: SecretStr | None = Field(default=None, exclude=True, repr=False)
    openai_api_key: SecretStr | None = Field(default=None, exclude=True, repr=False)
    rag_max_evidence_items: int = Field(default=5, ge=1, le=10)
    rag_max_context_tokens: int = Field(default=2048, ge=256, le=8192)
    rag_max_input_tokens: int = Field(default=4096, ge=512, le=16384)
    rag_max_output_tokens: int = Field(default=128, ge=16, le=512)
    rag_temperature: float = Field(default=0.1, ge=0, le=1, allow_inf_nan=False)
    rag_timeout_seconds: float = Field(default=5, ge=0.1, le=30)
    rag_request_timeout_seconds: float = Field(default=8, ge=1, le=60)
    rag_max_concurrency: int = Field(default=2, ge=1, le=4)
    rag_provider_retries: int = Field(default=0, ge=0, le=1)
    rag_streaming_enabled: bool = True
    rag_token_parameter: Literal["max_tokens", "max_completion_tokens"] = "max_tokens"
    rag_reasoning_effort: Literal["none", "minimal", "low", "medium", "high"] | None = None

    @model_validator(mode="after")
    def advanced_weights(self):
        if not self.rag_api_key or not self.rag_api_key.get_secret_value().strip():
            self.rag_api_key = (
                self.gemini_api_key
                if self.rag_model_provider == "gemini"
                else self.openai_api_key
                if self.rag_model_provider == "openai"
                else None
            )
        if self.multimodal_text_weight + self.multimodal_image_weight <= 0:
            raise ValueError("Fusion weights không được đồng thời zero")
        if (
            self.rerank_whole_weight + self.rerank_constraint_weight + self.rerank_metadata_weight
            <= 0
        ):
            raise ValueError("Rerank weights không được đồng thời zero")
        return self

    @field_validator("api_prefix")
    @classmethod
    def validate_prefix(cls, value: str) -> str:
        if value != "/api/v1":
            raise ValueError("API_PREFIX phải là /api/v1 theo contract hiện tại")
        return value

    @field_validator("database_url")
    @classmethod
    def validate_database(cls, value: SecretStr) -> SecretStr:
        try:
            url = make_url(value.get_secret_value())
            valid = url.drivername == "postgresql+psycopg" and url.host and url.database
        except Exception:
            valid = False
        if not valid:
            raise ValueError("DATABASE_URL phải là PostgreSQL với driver psycopg")
        return value

    @field_validator(
        "qdrant_api_key",
        "write_api_token",
        "ingestion_index_id",
        "rag_api_key",
        "gemini_api_key",
        "openai_api_key",
        "rag_reasoning_effort",
        mode="before",
    )
    @classmethod
    def empty_key(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("api_token", "minio_secret_key", "minio_access_key")
    @classmethod
    def validate_secret(cls, value: SecretStr, info) -> SecretStr:
        raw = value.get_secret_value()
        minimum = {"api_token": 24, "minio_secret_key": 16, "minio_access_key": 3}[info.field_name]
        if len(raw) < minimum or raw.lower().startswith(("change_me", "changeme", "example")):
            raise ValueError("Secret thiếu hoặc không hợp lệ; dùng scripts/init_env.py")
        return value

    @field_validator("qdrant_url")
    @classmethod
    def no_url_credentials(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        if value.username or value.password or value.query or value.fragment:
            raise ValueError("QDRANT_URL không được chứa credentials/query/fragment")
        return value

    @field_validator("minio_endpoint")
    @classmethod
    def validate_endpoint(cls, value: str) -> str:
        parsed = urlsplit("//" + value)
        if not parsed.hostname or parsed.path or parsed.username or parsed.query or parsed.fragment:
            raise ValueError("MINIO_ENDPOINT chỉ chứa host:port, không scheme/path/credentials")
        try:
            _ = parsed.port
        except ValueError as exc:
            raise ValueError("MINIO_ENDPOINT có port không hợp lệ") from exc
        return value

    @field_validator("cors_origins")
    @classmethod
    def validate_origins(cls, values: list[str]) -> list[str]:
        for value in values:
            parsed = urlsplit(value)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.username
                or "*" in value
            ):
                raise ValueError("CORS_ORIGINS cần origin HTTP(S) cụ thể, không wildcard/path")
        return values

    @model_validator(mode="after")
    def validate_environment(self) -> "Settings":
        if self.write_api_token is not None and len(self.write_api_token.get_secret_value()) < 24:
            raise ValueError("WRITE_API_TOKEN cần ít nhất 24 ký tự")
        if self.dependency_timeout_seconds >= self.request_timeout_seconds:
            raise ValueError("Dependency timeout phải nhỏ hơn request timeout")
        if self.app_env == "production" and (self.debug or self.minio_auto_create_bucket):
            raise ValueError("Production không cho DEBUG hoặc tự tạo bucket")
        return self


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        fields = ", ".join(".".join(map(str, item["loc"])) for item in exc.errors())
        raise RuntimeError(f"Cấu hình không hợp lệ ở fields: {fields}; xem docs/SETUP.md") from None
