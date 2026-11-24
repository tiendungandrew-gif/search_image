# Snapshot README trước chuẩn hóa repository

> Tài liệu lịch sử theo phase; lệnh trong nội dung giữ tên đường dẫn cũ. Hướng dẫn hiện hành tại [danh mục tài liệu](../README.md) và [scripts](../../scripts/README.md).

Các lệnh dưới đây giữ lịch sử. Hướng dẫn hiện hành tại [README](../../README.md) và [docs](../README.md).

# AI Multimodal Image Search System

Nền tảng tìm kiếm ảnh bằng văn bản, ảnh tham chiếu và kết hợp hai modality. Đã triển khai indexing, CLIP search, multimodal/multi-intent, framework đánh giá, RAG qua Gemini và Agent multi-hop có nguồn. **Phase 10 đã tích hợp giao diện Lens:** upload kéo thả, bộ lọc, gallery/chi tiết ảnh private, giải thích streaming, tiến độ Agent, dataset status và dashboard benchmark. Giao diện xử lý cả dữ liệu thật lẫn dataset rỗng. Snapshot nghiệm thu 07/11/2026 có 513 ảnh/vector, 4 thực thể và 3 quan hệ địa danh có nguồn; **chất lượng ngữ nghĩa/faithfulness vẫn chờ nhãn người đánh giá**.

**Phase 12 — bàn giao cuối:** đã có Docker images production, frontend static/Nginx, Compose riêng, bootstrap/worker, import sau triển khai, backup/restore và update/rollback. Trạng thái `READY_WITH_LIMITATIONS`, phạm vi kiểm chứng local với dữ liệu tổng hợp và CLIP CPU thật. Xem [báo cáo A–T](../../docs/FINAL_PROJECT_REPORT.md), [bàn giao](../../docs/FINAL_HANDOVER.md), [kiến trúc cuối](../../docs/architecture/FINAL_SYSTEM_ARCHITECTURE.md). Dữ liệu chính513 ảnh vẫn được giữ riêng; chưa triển khai máy chủ public, chưa có nhãn chất lượng do người đánh giá xác nhận.

## Triển khai bản bàn giao

Cần Python3.11+ trên Linux, Docker Engine/Compose và quyền Docker. Từ repository root:

```bash
python3 scripts/deploy.py init
python3 scripts/deploy.py validate
python3 scripts/deploy.py build
python3 scripts/deploy.py up
python3 scripts/deploy.py check
```

Mở http://127.0.0.1:8080; nhập read token từ `.env.deploy` tại máy quản trị. `init` sinh secrets riêng0600, không ghi đè `.env`. App khởi động khi chưa có ảnh/model/provider; không tự tải weights. `python3 scripts/deploy.py down` giữ volumes. Trên Docker Snap của máy kiểm chứng cần `DEPLOY_USE_SG=1` và cấu hình compatibility đã ghi tại [DEPLOYMENT_GUIDE](../../docs/operations/DEPLOYMENT_GUIDE.md); template hardening mặc định được giữ cho máy chủ phù hợp.

- [Cấu hình](../../docs/operations/CONFIGURATION_REFERENCE.md), [model](../../docs/operations/MODEL_MANAGEMENT.md), [thêm dataset](../../docs/operations/DATASET_IMPORT_GUIDE.md).
- [Vận hành](../../docs/operations/OPERATIONS_RUNBOOK.md), [backup/restore](../../docs/operations/BACKUP_AND_RECOVERY.md), [bảo mật/public TLS](../../docs/operations/SECURITY_DEPLOYMENT.md).
- [Kiểm thử bản bàn giao](../../docs/operations/TESTING_AND_VERIFICATION.md), [kiểm toán thay đổi](../../docs/archive/DEPLOYMENT_AUDIT.md).

Các hướng dẫn theo Phase 03–11 bên dưới giữ làm lịch sử và development. Bản triển khai mới dùng `scripts/deploy.py` cùng `compose.prod.yaml`, không dùng Vite development server làm ingress production. [Báo cáo Phase11](../../docs/archive/PHASE11_TEST_REPORT.md) lưu nguyên các bằng chứng QA và benchmark trước bàn giao.

## Kiểm thử QA cô lập

```bash
python3 scripts/qa.py up
python3 scripts/qa.py fast
python3 scripts/qa.py services
python3 scripts/qa.py frontend
python3 scripts/qa.py browser
python3 scripts/qa.py down
```

QA dùng `.env.qa`, database/collections/buckets/volumes riêng và ports8011/5175. `down` ở runner chỉ dọn QA. Docker Snap trên máy hiện tại cần prefix `QA_USE_SG=1`. Model thật, seed, mock browser và fault profiles xem [TEST_STRATEGY](../../docs/testing/TEST_STRATEGY.md); dùng `--with-model` chỉ khi đã có CLIP cache. `make test-integration`/`test-e2e` nay dùng QA, không chạy tests trên DB phục vụ. Các lệnh verifier của phase cũ bên dưới giữ làm lịch sử; không dùng để thay QA cô lập hiện hành.

## Kiến trúc

Modular monolith: React → FastAPI → application services/adapters → PostgreSQL, Qdrant, MinIO private. Worker cùng codebase đã triển khai ở Phase 04, semantic search đã triển khai ở Phase 05. CLIP weights tải có chủ đích và dimension được xác minh từ model thật; không dùng placeholder vectors.

- [Thiết kế hệ thống](../../docs/architecture/SYSTEM_ARCHITECTURE.md), [database](../../docs/architecture/DATABASE_DESIGN.md), [API](../../docs/architecture/API_SPECIFICATION.md).
- [Hướng dẫn Linux và cài prerequisites](../../docs/operations/SETUP.md).
- [Commands, kiểm thử và quy ước phát triển](../../docs/operations/DEVELOPMENT.md).
- [Kết quả kiểm chứng Phase 03 và giới hạn](../../docs/archive/PHASE03_REPORT.md).
- [Nghiệm thu Phase 07 và báo cáo A–M](../../docs/archive/PHASE07_TEST_REPORT.md), [số liệu thực nghiệm](../../docs/research/EXPERIMENT_RESULTS.md).
- [Nghiệm thu Phase 10 A–P](../../docs/archive/PHASE10_TEST_REPORT.md), [kiến trúc frontend](../../docs/features/FRONTEND_ARCHITECTURE.md), [UI/UX](../../docs/features/UI_UX_DESIGN.md), [kiểm thử](../../docs/testing/FRONTEND_TESTING.md).

## Chạy nhanh với Docker

Cần Python3, Git, Docker Engine/Compose v2; Node/npm/uv/Make cần cho workflow native. Phiên bản dùng phát triển: Python3.12, Node22.23.4, npm11.21.1, uv0.13.7. Không giả định chúng đã được cài:

```bash
bash scripts/check_environment.sh
python3 scripts/init_env.py
docker compose config --quiet
docker compose up -d --build
bash scripts/verify_services.sh
```

`init_env.py` sinh secrets ngẫu nhiên vào `.env` mode0600, không in hoặc ghi đè file đã có. Không commit `.env`, không đưa backend secrets vào `VITE_*`. Build MinIO lần đầu cần tải Go modules vì upstream image/archive không khả dụng trong lượt kiểm chứng; Dockerfile pin official source commit và tar SHA-256.

| Địa chỉ local | Chức năng |
| --- | --- |
| http://localhost:5173 | Frontend, preview ảnh local và health API thật |
| http://localhost:8000/api/v1/health/live | Process liveness công khai, không query dependencies |
| http://localhost:8000/api/v1/health/ready | Infrastructure readiness, cần Bearer token |
| http://localhost:8000/docs | Swagger/OpenAPI của endpoints đã triển khai |
| http://localhost:8000/openapi.json | OpenAPI JSON |

Không publish ports PostgreSQL/Qdrant/MinIO mặc định. Browser gọi `/api/v1` qua Vite proxy; hostname `backend`/`postgres` chỉ dùng giữa containers. `/health/ready` chưa kiểm tra search model/index. `/health?check=search` chỉ trả200 khi paired encoder/active index và required stores thực sự ready; offline index riêng chưa đủ.

## Kiểm thử

```bash
uv sync --project backend --extra dev --frozen
npm --prefix frontend ci
make test
make lint
make migrate
make test-integration
make health
```

Không có Make thì dùng runner QA phía trên. Unit tests dùng doubles được ghi rõ; integration yêu cầu `QA_ISOLATED=1`, host/database QA và opt-in flag được runner thiết lập. Không chạy pytest integration trực tiếp trên DB phục vụ. Migration rollback test tạo database riêng, không downgrade database ứng dụng. Source/package locks nằm `backend/uv.lock` và `frontend/package-lock.json`.

## Dừng và troubleshooting

`docker compose down` dừng services nhưng giữ named volumes. `make clean` không xóa dữ liệu. Xem SETUP cho native development, lỗi Docker socket, auth401, readiness503, `.env` sai hostnames, private bucket và password của volume đã tồn tại.

Compose profile này dành cho local development, không phải deployment đã harden cho public. Kết quả build/start, tests và giới hạn hiện tại nằm tại PHASE03_REPORT. Git đã có lịch sử trên nhánh `main`; kiểm tra `git status` để review các thay đổi local trước khi commit.

## Nghiệm thu Docker và trình duyệt

```bash
# Build/start, test, recreate giữ volumes và stop/restore từng dependency của project.
python3 scripts/verify_containers.py

# Browser tests trên stack đã khởi động; API_TOKEN được lấy từ .env cho child process.
cd frontend
npm exec -- playwright install chromium
cd ..
make test-e2e
```

Report máy đọc được: `docs/verification/docker.json`. Browser tests có desktop1440px/mobile390px, preview local, readiness thật và không gửi search chưa triển khai. `make test-containers` chạy riêng tests/static/build trong images hiện tại. Bộ outage/recreate dành cho local development: test markers có namespace UUID riêng và được dọn sau lượt kiểm tra; không thêm image/vector giả.

## Nhập ảnh và lập chỉ mục — Phase 04

Xem [IMAGE_INDEXING](../../docs/features/IMAGE_INDEXING.md) cho toàn bộ lệnh tải model/sample dataset, register index, chạy worker, upload API, inspect/retry/reindex/verify. [EMBEDDING_MODELS](../../docs/features/EMBEDDING_MODELS.md) ghi pinned CLIP revision và preprocessing; [VECTOR_INDEX_DESIGN](../../docs/features/VECTOR_INDEX_DESIGN.md) ghi compatibility/consistency; [INDEXING_TEST_REPORT](../../docs/archive/INDEXING_TEST_REPORT.md) ghi kết quả thực tế.

Profile Compose `indexing` thêm worker process dùng cùng backend package. Mutation APIs yêu cầu WRITE_API_TOKEN riêng và Idempotency-Key; read token không cấp quyền ghi. API không nạp Torch/model và không thực hiện embedding trong request. Model/sample downloads có chủ đích; tests không tự download. Không dùng dữ liệu chưa có quyền/privacy approval.

## Semantic Search — Phase 05

Sau khi có index ready, thực hiện activation/model preload theo [SEMANTIC_SEARCH](../../docs/features/SEMANTIC_SEARCH.md), đặt SEARCH_ENABLED=true và khởi động lại backend. Mở http://localhost:5173, nhập read token trong Token truy cập rồi tìm bằng text hoặc reference image. Query uploads không vào dataset; kết quả/ảnh đọc từ PG/Qdrant/MinIO thật. Không đưa token vào VITE_* hoặc image URLs.

[SEARCH_API](../../docs/features/SEARCH_API.md) ghi JSON/multipart canonical + aliases; [SEARCH_PERFORMANCE](../../docs/research/SEARCH_PERFORMANCE.md) ghi full-server/client latency boundaries và benchmark commands; [SEARCH_TEST_REPORT](../../docs/archive/SEARCH_TEST_REPORT.md) ghi actual tests/quality/performance limits. `bash scripts/verify_search.sh` chạy full acceptance, `bash scripts/benchmark_search.sh text` hoặc `image` chạy baseline. Chưa có human-verified qrels; không suy ra Recall@10 từ smoke queries.

## Multimodal và multi-intent — Phase 06

Trong UI chọn Tự động, Văn bản + Hình ảnh hoặc Nhiều điều kiện; mở Tùy chọn tìm kiếm nâng cao để chọn RRF/weighted score, trọng số văn bản/ảnh và reranking. Điểm không là xác suất; điều kiện thị giác chưa được xác minh sẽ ghi rõ. Không tự ingest ảnh query.

```bash
bash scripts/verify_advanced_search.sh --requests 100
bash scripts/benchmark_search.sh multi_intent --requests 100 --rerank
bash scripts/benchmark_search.sh multimodal --requests 100 --fusion weighted_score --rerank
```

Verifier cần host backend venv, Docker access, Node/npm/Playwright Chromium theo SETUP; script đọc token từ .env vào child environment, không yêu cầu dán token vào CLI. Core đã active từ Phase 05 thì không cần reindex/migration. Các flags MULTIMODAL_ENABLED/MULTI_INTENT_ENABLED/RERANKING_ENABLED mặc địnhtrue khi SEARCH_ENABLED bật; request rerank vẫn off mặc định. [Multimodal](../../docs/features/MULTIMODAL_SEARCH.md), [Multi-intent](../../docs/features/MULTI_INTENT_SEARCH.md), [Reranking](../../docs/features/RERANKING_DESIGN.md), [API](../../docs/features/ADVANCED_SEARCH_API.md), [Test report](../../docs/archive/ADVANCED_SEARCH_TEST_REPORT.md).

## Đánh giá và benchmark Phase 07

Cần stack/index CLIP đã sẵn sàng theo Phase 04–06; dùng cùng snapshot10 ảnh và28 query. Kết quả được ghi vào thư mục experiment mới, không ghi đè các phase trước.

```bash
uv sync --project backend --extra dev --extra ml --extra evaluation --frozen
backend/.venv/bin/python scripts/run_local.py --env-file .env -- backend/.venv/bin/python -m app.cli.evaluation validate-dataset
make annotate-evaluation
make benchmark-evaluation
bash scripts/run_evaluation_container.sh clip
bash scripts/run_evaluation_container.sh siglip2
bash scripts/run_evaluation_container.sh profile
make verify-evaluation
MPLCONFIGDIR=.cache/matplotlib backend/.venv/bin/python -m app.cli.evaluation report --output evaluation/reports/new_run
```

Tải SigLIP một lần bằng `backend/.venv/bin/python -m app.cli.download_evaluation_model --output .cache/siglip2` trước model comparison; không đổi active index. Các lệnh container cần quyền Docker. Nếu shell chưa nhận nhóm, dùng `sg docker -c 'LỆNH'`. Trang `.cache/evaluation/annotation.html` mở offline để gán nhãn24 query; xuất bản nháp trước khi đóng. Không có nhãn thì chỉ chấm4 ca exact identity, giữ các điểm relevance ở trạng thái chưa đo.

Xem [hướng dẫn CLI](../../evaluation/README.md), [protocol gán nhãn](../../docs/research/DATASET_AND_GROUND_TRUTH.md), [report tự sinh](../../evaluation/reports/phase07/REPORT.md). Mục tiêu P90≤300ms đã quan sát ở tải một client/corpus10; lỗi quá tải ở5–20 clients vẫn được báo. Chưa tự chuyển Phase 08.

## RAG tùy chọn — Phase 08

Sau khi tìm ảnh, nút **Giải thích bằng AI** gọi backend để đọc lại evidence thật; không tự gọi LLM mỗi lần search. Corpus hiện có510 ảnh, gồm500 ảnh COCO có caption gốc và10 ảnh mẫu cũ. RAG trích dẫn mô tả đã lưu; câu hỏi không có evidence vẫn báo thiếu thông tin. Khi AI lỗi có thể chọn **Thử lại giải thích**; kết quả ảnh vẫn được giữ. [Tải/nhập dữ liệu và trang đánh giá offline](../../docs/research/RAG_DATASET.md).

```env
RAG_ENABLED=true
RAG_MODEL_PROVIDER=gemini
RAG_MODEL_ID=gemini-3.5-flash-lite
RAG_MODEL_ENDPOINT=https://generativelanguage.googleapis.com/v1beta
RAG_GEMINI_API_STYLE=native
RAG_REASONING_EFFORT=minimal
RAG_API_KEY=
```

Điền key trong .env, hoặc dùng GEMINI_API_KEY đã có. Không đặt key vào frontend/URL/chat. OpenAI và self-hosted compatible endpoint có adapter cấu hình riêng tại [RAG_IMPLEMENTATION](../../docs/features/RAG_IMPLEMENTATION.md); nghiệm thu thật hiện dùng Gemini. RAG_ENABLED=false giữ Semantic Search hoạt động.

```bash
docker compose build backend indexing-worker frontend
docker compose up -d --wait backend frontend
bash scripts/verify_rag.sh
backend/.venv/bin/python scripts/run_local.py --env-file .env -- backend/.venv/bin/python -m app.cli.rag --requests 20
backend/.venv/bin/python scripts/verify_rag_fallback.py
```

Lệnh fallback recreate API ngắn để thử RAG disabled/connection failure/timeout, rồi khôi phục cấu hình RAG ban đầu. Báo cáo A–L: [PHASE08_TEST_REPORT](../../docs/archive/PHASE08_TEST_REPORT.md); [API](../../docs/features/RAG_API.md), [phương pháp](../../docs/research/RAG_EVALUATION.md), [hiệu năng](../../docs/research/RAG_PERFORMANCE.md). Không tự bắt đầu Phase 09.

[Báo cáo RAG ngày05/11 và CSV/biểu đồ](../../evaluation/reports/phase08_20261105/REPORT.md) giữ nguyên lịch sử timeout và corpus10 ảnh. Ngày06/11 đã bổ sung corpus caption, retry UI và kiểm thử trên510 ảnh; kết quả hiện hành nằm trong [báo cáo Phase 08](../../docs/archive/PHASE08_TEST_REPORT.md). Người dùng chọn giữ mục human quality review chờ xác nhận; không coi citation checks là chất lượng ngữ nghĩa đã được đánh giá.

[Báo cáo nghiệm thu06/11](../../docs/archive/PHASE08_COMPLETION_REPORT.md), [CSV/biểu đồ hiện hành](../../evaluation/reports/phase08_20261106/REPORT.md).

## Agent và tìm kiếm nhiều bước — Phase 09

Chọn **Agent** tại http://localhost:5173, nhập read token, thử `a dog outdoors`; có thể bật giải thích hoặc chọn LLM planning khi backend cấu hình. Truy vấn địa danh theo quan hệ sẽ trả thiếu bằng chứng cho tới khi nhập facts và image associations có nguồn. Có510 ảnh thực indexed,500 captions; fixture knowledge không được nhập vào serving DB.

```bash
# Migration cộng thêm ba bảng, giữ dữ liệu hiện có.
docker compose run --rm backend alembic upgrade head
docker compose up -d --build backend frontend
bash scripts/verify_agent.sh --output docs/verification/phase09/new_run
```

Flags và cách chạy empty dataset tại [SETUP](../../docs/operations/SETUP.md); [kiến trúc](../../docs/features/AGENT_ARCHITECTURE.md), [API](../../docs/features/AGENT_API.md), [knowledge/import](../../docs/features/KNOWLEDGE_BASE_DESIGN.md), [benchmark](../../docs/research/AGENT_PERFORMANCE.md), [nghiệm thu](../../docs/archive/PHASE09_TEST_REPORT.md). Agent mặc định tắt trong template, deterministic không cần LLM; full verification dùng cấu hình/corpus local mô tả trong báo cáo. Human relevance/faithfulness và multi-hop chất lượng thực chưa được nghiệm thu. Đây là snapshot nghiệm thu Phase 09; cập nhật hiện hành ở phần Phase 10.

## Hoàn thiện Phase 09 với dữ liệu địa danh thật

Hiện có **513 ảnh**, gồm510 ảnh trước đó và3 ảnh NPS public-domain có nguồn; knowledge4 entities/3 relations/3 image links. Index510 ảnh cũ vẫn giữ nguyên. Chọn Agent và thử `Find landmarks in the city where Washington Monument is located`, hoặc `Tìm ảnh địa danh ở thành phố nơi Washington Monument tọa lạc`. Mở “Nguồn quan hệ” để đối chiếu NPS; optional Gemini planning/RAG vẫn theo flags trong .env.

[Nguồn và cách nhập dataset](../../docs/research/PUBLIC_LANDMARK_DATASET.md), [báo cáo nghiệm thu hiện hành](../../docs/archive/PHASE09_TEST_REPORT.md). Kiểm tra mới200 backend/21 frontend unit,24 browser full và6 ca browser nhánh cuối đạt; human relevance/faithfulness vẫn chờ, latency3s phải đọc số đo thay vì suy từ timeout. Số liệu trên thuộc mốc Phase 09; xem cập nhật Phase 10 bên dưới.


## Frontend tích hợp — Phase 10

Mở `http://127.0.0.1:5173`, nhập read token từ `.env` vào ô “Token truy cập” (không gửi key vào chat hoặc VITE env). Chọn phương thức, tìm bằng Enter/nút tìm; Shift+Enter xuống dòng. Ảnh query không được thêm vào dataset. Bấm tiêu đề thẻ để xem chi tiết, dùng mũi tên/Escape trong dialog. RAG là thao tác tùy chọn sau khi có kết quả; Agent có chế độ theo mẫu hoặc LLM khi được cấu hình.

Trang `/evaluation` đọc số liệu tổng hợp có xác thực. Compose mount `evaluation/results` read-only; thiếu artifact thì hiển thị trạng thái chưa có benchmark. Dataset status cập nhật mỗi 30 giây khi tab hiện hoặc bằng nút refresh; nhập dữ liệu qua CLI/worker hiện có không cần sửa frontend.

```bash
# Chạy stack chính, giữ volumes dữ liệu.
docker compose up -d --build
# Kiểm tra frontend bằng Node/npm đã cài trong môi trường.
npm --prefix frontend run typecheck
npm --prefix frontend run lint
npm --prefix frontend test
npm --prefix frontend run build
# E2E chỉ trên stack chính (Chromium/Firefox/WebKit đã cài bằng Playwright).
RUN_RAG_E2E=1 RUN_AGENT_E2E=1 RUN_AGENT_PUBLIC_DATA=1 \
  backend/.venv/bin/python scripts/check_frontend.py \
  --project=desktop --project=mobile --project=tablet --project=firefox --project=webkit
```

Fixture backend rỗng và các lệnh đầy đủ ở [FRONTEND_EMPTY_DATASET_MODE.md](../../docs/features/FRONTEND_EMPTY_DATASET_MODE.md); [FRONTEND_TESTING.md](../../docs/testing/FRONTEND_TESTING.md) phân biệt mock, real API, real data, accessibility và giới hạn thiết bị thật. Snapshot kiểm thử: 40 frontend unit, 211 backend tests, 72 functional E2E + 2 performance E2E pass. Chỉ theme được lưu trong browser; token, ảnh query và provider key không được lưu vào localStorage. Phase11 chưa được triển khai tự động.
