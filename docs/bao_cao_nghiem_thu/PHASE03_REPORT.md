# Báo cáo triển khai và nghiệm thu Prompt 03

> Tài liệu lịch sử theo phase; lệnh trong nội dung giữ tên đường dẫn cũ. Hướng dẫn hiện hành tại [danh mục tài liệu](../README.md) và [scripts](../../scripts/README.md).

Ngày 2026-11-03 · Application version 0.3.0 · **Hoàn thành foundation Prompt 03 và nghiệm thu trên Docker thật.** Năm services đang chạy healthy. Prompt 04 chưa bắt đầu.

## 1. Phạm vi đã triển khai

- FastAPI application factory/lifespan, Pydantic Settings v2, restricted CORS, JSON logging, standardized errors, UUID request ID, full-response deadline/timer và đóng clients khi shutdown.
- Async SQLAlchemy/psycopg pool/session, Qdrant async client, MinIO SDK wrapper với bounded executor/timeouts, private bucket và safe dev auto-create.
- Bốn API thật: `/api/v1/health/live`, `/api/v1/health/ready`, `/api/v1/health`, `/api/v1/system/info`; Swagger `/docs` và `/openapi.json`. Readiness/system info yêu cầu local Bearer token. Search health trả unavailable khi chưa có model/index.
- Alembic revision `0001_foundation` và sáu ORM tables: images, image_metadata, embedding_models, indexing_jobs, search_indexes, dataset_sources. Hai bảng cuối giữ approved foreign keys; có upgrade/downgrade, constraints/indexes và PostgreSQL metadata comparison.
- React/TypeScript/Vite/Tailwind responsive: query/mode, local image preview/clear, loading/error/empty states, health API thật và diagnostics giữ token trong memory. Search disabled, không fake results hoặc upload tới endpoint chưa có.
- Compose năm services, private data network, ba named volumes, healthchecks, backend non-root, migration trước Uvicorn và Vite proxy. Khóa versions và dependency trees; không dùng latest.
- Env generator không overwrite, scripts kiểm tra môi trường/services, Make commands, unit/integration/browser tests và tài liệu Linux setup/development.

Không tải AI weights, tạo embedding/vector collection với dimension placeholder, triển khai ingestion, retrieval, RAG, Agent hoặc multi-hop.

## 2. Artifacts và evidence

| Nhóm | Đường dẫn |
| --- | --- |
| Backend | [main.py](../../backend/app/main.py), `backend/app/core/`, `db/`, `integrations/`, `services/`, `schemas/`, `api/v1/` |
| Migration | [0001_foundation.py](../../backend/alembic/versions/0001_foundation.py), [ORM](../../backend/app/db/models/foundation.py) |
| Frontend | `frontend/src/`, [package.json](../../frontend/package.json), [Playwright suite](../../frontend/e2e/foundation.spec.ts) |
| Infrastructure | [compose.yaml](../../compose.yaml), [host override](../../compose.host.yaml), backend/frontend Dockerfiles, [MinIO build](../../infra/docker/minio.Dockerfile) |
| Commands | [Makefile](../../Makefile), [verify_containers.py](../../scripts/verification/verify_containers.py), `scripts/init_env.py`, `run_local.py`, `verify_services.py` và shell wrappers |
| Hướng dẫn | [README](../../README.md), [SETUP](../operations/SETUP.md), [DEVELOPMENT](../operations/DEVELOPMENT.md), [DECISIONS](../architecture/DECISIONS.md) |
| Docker nghiệm thu | [docker.json](../verification/docker.json): build, tests, health, persistence, outage/recovery và cleanup đều pass |
| Browser nghiệm thu | [browser.json](../verification/browser.json): 6 passed, 0 skipped, 0 flaky; [desktop](../verification/desktop.png), [mobile](../verification/mobile.png) đã kiểm tra trực quan |
| Mermaid | [mermaid.json](../verification/mermaid.json), 11 SVG tại `docs/verification/diagrams/` |
| Frontend audit | [frontend_audit.json](../verification/frontend_audit.json): 0 vulnerabilities trong toàn dependency tree tại lượt kiểm tra |

## 3. Môi trường đã kiểm chứng

| Thành phần | Phiên bản/thực thi |
| --- | --- |
| Host | Linux x86_64; Python 3.12.3; Node 22.23.4; npm 11.21.1; uv 0.13.7 |
| Docker | Engine 29.8.0 qua Docker Snap; Compose 5.5.1 |
| Backend image | Python 3.12.12-slim-bookworm; cùng uv.lock |
| Frontend image | Node 22.23.4-bookworm-slim; cùng package-lock.json |
| FastAPI/Pydantic/SQLAlchemy | 0.162.0 / 2.14.2 / 2.0.55 |
| Alembic/psycopg | 1.20.1 / 3.3.6 |
| React/Vite/TypeScript/Tailwind | 19.3.1 / 7.3.7 / 5.9.3 / 4.3.4 |
| Ruff/ESLint/Vitest | 0.17.3 / 10.14.0 / 4.1.12 |
| PostgreSQL | postgres:16.15-bookworm, đã pull/run thật |
| Qdrant | qdrant/qdrant:v1.20.0, đã pull/run thật |
| MinIO | Docker source build commit `07c3a429bfed433e49018cb0f78a52145d4bedeb`, tar checksum pinned, Go 1.25.3, CGO=0; đã build/run thật |
| Browser/diagram tools | Playwright 1.64.1; Chromium 156.0.8078.4; Mermaid CLI 11.17.1 |

MinIO source build hiển thị version `DEVELOPMENT.GOGET`; provenance là commit/checksum và toolchain trong Dockerfile, không suy diễn release binary version từ tag image local. Toolchain và native data tạm trong `/tmp` không phải đường dẫn bắt buộc trên máy khác. Đây là verification local development, chưa là benchmark hardware profile hoặc chứng minh trên một máy sạch độc lập.

## 4. Kết quả kiểm thử thực tế

| Kiểm tra | Kết quả |
| --- | --- |
| Compose config và build/start | PASS; build đủ images, năm containers running/healthy |
| Backend unit trong container | 32 passed |
| Backend integration thật trong container | 3 passed: dependency connections, readiness và disposable PostgreSQL migration upgrade/ORM comparison/downgrade |
| Frontend unit trong container | 8 passed |
| Static checks/build trong container | PASS Ruff check/format, TypeScript strict, ESLint và production Vite build |
| HTTP smoke | PASS liveness, authenticated readiness, OpenAPI, Swagger, UI và frontend→backend proxy |
| Persistence | PASS PG text marker, MinIO private text object và hidden file trong Qdrant volume còn nguyên sau force-recreate cả năm containers; volume names giữ nguyên |
| Dependency failures | PASS stop/restore riêng PG, Qdrant, MinIO: liveness 200, readiness 503 với đúng dependency unavailable/timeout, rồi HTTP smoke hồi phục |
| Marker cleanup | PASS; chỉ dọn schema/object/file thuộc UUID lượt test, không xóa volumes hoặc tạo image/vector giả |
| Chromium E2E trên Docker | 6 passed, 0 skipped: desktop 1440×1000 và mobile 390×844; health thật, disabled search/no search calls, decode/clear preview/no upload, readiness/token không local/sessionStorage, không tràn viewport |
| Mermaid engine | 11/11 sources render thành SVG; sửa ingestion Note chứa semicolon làm parser tách statement |
| npm audit toàn tree | 0 findings sau override minimatch 11.0.1; không đồng nghĩa production hardening đã hoàn tất |
| Git | Project repository hợp lệ, nhánh main, chưa commit/remote/CI; secrets/dependencies/raw browser artifacts được ignore |

Các integration tests có 2 Qdrant SDK warnings do API key qua HTTP local; không coi profile này là TLS production. Container logs có các shutdown/503 dự kiến do outage tests; sau restore services healthy. Native integration/migration và unit/static/build đã qua ở lượt trước; bằng chứng Docker ở lượt này độc lập với native processes.

## 5. Các phần còn thiếu đã xử lý trong lượt bổ sung

1. Quyền socket Docker Snap: thêm nhóm docker và disable/enable Snap theo hướng dẫn Canonical sau khi restart đơn thuần chưa đổi root:root. Dùng group membership trong phiên hiện tại; không chmod666 socket.
2. Backend image bổ sung scripts/, .env.example và root Ruff config để script-safety tests và static checks chạy được trong container.
3. Thêm script nghiệm thu Docker có report JSON, persistence markers UUID riêng, force-recreate và stop/restore dependency trong finally.
4. Sửa mobile form thành cột để mode selector không cắt chữ; bổ sung Playwright E2E chạy với Docker/API thật, trace tắt để tránh lưu auth headers.
5. Khắc phục 12 moderate dev advisories trước đó bằng minimatch 11.0.1. So sánh 7 glob patterns × 9 paths qua functional/class APIs với 10.2.6, rồi chạy TypeScript/ESLint/unit/build. Theo dõi và gỡ override khi upstream phù hợp; fixture project không chứng minh mọi use case của thư viện.
6. Render toàn bộ Mermaid bằng engine; khởi tạo Git main sau khi kiểm tra host .git thực tế rỗng/writable, không overwrite history. Chưa tạo commit.

Các nhận định Docker/Git/browser/audit còn thiếu trong snapshot Prompt 01/02 và quyết định ban đầu là lịch sử; kết quả hiện hành là báo cáo này.

## 6. Checklist nghiệm thu Prompt 03

**Tiến độ: 8/8 mục đạt.** Container/HTTP/migration được kiểm tra lại khi đối chiếu checklist; browser và unit/static results dùng evidence đã lưu ở mục 2–4.

- [x] Docker Compose khởi chạy được các dịch vụ — cả năm containers running/healthy.
- [x] Frontend React hiển thị trên trình duyệt — Chromium desktop/mobile, 6 browser tests passed.
- [x] FastAPI trả kết quả từ `/api/v1/health/live` — HTTP smoke pass.
- [x] Readiness kiểm tra PostgreSQL, Qdrant, MinIO thành công — authenticated readiness pass với dependencies thật.
- [x] Database migration chạy thành công — `0001_foundation (head)`; upgrade/ORM comparison/downgrade trên disposable DB đã qua.
- [x] Frontend gọi được backend — frontend API proxy smoke và browser tests pass.
- [x] Unit tests và các kiểm tra lint/type không có lỗi chưa giải quyết — 32 backend unit, 8 frontend unit; Ruff/format, TypeScript, ESLint và build pass.
- [x] README có hướng dẫn cài đặt và chạy hệ thống — prerequisites, env, Compose startup, URLs, tests và troubleshooting; chi tiết tại SETUP/DEVELOPMENT.

## 7. Tái lập và sử dụng

Từ project root sau khi cài prerequisites và tạo .env theo [SETUP](../operations/SETUP.md):

```bash
python3 scripts/verify_containers.py
cd frontend
npm ci
npm exec -- playwright install chromium
cd ..
make test-e2e
```

`verify_containers.py` cần quyền Docker và chỉ dùng Python standard library trên host. Nó recreate/stop/restore local stack, giữ data volumes và ghi docker.json. `make test-containers` chạy tests/static/build trên images đang có. Browser workflow cần uv/backend dependencies và Node/npm như SETUP. Mermaid CLI có thể dùng riêng khi review diagrams; không là runtime dependency ứng dụng.

Stack Docker được giữ chạy cho nghiệm thu: UI tại http://localhost:5173 và Swagger tại http://localhost:8000/docs. `docker compose down` giữ volumes. Native processes dùng cho lượt kiểm chứng trước đã được dừng; dữ liệu tạm giữ nguyên. Actual .env/.env.native private/ignored, không chứa trong artifacts.

## 8. Giới hạn và bàn giao Prompt 04

- Profile local chưa tách PG/MinIO bootstrap credentials thành least-privilege application accounts; chưa public user/tenant auth, TLS, shared quotas/rate limits hoặc backup hardening. Chưa nghiệm thu public production.
- Browser kiểm tra Chromium ở hai viewport; full cross-browser matrix thuộc phase kiểm thử sau. Chưa kiểm chứng trên máy sạch thứ hai; versions/locks và lệnh tái lập được cung cấp.
- Dataset/rights/privacy, pinned AI checkpoint/license/processor/dimension, hardware/resource envelope và numeric quality gates còn cần chốt trước ingestion/model phases.
- Chưa có Recall@10/P90/P95/TTLast kết quả. Không suy ra retrieval performance từ health/test timings.
- Prompt 04 cần migrations cho items/attempts/objects/embeddings/active-index, durable worker và recovery tests theo DATABASE_DESIGN. Chỉ bắt đầu khi người dùng yêu cầu.

Source/config snapshot và kiểm tra tài liệu cuối được ghi tại [source_snapshot.json](../verification/source_snapshot.json). Snapshot không phải Git commit hash hoặc bằng chứng clean worktree; source hiện chưa commit.
