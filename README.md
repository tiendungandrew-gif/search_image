# AI Multimodal Image Search System

Nền tảng tìm kiếm ảnh bằng văn bản, ảnh tham chiếu và kết hợp hai modality. Đã triển khai indexing, CLIP search, multimodal/multi-intent và framework đánh giá Prompt07 và **RAG tùy chọn Prompt08**. Có công cụ gán nhãn, benchmark/load/profiling, so sánh CLIP/SigLIP 2 và báo cáo thực nghiệm. **Chất lượng tìm kiếm ngữ nghĩa chưa được nghiệm thu vì chưa có nhãn người đánh giá.** RAG đã có API/streaming/giải thích metadata qua Gemini; Agent và multi-hop chưa triển khai.

## Kiến trúc

Modular monolith: React → FastAPI → application services/adapters → PostgreSQL, Qdrant, MinIO private. Worker cùng codebase đã triển khai ở Prompt 04, semantic search đã triển khai ở Prompt05. CLIP weights tải có chủ đích và dimension được xác minh từ model thật; không dùng placeholder vectors.

- [Thiết kế hệ thống](docs/SYSTEM_ARCHITECTURE.md), [database](docs/DATABASE_DESIGN.md), [API](docs/API_SPECIFICATION.md).
- [Hướng dẫn Linux và cài prerequisites](docs/SETUP.md).
- [Commands, kiểm thử và quy ước phát triển](docs/DEVELOPMENT.md).
- [Kết quả kiểm chứng Prompt 03 và giới hạn](docs/PHASE03_REPORT.md).
- [Nghiệm thu Prompt 07 và báo cáo A–M](docs/PHASE07_TEST_REPORT.md), [số liệu thực nghiệm](docs/EXPERIMENT_RESULTS.md).

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

Không có Make thì dùng từng command tại DEVELOPMENT. Unit tests dùng doubles được ghi rõ; integration tests chỉ chạy với services thật và `RUN_INTEGRATION=1`. Migration rollback test tạo database riêng, không downgrade database ứng dụng. Source/package locks nằm `backend/uv.lock` và `frontend/package-lock.json`.

## Dừng và troubleshooting

`docker compose down` dừng services nhưng giữ named volumes. `make clean` không xóa dữ liệu. Xem SETUP cho native development, lỗi Docker socket, auth401, readiness503, `.env` sai hostnames, private bucket và password của volume đã tồn tại.

Compose profile này dành cho local development, không phải deployment đã harden cho public. Kết quả build/start, tests và giới hạn hiện tại nằm tại PHASE03_REPORT. Git đã được khởi tạo nhánh `main` trên host; chưa tạo commit.

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

## Nhập ảnh và lập chỉ mục — Prompt 04

Xem [IMAGE_INDEXING](docs/IMAGE_INDEXING.md) cho toàn bộ lệnh tải model/sample dataset, register index, chạy worker, upload API, inspect/retry/reindex/verify. [EMBEDDING_MODELS](docs/EMBEDDING_MODELS.md) ghi pinned CLIP revision và preprocessing; [VECTOR_INDEX_DESIGN](docs/VECTOR_INDEX_DESIGN.md) ghi compatibility/consistency; [INDEXING_TEST_REPORT](docs/INDEXING_TEST_REPORT.md) ghi kết quả thực tế.

Profile Compose `indexing` thêm worker process dùng cùng backend package. Mutation APIs yêu cầu WRITE_API_TOKEN riêng và Idempotency-Key; read token không cấp quyền ghi. API không nạp Torch/model và không thực hiện embedding trong request. Model/sample downloads có chủ đích; tests không tự download. Không dùng dữ liệu chưa có quyền/privacy approval.

## Semantic Search — Prompt 05

Sau khi có index ready, thực hiện activation/model preload theo [SEMANTIC_SEARCH](docs/SEMANTIC_SEARCH.md), đặt SEARCH_ENABLED=true và khởi động lại backend. Mở http://localhost:5173, nhập read token trong Token truy cập rồi tìm bằng text hoặc reference image. Query uploads không vào dataset; kết quả/ảnh đọc từ PG/Qdrant/MinIO thật. Không đưa token vào VITE_* hoặc image URLs.

[SEARCH_API](docs/SEARCH_API.md) ghi JSON/multipart canonical + aliases; [SEARCH_PERFORMANCE](docs/SEARCH_PERFORMANCE.md) ghi full-server/client latency boundaries và benchmark commands; [SEARCH_TEST_REPORT](docs/SEARCH_TEST_REPORT.md) ghi actual tests/quality/performance limits. `bash scripts/verify_search.sh` chạy full acceptance, `bash scripts/benchmark_search.sh text` hoặc `image` chạy baseline. Chưa có human-verified qrels; không suy ra Recall@10 từ smoke queries.

## Multimodal và multi-intent — Prompt 06

Trong UI chọn Tự động, Văn bản + Hình ảnh hoặc Nhiều điều kiện; mở Tùy chọn tìm kiếm nâng cao để chọn RRF/weighted score, trọng số văn bản/ảnh và reranking. Điểm không là xác suất; điều kiện thị giác chưa được xác minh sẽ ghi rõ. Không tự ingest ảnh query.

```bash
bash scripts/verify_advanced_search.sh --requests 100
bash scripts/benchmark_search.sh multi_intent --requests 100 --rerank
bash scripts/benchmark_search.sh multimodal --requests 100 --fusion weighted_score --rerank
```

Verifier cần host backend venv, Docker access, Node/npm/Playwright Chromium theo SETUP; script đọc token từ .env vào child environment, không yêu cầu dán token vào CLI. Core đã active từ Prompt05 thì không cần reindex/migration. Các flags MULTIMODAL_ENABLED/MULTI_INTENT_ENABLED/RERANKING_ENABLED mặc địnhtrue khi SEARCH_ENABLED bật; request rerank vẫn off mặc định. [Multimodal](docs/MULTIMODAL_SEARCH.md), [Multi-intent](docs/MULTI_INTENT_SEARCH.md), [Reranking](docs/RERANKING_DESIGN.md), [API](docs/ADVANCED_SEARCH_API.md), [Test report](docs/ADVANCED_SEARCH_TEST_REPORT.md).

## Đánh giá và benchmark Prompt 07

Cần stack/index CLIP đã sẵn sàng theo Prompt04–06; dùng cùng snapshot10 ảnh và28 query. Kết quả được ghi vào thư mục experiment mới, không ghi đè các phase trước.

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

Xem [hướng dẫn CLI](evaluation/README.md), [protocol gán nhãn](docs/DATASET_AND_GROUND_TRUTH.md), [report tự sinh](evaluation/reports/phase07/REPORT.md). Mục tiêu P90≤300ms đã quan sát ở tải một client/corpus10; lỗi quá tải ở5–20 clients vẫn được báo. Chưa tự chuyển Prompt08.

## RAG tùy chọn — Prompt08

Sau khi tìm ảnh, nút **Giải thích bằng AI** gọi backend để đọc lại evidence thật; không tự gọi LLM mỗi lần search. Corpus10 ảnh chưa có caption/tags nên câu hỏi về đối tượng/màu/cảnh sẽ báo thiếu bằng chứng. Có thể hỏi về định dạng/kích thước/source metadata đã lưu.

```env
RAG_ENABLED=true
RAG_MODEL_PROVIDER=gemini
RAG_MODEL_ID=gemini-3.5-flash-lite
RAG_MODEL_ENDPOINT=https://generativelanguage.googleapis.com/v1beta
RAG_GEMINI_API_STYLE=native
RAG_REASONING_EFFORT=minimal
RAG_API_KEY=
```

Điền key trong .env, hoặc dùng GEMINI_API_KEY đã có. Không đặt key vào frontend/URL/chat. OpenAI và self-hosted compatible endpoint có adapter cấu hình riêng tại [RAG_IMPLEMENTATION](docs/RAG_IMPLEMENTATION.md); nghiệm thu thật hiện dùng Gemini. RAG_ENABLED=false giữ Semantic Search hoạt động.

```bash
docker compose build backend indexing-worker frontend
docker compose up -d --wait backend frontend
bash scripts/verify_rag.sh
backend/.venv/bin/python scripts/run_local.py --env-file .env -- backend/.venv/bin/python -m app.cli.rag --requests 20
backend/.venv/bin/python scripts/verify_rag_fallback.py
```

Lệnh fallback recreate API ngắn để thử RAG disabled/connection failure/timeout, rồi khôi phục cấu hình RAG ban đầu. Báo cáo A–L: [PHASE08_TEST_REPORT](docs/PHASE08_TEST_REPORT.md); [API](docs/RAG_API.md), [phương pháp](docs/RAG_EVALUATION.md), [hiệu năng](docs/RAG_PERFORMANCE.md). Không tự bắt đầu Prompt09.

[Báo cáo RAG tự sinh và CSV/biểu đồ](evaluation/reports/phase08_20261105/REPORT.md). Trạng thái nghiệm thu hiện chưa toàn bộ pass: provider có timeout/intermittent browser failure và một nhóm RAG vượt target3s; xem PHASE08_TEST_REPORT trước khi suy production readiness.
