# Tham chiếu cấu hình

Không lưu secrets trong tài liệu. scripts/deploy.py init sinh env riêng0600 và không copy .env serving. Bảng lấy từ Settings: default class có thể khác production init/template; .env.deploy.example ghi cấu hình triển khai không có credentials.

## Application settings

| Biến | Bắt buộc | Default class | Secret |
| --- | --- | --- | --- |
| EVALUATION_RESULTS_DIR | Không | evaluation/results | Không |
| APP_NAME | Không | image-search-api | Không |
| APP_ENV | Không | development | Không |
| DEBUG | Không | false | Không |
| LOG_LEVEL | Không | INFO | Không |
| API_PREFIX | Không | /api/v1 | Không |
| DATABASE_URL | Có | init cung cấp | Có |
| QDRANT_URL | Có | init cung cấp | Không |
| QDRANT_API_KEY | Không | trống | Có |
| MINIO_ENDPOINT | Có | init cung cấp | Không |
| MINIO_ACCESS_KEY | Có | init cung cấp | Có |
| MINIO_SECRET_KEY | Có | init cung cấp | Có |
| MINIO_BUCKET | Không | image-search | Không |
| MINIO_SECURE | Không | false | Không |
| MINIO_AUTO_CREATE_BUCKET | Không | false | Không |
| AUTH_QUICK_LOGIN_ENABLED | Không | false; chỉ local development/test | Không |
| AUTH_LEGACY_TOKENS_ENABLED | Không | false | Không |
| AUTH_COOKIE_SECURE | Không | false (public HTTPS cần true) | Không |
| AUTH_SESSION_HOURS | Không | 12 | Không |
| AUTH_LOGIN_ATTEMPTS_PER_MINUTE | Không | 10 | Không |
| USER_SEARCH_PER_MINUTE | Không | 60 | Không |
| USER_RAG_PER_DAY | Không | 20 | Không |
| USER_AGENT_PER_DAY | Không | 20 | Không |
| API_TOKEN | Có | init cung cấp | Có |
| CORS_ORIGINS | Không | ["http://localhost:5173", "http://127.0.0.1:5173"] | Không |
| REQUEST_TIMEOUT_SECONDS | Không | 2 | Không |
| DEPENDENCY_TIMEOUT_SECONDS | Không | 0.75 | Không |
| DATABASE_POOL_SIZE | Không | 5 | Không |
| DATABASE_MAX_OVERFLOW | Không | 5 | Không |
| DATABASE_POOL_TIMEOUT_SECONDS | Không | 0.5 | Không |
| WRITE_API_TOKEN | Không | trống | Có |
| EMBEDDING_MODEL_ID | Không | openai/clip-vit-base-patch32 | Không |
| EMBEDDING_MODEL_REVISION | Không | 3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268 | Không |
| EMBEDDING_CACHE_DIR | Không | /models/clip | Không |
| EMBEDDING_DEVICE | Không | auto | Không |
| EMBEDDING_BATCH_SIZE | Không | 4 | Không |
| EMBEDDING_CPU_THREADS | Không | 4 | Không |
| INGESTION_INDEX_ID | Không | trống | Không |
| IMAGE_MAX_UPLOAD_MB | Không | 20 | Không |
| IMAGE_MAX_PIXELS | Không | 25000000 | Không |
| IMAGE_MAX_SIDE | Không | 10000 | Không |
| IMAGE_DECODE_TIMEOUT_SECONDS | Không | 2 | Không |
| INGESTION_TIMEOUT_SECONDS | Không | 30 | Không |
| INDEXING_MAX_RETRIES | Không | 3 | Không |
| INDEXING_LEASE_SECONDS | Không | 120 | Không |
| INDEXING_JOB_TIMEOUT_SECONDS | Không | 600 | Không |
| DATASET_ROOT | Không | /datasets | Không |
| SEARCH_ENABLED | Không | false | Không |
| SEARCH_MAX_TOP_K | Không | 50 | Không |
| SEARCH_DEFAULT_CANDIDATES | Không | 50 | Không |
| SEARCH_MAX_TEXT_LENGTH | Không | 2000 | Không |
| SEARCH_ENABLE_BASIC_FILTERS | Không | true | Không |
| SEARCH_QUEUE_CAPACITY | Không | 8 | Không |
| SEARCH_QUEUE_WAIT_SECONDS | Không | 0.05 | Không |
| SEARCH_VECTOR_TIMEOUT_SECONDS | Không | 1 | Không |
| SEARCH_OBJECT_CHECK_CONCURRENCY | Không | 1 | Không |
| MULTI_INTENT_ENABLED | Không | true | Không |
| MULTIMODAL_ENABLED | Không | true | Không |
| QUERY_DECOMPOSITION_ENABLED | Không | true | Không |
| SEARCH_MAX_CONSTRAINTS | Không | 8 | Không |
| SEARCH_MAX_BRANCHES | Không | 4 | Không |
| SEARCH_ADVANCED_CANDIDATE_LIMIT | Không | 100 | Không |
| MULTIMODAL_FUSION_STRATEGY | Không | rrf | Không |
| MULTIMODAL_TEXT_WEIGHT | Không | 0.5 | Không |
| MULTIMODAL_IMAGE_WEIGHT | Không | 0.5 | Không |
| FUSION_RRF_K | Không | 60 | Không |
| RERANKING_ENABLED | Không | true | Không |
| RERANKING_MAX_CANDIDATES | Không | 50 | Không |
| RERANKING_TIMEOUT_MS | Không | 200 | Không |
| RERANK_WHOLE_WEIGHT | Không | 0.4 | Không |
| RERANK_CONSTRAINT_WEIGHT | Không | 0.4 | Không |
| RERANK_METADATA_WEIGHT | Không | 0.2 | Không |
| RERANK_UNKNOWN_PENALTY | Không | 0.02 | Không |
| RERANK_REQUIRED_PENALTY | Không | 0.25 | Không |
| RERANK_OPTIONAL_WEIGHT | Không | 0.1 | Không |
| RAG_ENABLED | Không | false | Không |
| AGENT_ENABLED | Không | false | Không |
| AGENT_ROUTER_ENABLED | Không | true | Không |
| AGENT_PLANNER_MODE | Không | deterministic | Không |
| AGENT_LLM_PLANNING_ENABLED | Không | false | Không |
| AGENT_MAX_HOPS | Không | 3 | Không |
| AGENT_MAX_TOOL_CALLS | Không | 6 | Không |
| AGENT_MAX_REPLANS | Không | 1 | Không |
| AGENT_TIMEOUT_SECONDS | Không | 15 | Không |
| AGENT_TOOL_TIMEOUT_SECONDS | Không | 2 | Không |
| AGENT_PLANNING_TIMEOUT_SECONDS | Không | 4 | Không |
| AGENT_MAX_CONCURRENCY | Không | 2 | Không |
| AGENT_RAG_ENABLED | Không | false | Không |
| AGENT_STREAMING_ENABLED | Không | true | Không |
| AGENT_ALLOW_EMPTY_DATASET | Không | true | Không |
| AGENT_ENABLE_FALLBACK | Không | true | Không |
| AGENT_ALLOW_FIXTURE_KNOWLEDGE | Không | false | Không |
| AGENT_LOG_TRACE | Không | true | Không |
| RAG_MODEL_PROVIDER | Không | gemini | Không |
| RAG_MODEL_ID | Không | trống | Không |
| RAG_MODEL_REVISION | Không | provider_managed | Không |
| RAG_MODEL_ENDPOINT | Không | https://generativelanguage.googleapis.com/v1beta | Không |
| RAG_GEMINI_API_STYLE | Không | native | Không |
| RAG_API_KEY | Không | trống | Có |
| GEMINI_API_KEY | Không | trống | Có |
| OPENAI_API_KEY | Không | trống | Có |
| RAG_MAX_EVIDENCE_ITEMS | Không | 5 | Không |
| RAG_MAX_CONTEXT_TOKENS | Không | 2048 | Không |
| RAG_MAX_INPUT_TOKENS | Không | 4096 | Không |
| RAG_MAX_OUTPUT_TOKENS | Không | 128 | Không |
| RAG_TEMPERATURE | Không | 0.1 | Không |
| RAG_TIMEOUT_SECONDS | Không | 8 | Không |
| RAG_REQUEST_TIMEOUT_SECONDS | Không | 12 | Không |
| RAG_MAX_CONCURRENCY | Không | 2 | Không |
| RAG_PROVIDER_RETRIES | Không | 0 | Không |
| RAG_STREAMING_ENABLED | Không | true | Không |
| RAG_TOKEN_PARAMETER | Không | max_tokens | Không |
| RAG_REASONING_EFFORT | Không | trống | Không |

Typed validation trong source là nguồn bounds/enums. Settings bao phủ application, PG pool, Qdrant/MinIO, model/cache/CPU/batch, upload/retry/lease, search/fusion/rerank, RAG và Agent. Giữ SEARCH_MAX_TOP_K không quá50 cho client web hiện tại. Dimension/collection lấy từ model manifest, không tự đặt để né compatibility checks.

## Production init

APP_ENV=production; DEBUG=false; MINIO_AUTO_CREATE_BUCKET=false. Bootstrap tạo/verify bucket có chủ đích. DATABASE_URL phải khớp POSTGRES_USER/POSTGRES_DB/POSTGRES_PASSWORD trên postgres:5432; QDRANT_URL=http://qdrant:6333, MINIO_ENDPOINT=minio:9000. Các POSTGRES_* là Compose settings. Production init dùng request/dependency timeout5s/3s, SEARCH/RAG/AGENT=false, CORS origin loopback:8080, model CPU, evaluation root /evaluation/results. Credentials là random hex; API read/write khác nhau.

## Deployment settings

| Biến | Default / ý nghĩa |
| --- | --- |
| DEPLOY_PROJECT_NAME | image-search-prod; prefix riêng, khác dev/QA |
| DEPLOY_RELEASE | phase12-local; local immutable tag/release manifest |
| DEPLOY_INSTALL_ML |true; init --without-ml cho empty CI, inference cần ML image |
| DEPLOY_BIND_ADDRESS / DEPLOY_HTTP_PORT |127.0.0.1 /8080 |
| DEPLOY_MODEL_PATH / DEPLOY_DATASET_PATH |Absolute paths, init resolve .cache/clip và datasets, runtime read-only |
| DEPLOY_NO_NEW_PRIVILEGES |true; local Docker Snap compatibility=false được ghi riêng |
| DEPLOY_BACKEND_MEMORY / DEPLOY_WORKER_MEMORY |3g /3g |
| DEPLOY_POSTGRES_MEMORY / DEPLOY_QDRANT_MEMORY / DEPLOY_MINIO_MEMORY |768m /1g /768m |
| DEPLOY_BACKEND_CPUS / DEPLOY_WORKER_CPUS |4 /4 |
| DEPLOY_POSTGRES_CPUS / DEPLOY_QDRANT_CPUS / DEPLOY_MINIO_CPUS |2 /2 /2 |
| DEPLOY_HTTPS_PORT |8443 khi --tls |
| DEPLOY_TLS_PATH |Directory tls.crt/tls.key; bắt buộc khi --tls |
| DEPLOY_TLS_CA_FILE |CA tin cậy cho local TLS check; không verify=false |
| DEPLOY_CHECK_URL |URL check override; mặc định loopback/profile port |
| DEPLOY_PUBLIC_HOST |Bắt buộc nếu bind ngoài loopback; operator xác minh domain/exposure |
| DEPLOY_ENV_FILE / DEPLOY_SOURCE_VERSION |Tool inject env path/source hash; không đặt thủ công |
| DEPLOY_USE_SG |Shell prefix=1 cho Docker Snap, không phải VITE variable |

## Thay đổi an toàn

Env parser dùng KEY=value, hỗ trợ quoted strings, không source/eval shell hoặc tự interpolate ${VAR}. Không dùng multiline literal. CORS_ORIGINS là JSON array một dòng. Nếu sửa DATABASE_URL phải encode credentials và khớp Compose fields. Dùng deploy.py validate, không dump docker compose config chứa secrets.

features --search true|false --agent true|false --rag true|false chỉ đổi flags/recreate backend; không cung cấp key/model/knowledge còn thiếu. Khi search bật, check còn kiểm health?check=search. Provider configured không phải provider SLA healthy. Keys nằm trong env server, không VITE_*; chỉ VITE_API_BASE_URL=/api/v1 là public build config.

Production image không copy host env. Env phải0600; thay model/data path/resources cần recreate service và check. Giới hạn queue/deadline hữu hạn; không tăng vô hạn để làm benchmark pass.
