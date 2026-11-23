# Phát triển và kiểm thử foundation

**Bàn giao Phase12:** production entrypoint là `scripts/deploy.py`, dùng Compose riêng; xem [TESTING_AND_VERIFICATION](TESTING_AND_VERIFICATION.md) và [FINAL_PROJECT_REPORT](../FINAL_PROJECT_REPORT.md). Make thêm `deploy-init`, `deploy-build`, `deploy-up`, `deploy-down`, `deploy-check`, `deploy-status`, `deploy-backup`; `DEPLOY_ENV` mặc định `.env.deploy`. Nếu thiếu Make, gọi CLI trực tiếp. Không chạy integration trên DB serving. Các workflow Phase11 dưới đây tiếp tục dùng cho development/QA.

**Workflow hiện hành Phase11:** [TEST_STRATEGY](../testing/TEST_STRATEGY.md) thay hướng dẫn integration trên DB phục vụ trong snapshot cũ bên dưới. `make test-integration` dựng QA rồi chạy service tests; `make test-containers` chạy QA backend fast/services và frontend local; `make test-e2e` dùng QA browser rỗng. `make test-unit` gồm unit/security/reliability và evaluation extra. Guard từ chối integration nếu không có flag/host/database QA. Với Docker Snap dùng `QA_USE_SG=1 make test-integration`. Không dùng verifier cũ trên DB serving để regression. `qa-up` không tải model; AI dùng `scripts/qa.py up --with-model` và cache có sẵn. Chưa tự triển khai Phase12.

Prompt 03 · 2026-11-03. Tuân thủ [ENGINEERING_STANDARDS](../architecture/ENGINEERING_STANDARDS.md) và baseline thiết kế. Chỉ triển khai health/config/connectivity/schema foundation; không implement ingestion/retrieval trước phase tương ứng.

## 1. Commands thực tế

| Make target | Command tương đương / ý nghĩa |
| --- | --- |
| make env | python3 scripts/init_env.py; không overwrite secrets |
| make check | bash scripts/checks/check_environment.sh |
| make up / down | docker compose up -d --build / docker compose down; giữ volumes |
| make logs | docker compose logs --tail=100 -f |
| make test | Backend unit + frontend tests; không tự giả integration pass |
| make test-unit | uv run --project backend --extra dev --frozen pytest backend/tests/unit |
| make test-frontend | npm --prefix frontend test |
| make test-containers | Backend unit/integration/Ruff và frontend type/lint/unit/build bằng docker compose exec |
| make test-e2e | Playwright desktop/mobile qua run_local.py với API_TOKEN từ .env |
| make test-integration | docker compose exec -e RUN_INTEGRATION=1 backend pytest backend/tests/integration -p no:cacheprovider |
| make lint | Ruff lint + format check, TypeScript strict, ESLint |
| make format | Ruff fix/format và Prettier frontend |
| make migrate | docker compose exec backend alembic -c backend/alembic.ini upgrade head |
| make health | bash scripts/checks/verify_services.sh; kiểm tra response semantics, exit nonzero nếu fail |
| make clean | Chỉ thông báo; không xóa generated data/volumes |

Không có Make thì chạy các command tương đương. Không có uv thì cài theo SETUP; `backend/.venv/bin/python` và các executable tương ứng có thể dùng trực tiếp sau khi environment đã được sync. Không cần PyTorch/Transformers ở phase này.

## 2. Test layers và môi trường

`backend/tests/unit` kiểm tra invalid config, secret repr, error envelopes, request IDs, CORS, auth, health modes, complete-send timer, lifecycle cleanup, aggregate dependency failures/timeouts, private bucket policy và offline migration SQL. Doubles được ghi rõ trong fixture; không dùng chúng để claim real connectivity.

`backend/tests/integration` mặc định skip khi thiếu RUN_INTEGRATION=1. Khi bật, failures thật không bị đổi thành skip. Tests kết nối PG/Qdrant/MinIO thật, gọi real readiness, tạo database `foundation_test_<uuid>` riêng để upgrade/compare ORM/downgrade/drop. Principal PG test cần CREATE DATABASE; không cấp quyền đó cho public application role tương lai. Không chạy rollback trên DB ứng dụng. Với services native và env file đúng:

```bash
uv run --project backend python scripts/run_local.py --env-file .env.host -- env RUN_INTEGRATION=1 backend/.venv/bin/pytest backend/tests/integration -q
```

Frontend Vitest/Testing Library dùng jsdom với network mocks cho unit tests. Playwright E2E bổ sung dùng browser Chromium thật ở1440×1000 và390×844, API thật, không route mocks: kiểm tra ready status, disabled search/no search calls, decode/clear preview, không tràn viewport và diagnostics không local/sessionStorage. Screenshots được kiểm tra trực quan; full cross-browser matrix vẫn thuộc Prompt10/11. Trace tắt để tránh lưu credentials.

## 3. API/lifecycle và observability

Factory entrypoint `app.main:create_app --factory` tránh tạo clients tại import. Lifespan tạo SQLAlchemy async engine/session pool, AsyncQdrantClient, MinIO SDK wrapper rồi close khi shutdown. MinIO blocking I/O có executor/slot caps và HTTP timeouts; caller cancel không trả slot sớm khi I/O còn chạy. Dev bucket auto-create private, không thay policy của bucket hiện hữu.

Pure ASGI middleware nhận/generate UUID request ID, enforce total deadline và ghi JSON access event. Timer bắt đầu trước body parse, chốt ngay sau final-body send; không cộng background work sau response. Aborted/incomplete response và error_category được ghi riêng. Log không chứa query string, Authorization, raw inputs, URL credentials hoặc stack của SDK. X-Request-ID được echo/expose CORS. Không dùng uvicorn access log mặc định vì nó có thể chứa query string; dùng `--no-access-log`.

Extension points sau này: thêm request-correlated spans ở encoder/vector/filter/rerank/metadata/tools/generator, không fabricate stage values hiện chưa có. Full response duration chỉ biết sau send, không nhét số pre-serialization vào response rồi gọi đó full latency.

## 4. Dependency và schema changes

Backend dùng pyproject + uv.lock; frontend direct versions exact + package-lock. Sau thay dependency, cập nhật lock có chủ đích rồi chạy checks liên quan. Không npm audit fix --force nếu chưa review compatibility. Frontend runtime và dev dependency audits tách riêng; unresolved advisories được ghi tại PHASE03_REPORT.

Override minimatch11.0.1 vá GHSA-g3hv-75wg-m249 cho ba consumers dùng API hiện đại. Đã so semantics của7 glob patterns qua functional/class APIs trên9 paths với phiên bản10.2.6 trước đó, rồi chạy TypeScript/ESLint/unit/build. Theo dõi và gỡ override khi upstream dependency ranges có bản vá phù hợp; không suy ra full upstream compatibility từ các fixture của project.

`scripts/verification/verify_containers.py` là bộ nghiệm thu thật, không thay unit doubles bằng fake Docker status. Nó có thay đổi trạng thái local stack (recreate/stop/restore), giữ dữ liệu volumes và dùng markers UUID riêng. Report JSON chỉ ghi status/checks/service/volume names, không dump env/inspect Config.Env hoặc Bearer token. Container backend đóng gói cả scripts, `.env.example` và root Ruff config để tests chạy được như trên host.

Alembic migration là snapshot bất biến, không import `Base.metadata.create_all` từ model hiện tại để upgrade quá khứ. Model/thêm schema cần revision mới và upgrade/downgrade/metadata comparison tests. `updated_at` được ORM cập nhật, chưa có DB trigger; external SQL writers tương lai phải cập nhật timestamp/revision theo contract. Metadata/embedding registry chưa có semantic processing hoặc activation.

## 5. Ranh giới bảo mật local

Đọc .env bằng Settings/helper, không echo hoặc source qua shell. Frontend VITE_* không chứa secrets. Local opaque token hiện chỉ bảo vệ các read diagnostics endpoints; chưa có writes/users/tenants. Data services private, data ports chỉ mở loopback qua override explicit. CORS không là authorization, backend vẫn kiểm tra token.

Production yêu cầu scoped application credentials, auth/user policy phù hợp, TLS, shared rate/admission enforcement, backup/restore/retention và dependency hardening. Các điều đó không được coi hoàn thành bởi dev Compose. Không download/model-load hoặc tạo arbitrary vector dimension trong health probes.

## 6. Prompt 04 prerequisites

Cần chọn corpus/rights/privacy, pinned CLIP checkpoint/processor/license, hardware/device/limits; tạo immutable manifest với dimension thực. Bổ sung item/attempt/object/embedding/active-index schema, durable worker, idempotency/retry/fencing/reconciliation và real-image tests. Giữ health/live độc lập và search capability false tới khi engine thực sự sẵn sàng. Không tự bắt đầu Prompt04 từ các commands foundation.

## 7. Pipeline tests Prompt 04

`python3 scripts/verification/verify_indexing.py` là full Docker acceptance, cần model/dataset/index chuẩn bị theo IMAGE_INDEXING. Backend unit dùng decode/numeric fixtures thật và doubles riêng khi cần; `RUN_INDEXING_E2E=1` bật test dùng CLIP + data services thật. Test thực hiện HTTP upload/content/job pagination, injected transient MinIO/Qdrant failure, stale lease/non-publish, invalid input isolation, repair missing vector và reindex old/new collections. Fault injection không được mô tả là actual daemon outage; inference và persistence vẫn thật.

Native tests cần extra ml và env host URLs: `uv run --project backend --extra dev --extra ml python scripts/run_local.py --env-file .env.host -- env RUN_INTEGRATION=1 RUN_INDEXING_E2E=1 backend/.venv/bin/pytest backend/tests/unit backend/tests/integration -q`. Worker launcher và scripts được Ruff/format; không dùng test skips làm bằng chứng real-model pass.

## 8. Search Prompt05

Commands/activation tại [SEMANTIC_SEARCH](../features/SEMANTIC_SEARCH.md); full verifier `python3 scripts/verification/verify_search.py`, benchmark wrapper `bash scripts/evaluation/benchmark_search.sh text|image`. Real integration opt-in RUN_SEARCH_E2E=1 cần active index/cache; tests giữ indexed corpus và cleanup chỉ isolated incompatible test collection. Unit fixture metrics không là actual quality.

API image giờ có extra ml. Query decoder đã preload/Pipe JSON+RGB reuse hàm P04, không thay image manifest; unit tests kiểm pixel equivalence/error/restart. Full-response metrics join ASGI request ID, không dùng response processing field để claim P90 API. Reranking/fusion/agent chưa triển khai.

## 9. Verification và research Prompt06

`bash scripts/verification/verify_advanced_search.sh` hoặc `make verify-advanced-search` reuse verifier nền, bật RUN_ADVANCED_E2E và ghi docs/verification/phase06. Chạy build, full backend tests, lint/format, frontend type/lint/unit/build, browser, E1–E5 latency và verify index không đổi. --skip-build/--skip-browser/--skip-benchmark chỉ dùng khi báo rõ skipped scope; không dùng để khẳng định full acceptance.

Actual advanced integration test dùng same CLIP/index, có metadata AND/OR, semantic UNKNOWN/strict refusal, auth/private content, rerank runtime failure/timeout fixtures và no query-ingest writes. Failure fixtures monkeypatch chỉ reranker/timing trong app, vẫn dùng thật model và ba stores; không coi fixtures là real dependency outage benchmark.

Quality tools ở evaluation/scripts/evaluate_advanced.py yêu cầu exhaustive human labels trước HTTP calls; template false phải bị từ chối. Không tự gán relevance theo model/filename hoặc dùng unit fixtures làm corpus judgments. Xem [evaluation](../../evaluation/README.md) và [report](../archive/ADVANCED_SEARCH_TEST_REPORT.md).

## Evaluation Prompt07

`make verify-evaluation` chạy functional regressions/model/store/browser thật; scientific matrix chạy riêng bằng `scripts/evaluation/run_evaluation_suite.py --optimization --matrix`. Script matrix recreate backend ngắn khi đổi width và khôi phục width ban đầu; cần quyền Docker. `make benchmark-evaluation` đo500 request fast với cấu hình hiện tại. Không chạy unit/integration/model jobs đồng thời với các phép đo latency cần so sánh. `make annotate-evaluation` tạo HTML local chứa ảnh thật, không token. Source/data/query/labels phải freeze và giữ experiment IDs khi báo kết quả; không sửa raw results. [CLI và tái lập](../../evaluation/README.md), [nghiệm thu](../archive/PHASE07_TEST_REPORT.md).

## Cập nhật triển khai Prompt08

Đã có RAG metadata tùy chọn, tái sử dụng SearchService/active CLIP, batch evidence validation/current IDs, bounded context/prompts, Gemini/OpenAI-compatible adapter, citation validation, JSON/SSE và React explanation panel. Không gửi ảnh sang provider hoặc thay Fast Search/ranking. Gemini key ở backend; generator tắt/lỗi giữ ảnh. Với corpus10 ảnh không caption/tags, chưa thể xác minh nội dung thị giác. [Kiến trúc](../features/RAG_ARCHITECTURE.md), [API hiện hành](../features/RAG_API.md), [cấu hình](../features/RAG_IMPLEMENTATION.md), [đánh giá](../research/RAG_EVALUATION.md), [nghiệm thu A–L](../archive/PHASE08_TEST_REPORT.md). Không triển khai Prompt09.
