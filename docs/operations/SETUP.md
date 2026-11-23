# Cài đặt và chạy trên Linux

Từ 19/11/2026, tìm kiếm văn bản mặc định hỗ trợ Việt–Anh. Máy đã có CLIP cần
chuẩn bị thêm model text trong thư mục con `multilingual-text` trước khi restart
backend; xem [lệnh tải model và kiểm chứng](../features/BILINGUAL_SEARCH.md).

Cập nhật tài khoản/UI 08/11/2026: xem [thiết kế quyền](../architecture/ACCESS_CONTROL.md) và [hướng dẫn đăng nhập](../operations/ACCOUNTS.md). Các hướng dẫn dùng data token trước đây chỉ áp dụng khi bật legacy; mặc định mới dùng session tài khoản.
## Bản bàn giao Phase12

Triển khai static frontend và services bằng [DEPLOYMENT_GUIDE](DEPLOYMENT_GUIDE.md); secrets/resources ở [CONFIGURATION_REFERENCE](CONFIGURATION_REFERENCE.md), model ở [MODEL_MANAGEMENT](MODEL_MANAGEMENT.md). `python3 scripts/deploy.py init`, `validate`, `build`, `up`, `check` là các lệnh riêng từ root. App có thể chạy chưa có dữ liệu/model/provider; thêm ảnh theo [DATASET_IMPORT_GUIDE](DATASET_IMPORT_GUIDE.md). Production Compose độc lập với profile development phía dưới. [FINAL_HANDOVER](../FINAL_HANDOVER.md) ghi các giới hạn và lệnh dừng/backup/restore.

## Kiểm thử hiện hành Phase11

Dùng [TEST_STRATEGY](../testing/TEST_STRATEGY.md) và `python3 scripts/qa.py up|fast|services|frontend|browser|down` theo từng lệnh riêng. QA tự sinh `.env.qa` khác `.env`, ports8011/5175, không dùng production credentials. `make test-integration`/`test-e2e` nay trỏ QA. Cấu hình Gemini/model/dataset serving tiếp tục giữ như phần sau, nhưng các verifier mutating của phase cũ không dùng cho regression trên DB phục vụ. [Báo cáo Phase11](../archive/PHASE11_TEST_REPORT.md) nêu số liệu và giới hạn mới nhất; sections dưới giữ lịch sử setup.

## Hoàn thiện Prompt 09 — 06/11/2026

Đã bổ sung bộ địa danh NPS có nguồn:3 ảnh thật,4 entities,3 quan hệ và3 liên kết ảnh. Index phục vụ hiện513 ảnh, generation3; index510 ảnh cũ giữ nguyên. Workflow Anh/Việt/alias, Gemini planner và RAG thật đã được kiểm tra. Planner có trace từng attempt; prompt tools và RAG context đã rút gọn, citation provenance vẫn giữ đầy đủ trên server. Bộ kiểm tra mới đạt200 backend,21 frontend unit và24 browser full tests cùng6 ca browser nhánh cuối. Chất lượng do người đánh giá vẫn chờ; số đo latency và trạng thái target3s xem [báo cáo Prompt09](../archive/PHASE09_TEST_REPORT.md), dữ liệu/nguồn tại [PUBLIC_LANDMARK_DATASET](../research/PUBLIC_LANDMARK_DATASET.md).

## Chạy Agent tùy chọn Prompt09

Giữ cấu hình PG/Qdrant/MinIO và model/index đã có. Mặc định `.env.example` tắt Agent/LLM/RAG để core không phụ thuộc provider. Để bật trên máy local, chỉnh `.env` (không commit):

```dotenv
AGENT_ENABLED=true
AGENT_PLANNER_MODE=deterministic
AGENT_LLM_PLANNING_ENABLED=false
AGENT_RAG_ENABLED=false
AGENT_ALLOW_EMPTY_DATASET=true
AGENT_ALLOW_FIXTURE_KNOWLEDGE=false
```

```bash
docker compose run --rm backend alembic upgrade head
docker compose up -d --build backend frontend
bash scripts/verification/verify_agent.sh --output docs/verification/phase09/new_run
```

Verifier đầy đủ cần flags RAG/LLM và corpus đáp ứng từng gate; bộ fixtures deterministic có thể chạy riêng. Không bật fixture trong serving DB. Muốn thử Gemini planning/explanation, giữ provider/key Phase08 trong `.env`, bật `AGENT_LLM_PLANNING_ENABLED=true`/`AGENT_RAG_ENABLED=true` và RAG config tương ứng rồi restart backend. Không nhập API key vào trình duyệt. Read token ứng dụng nhập trong UI, chọn Agent và deterministic trước. Không có knowledge thì truy vấn quan hệ trả thiếu bằng chứng; semantic query vẫn tìm510 ảnh hiện có. Máy cài mới hoàn toàn có thể `SEARCH_ENABLED=false`, Agent vẫn khởi tạo và hiển thị empty dataset. Xem [AGENT_API](../features/AGENT_API.md), [AGENT_EVALUATION](../research/AGENT_EVALUATION.md), [PHASE09_TEST_REPORT](../archive/PHASE09_TEST_REPORT.md).

Prompt 03/04 · 2026-11-03. Hướng dẫn foundation sau dùng project root. Prompt04 có model/sample downloads explicit; quy trình tại [IMAGE_INDEXING](../features/IMAGE_INDEXING.md). Versions khóa trong uv.lock/package-lock.json.

## 1. Kiểm tra prerequisites

```bash
bash scripts/checks/check_environment.sh
```

Script kiểm tra Python3.11…3.13, Node dòng22 từ22.12, npm, Git, Make, Docker Engine và Compose plugin; thiếu dependency hoặc daemon không truy cập được thì exit khác0. Repository Git chưa hợp lệ được báo riêng, không tự sửa `.git`.

Ubuntu/Debian có thể cài Python/Git/Make bằng package manager của máy:

```bash
sudo apt-get update
sudo apt-get install python3 python3-venv git make wget xz-utils
```

Python3.12 là runtime phát triển chính. Nếu `python3 -m venv` lỗi ensurepip, cài đúng gói `python3-venv`/`python3.12-venv` của distribution; không ghi đè system Python. Docker: theo [hướng dẫn chính thức cho Ubuntu](https://docs.docker.com/engine/install/ubuntu/), gồm Compose v2. Không tự chmod Docker socket hoặc thay group người dùng trong setup script.

Node22.23.4 được ghi trong `.nvmrc`: dùng version manager sẵn có với `nvm install && nvm use`, hoặc tải binary/checksum từ [Node.js distribution](https://nodejs.org/dist/v22.23.4/). Không coi nvm đã cài. Khi dùng Node trong thư mục do mình quản lý, pin npm bằng `npm install --global npm@11.21.1`; không dùng sudo npm trên system prefix. Nếu prefix không writable, cài npm vào thư mục local của riêng mình và dùng CLI tương ứng.

Nếu chưa có uv, bootstrap trong thư mục project:

```bash
python3 -m venv .tools/venv
.tools/venv/bin/python -m pip install uv==0.13.7
export PATH="$PWD/.tools/venv/bin:$PATH"
uv --version
```

Các lệnh cài dependencies cần mạng. Nếu máy bị hạn chế registry, cấu hình proxy/mirror được tổ chức chấp thuận; không bỏ TLS verification. Môi trường kiểm chứng của tác vụ dùng toolchain tạm ở `/tmp`, không yêu cầu các đường dẫn đó để chạy project trên máy khác.

## 2. Môi trường và secrets

```bash
python3 scripts/init_env.py
```

Sinh `.env` mode0600 với passwords/tokens khác nhau, không in secrets; file tồn tại thì fail và giữ nguyên. `.env.example` chỉ là template, các secrets trống khiến validation/Compose fail rõ ràng. Không source `.env` bằng shell vì CORS_ORIGINS là JSON; dùng env_file của Compose hoặc helper run_local.

| Biến | Ý nghĩa |
| --- | --- |
| APP_NAME, APP_ENV, DEBUG, LOG_LEVEL | Tên/môi trường/log level; APP_ENV development/test/production. DEBUG không bật traceback public; production từ chối DEBUG=true |
| API_PREFIX | Hiện bắt buộc /api/v1 để khớp contract |
| POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD | Bootstrap database dev; không là cơ chế đổi password sau khi volume đã tồn tại |
| DATABASE_URL | postgresql+psycopg://...; SecretStr, không log |
| DATABASE_POOL_SIZE, DATABASE_MAX_OVERFLOW, DATABASE_POOL_TIMEOUT_SECONDS | Pool bounds; mặc định5/5/0,5s |
| QDRANT_URL, QDRANT_API_KEY | URL không chứa userinfo/query; SDK chấp nhận key absent, Compose mặc định yêu cầu key sinh bởi helper |
| MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY | Endpoint host:port không scheme/path và credentials backend |
| MINIO_BUCKET, MINIO_SECURE, MINIO_AUTO_CREATE_BUCKET | Bucket private; dev auto-create, production không cho auto-create |
| API_TOKEN | Opaque token local, tối thiểu24 chars; bảo vệ readiness/system info; chưa có user/tenant management |
| CORS_ORIGINS | JSON array origins cụ thể, không wildcard/path |
| REQUEST_TIMEOUT_SECONDS, DEPENDENCY_TIMEOUT_SECONDS | Mặc định2s và0,75s; dependency timeout phải nhỏ hơn request timeout |
| VITE_API_BASE_URL | Chỉ public API prefix /api/v1, không token |
| VITE_PROXY_TARGET | URL backend từ Vite server; không bundle credentials vào frontend |

Token chỉ được người vận hành nhập vào diagnostics UI khi cần readiness; giữ trong memory, không localStorage/cookie. Trong runtime thực, environment có precedence với `.env`; helper `run_local.py` cố ý áp dụng file chỉ định cho child process để tránh biến có sẵn như DEBUG=release của host gây lỗi kiểu boolean. Host environment không bị sửa.

## 3. Docker Compose development

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose logs --tail=100
bash scripts/checks/verify_services.sh
```

`config --quiet` tránh in resolved secrets ra terminal/report. Có năm services: frontend, backend, postgres, qdrant, minio. Chỉ publish API8000 và UI5173 trên127.0.0.1. Data network internal, ba named volumes riêng. MinIO console tắt, không expose admin port. Backend non-root chạy migration trước Uvicorn; startup fail nếu migration lỗi. Data service outage sau startup khiến readiness503 nhưng liveness vẫn200. Chưa có encoder/index thì search-ready503 là đúng.

MinIO được build từ commit `07c3a429bfed433e49018cb0f78a52145d4bedeb`, SHA-256 source tar được pin trong Dockerfile. Registry official trả401 và binary archive410 trong lượt kiểm chứng nên dùng source build. Build cần Go-module network/cache và lâu hơn pull image; giữ LICENSE AGPL trong image. Images/build tool versions cụ thể, không latest. Kết quả build/runtime mới nhất tại PHASE03_REPORT.

Với Docker Snap, quyền socket cần được cấp trên host. Nếu tạo nhóm sau khi daemon đang chạy, [Canonical hướng dẫn disable/enable Snap](https://github.com/canonical/docker-snap#running-docker-as-normal-user):

```bash
sudo groupadd -f docker
sudo usermod -aG docker "$USER"
sudo snap disable docker
sudo snap enable docker
```

Đăng xuất/đăng nhập lại hoặc mở shell `newgrp docker`; kiểm tra `docker info`. Nhóm docker có quyền tương đương root. Chỉ restart daemon đã không cập nhật socket root:root trong lượt kiểm chứng này; disable/enable sau đó khắc phục. Không chmod666 socket hoặc công bố Docker API qua TCP.

MVP local dùng credentials bootstrap cho PG/MinIO, chưa tách application role/service account least privilege. Trước public deployment cần role/policy separation, TLS, auth/rate-limit/backup hardening; không quảng bá profile dev là production security.

## 4. Host URLs và container URLs

| Thành phần | Giữa containers | Backend native qua host override |
| --- | --- | --- |
| PostgreSQL | postgres:5432 | 127.0.0.1:5432 |
| Qdrant | http://qdrant:6333 | http://127.0.0.1:6333 |
| MinIO | minio:9000 | 127.0.0.1:9000 |
| API từ Vite | http://backend:8000 | http://127.0.0.1:8000 |
| API từ browser | /api/v1 qua Vite | /api/v1 qua Vite |

Chạy data containers, còn backend/frontend native:

```bash
# .env dùng credentials cho data services; .env.host là bản local riêng, giữ nguyên secrets.
cp .env .env.host
chmod 600 .env.host
# Sửa chỉ hostname trong DATABASE_URL thành127.0.0.1, QDRANT_URL/MINIO_ENDPOINT
# và VITE_PROXY_TARGET theo bảng trên; không sinh lại passwords khác .env.
docker compose -f compose.yaml -f compose.host.yaml up -d --build postgres qdrant minio
uv sync --project backend --extra dev --frozen
npm --prefix frontend ci
uv run --project backend python scripts/run_local.py --env-file .env.host -- backend/.venv/bin/alembic -c backend/alembic.ini upgrade head
uv run --project backend python scripts/run_local.py --env-file .env.host -- backend/.venv/bin/uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

Ở terminal thứ hai, từ project root:

```bash
uv run --project backend python scripts/run_local.py --env-file .env.host -- npm --prefix frontend run dev -- --host 127.0.0.1
bash scripts/checks/verify_services.sh --env-file .env.host
```

Host override chỉ mở loopback data ports khi explicitly dùng file đó. Không dùng `.env.host` làm env_file backend container vì127.0.0.1 bên trong container là chính container. Nếu không có Docker, có thể dùng ba services được vận hành riêng và cấu hình URL tương ứng; script không giả định dịch vụ đó đã healthy.

## 5. Migrations, tests và stop

```bash
docker compose exec backend alembic -c backend/alembic.ini current
make migrate
make test
make lint
make test-integration
make health
docker compose down
```

Migration đầu tạo images, image_metadata, embedding_models, indexing_jobs, search_indexes, dataset_sources. Hai bảng cuối cần cho approved FKs; 18 bảng còn lại được thêm theo phase. Không seed images/model rows hoặc tạo vector collection. Downgrade có sẵn, chỉ thực hiện trên disposable DB hoặc sau backup/approval vận hành phù hợp; test tự tạo DB ngẫu nhiên để kiểm chứng upgrade/downgrade.

`docker compose down` giữ volumes. Không dùng `down -v` khi muốn bảo toàn dữ liệu; project không có cleanup target xóa volume ngầm. Không thay password .env rồi kỳ vọng entrypoint PostgreSQL đổi password của volume cũ; cần quy trình đổi credential thực tế hoặc môi trường test mới.

## 6. Troubleshooting

| Triệu chứng | Kiểm tra |
| --- | --- |
| Docker command/socket lỗi | Cài Engine/Compose, kiểm tra daemon và quyền hiện tại; không coi config validation là container startup |
| Config invalid | Field name được báo an toàn; kiểm tra secrets trống, URL driver/hostname, JSON CORS và DEBUG boolean |
| Readiness401 | Bearer token phải khớp API_TOKEN; liveness không cần token |
| Readiness503 | Xem dependency status healthy/unhealthy/timeout và service logs; kiểm tra credentials/URL/bucket, không fake status |
| Search health503 | Dự kiến ở Prompt03: encoder not_implemented/index not_initialized |
| Bucket tồn tại nhưng unhealthy | Credentials thiếu quyền hoặc anonymous policy bị từ chối; không tự đổi policy bucket hiện hữu |
| Frontend không gọi được API | Vite proxy target phải từ góc nhìn server Vite; browser không resolve hostname backend |
| npm resolver edgesOut | Dùng npm11.21.1 với lockfile và npm ci; không force dependency upgrades mù quáng |
| Git status không hợp lệ | Kiểm tra đúng project root và metadata. Lượt bổ sung đã init nhánh main trong thư mục .git rỗng trên host; không overwrite history hoặc tự nhận đã commit |

Các kết quả đã thực thi và phần chưa kiểm chứng nằm tại [PHASE03_REPORT](../archive/PHASE03_REPORT.md).

## 7. Nghiệm thu đầy đủ

`python3 scripts/verification/verify_containers.py` dùng Python standard library và quyền Docker của phiên hiện tại. Nó build/start đủ năm containers, chạy backend/frontend tests/static/build, tạo markers riêng trong PG/MinIO và hidden file trong Qdrant volume, force-recreate giữ volumes, xác nhận markers còn nguyên, stop/restore từng dependency và kiểm tra live200/ready503 rồi hồi phục. Không tạo vector collection/dimension giả hoặc image records. Cleanup chỉ xóa markers thuộc UUID lượt test, không xóa volumes. Có thể dùng `--skip-build` khi chỉ kiểm tra lại images hiện tại; report ghi rõ tùy chọn này.

```bash
python3 scripts/verification/verify_containers.py
cd frontend
npm exec -- playwright install chromium
cd ..
make test-e2e
```

Nếu không có Make: `uv run --project backend python scripts/run_local.py --env-file .env -- npm --prefix frontend run test:e2e`. Browser tests không mock API, dùng backend/UI đang chạy, kiểm tra desktop/mobile và không lưu token; trace tắt để tránh ghi request headers. Không chạy đồng thời một native server khác trên ports8000/5173. Artifacts screenshots/SVG và reports chọn lọc tại `docs/verification/`; raw Playwright test-results được ignore.

## 8. Ingestion và worker Prompt 04

Thực hiện [IMAGE_INDEXING](../features/IMAGE_INDEXING.md) sau foundation setup: cài ml extra, tải CLIP vào .cache/clip, tải10 licensed fixtures, register index, đặt INGESTION_INDEX_ID và WRITE_API_TOKEN riêng, khởi động profile indexing. Chỉ mount cache public weights/dataset read-only; không đưa backend/data credentials vào VITE_*.

Host override có thêm host_access bridge để loopback port publication hoạt động với Docker Engine hiện tại; default compose không mở data ports. Dùng native CLI thì set EMBEDDING_CACHE_DIR/DATASET_ROOT thành paths thực trên host trong .env.host, không dùng /models/clip hoặc /datasets của container. Không đổi secrets của existing volumes.

`python3 scripts/verification/verify_indexing.py` build/start, chạy backend unit + real CLIP integration trong worker, frontend static/unit/build, HTTP smoke, ingest/queue10 ảnh, batch inference, kiểm chứng storage và repeat idempotency; report tại docs/verification/phase04. Đây là fixture acceptance trên index cấu hình, có thêm job và idempotent upserts thật, không xóa volumes hoặc collection ứng dụng. Cần cache/dataset và registry index đã chuẩn bị; tests không tự tải mạng. `--skip-build` dùng images hiện tại và được ghi rõ trong summary.

## 9. Online search Prompt05

Backend Compose hiện cài extra ml và mount model cache read-only để preload paired query encoder khi SEARCH_ENABLED=true; các câu API không cài/load Torch trong snapshot Prompt04 mô tả phase trước. Không cần tải model hoặc reindex khi cache/index vẫn matching. Activation CLI `python -m app.cli.search --activate INDEX_UUID` phải verify actual index và load model trước pointer publish; xem [SEMANTIC_SEARCH](../features/SEMANTIC_SEARCH.md).

Search config thực: SEARCH_ENABLED=false default, SEARCH_MAX_TOP_K=50, SEARCH_DEFAULT_CANDIDATES=50, SEARCH_MAX_TEXT_LENGTH=2000, SEARCH_ENABLE_BASIC_FILTERS=true, SEARCH_QUEUE_CAPACITY=8, SEARCH_QUEUE_WAIT_SECONDS=0.05, SEARCH_VECTOR_TIMEOUT_SECONDS=1. Core timeout vẫn REQUEST_TIMEOUT_SECONDS2s, không tự đổi thành target300ms. Missing/mismatch cache/index: process vẫn live, search not_ready; xem health/check search và safe logs.

Verifier cần host backend venv (HTTPX/app), Node/npm, Playwright Chromium đã install, model/cache/dataset/active pointer. `python3 scripts/verification/verify_search.py` build/start, full tests, browser và100 requests/modality; report docs/verification/phase05 + evaluation/results. --skip-build/--skip-browser/--skip-benchmark được ghi trong summary, không dùng skip để claim phần chưa chạy. Không xóa/recreate collection ứng dụng.

## 10. Chạy Prompt06

Giữ index/model/cache đã verify Prompt05, không cần đổi migration hoặc tạo lại dataset. Build rồi restart backend/frontend để load source/config mới; SEARCH_ENABLED=true và active index ready là prerequisites. MULTI_INTENT_ENABLED, MULTIMODAL_ENABLED, QUERY_DECOMPOSITION_ENABLED và RERANKING_ENABLED mặc địnhtrue; tham số/caps/weights trong .env.example. Request rerank mặc địnhfalse, người dùng bật trên UI hoặc API.

```bash
docker compose build backend indexing-worker frontend
docker compose up -d --wait backend frontend
bash scripts/verification/verify_advanced_search.sh --requests 100
```

UI http://localhost:5173 dùng token chỉ trong memory. Tự động với cả text và ảnh gọi multimodal endpoint; simple text/image không tự rerank. Nếu process shell chưa refresh docker group trên máy phát triển, chạy verifier qua sg docker -c như Phase05; không chmod socket/public services. [API](../features/ADVANCED_SEARCH_API.md), [tài liệu](../features/MULTIMODAL_SEARCH.md), [nghiệm thu](../archive/ADVANCED_SEARCH_TEST_REPORT.md). Human qrels không là prerequisite chạy ứng dụng, nhưng bắt buộc trước quality claims.


Trên máy phát triển hiện tại, Node/npm và Chromium đã được đặt trong project cache thay cho /tmp để tránh mất khi phiên được làm mới. Các thư mục này bị Git/Docker build ignore. Nếu shell chưa có Node/npm trong PATH:

```bash
export PATH="$PWD/.tools/node/bin:$PATH"
export PLAYWRIGHT_BROWSERS_PATH="$PWD/.cache/playwright"
bash scripts/verification/verify_advanced_search.sh --requests 100
```

Fresh clone vẫn phải cài prerequisites theo phần đầu SETUP; .tools/.cache không được đóng gói vào source repository.

## 11. Evaluation Prompt07

Cài optional extra evaluation để xuất biểu đồ: `uv sync --project backend --extra dev --extra ml --extra evaluation --frozen`. Không nâng core ML dependencies. Sau khi sample index/cache/active CLIP đã sẵn sàng, theo [evaluation/README](../../evaluation/README.md) để xác minh dataset, tạo trang gán nhãn, benchmark và xuất báo cáo. Fresh clone cần tạo snapshot mới từ UUID thật sau ingestion; không dùng snapshot máy khác cho corpus mới. Không tải COCO/Flickr hoặc nhãn giả. Model so sánh cần explicit download SigLIP2 (~1,54GB); worker build có evaluation extra và runner mount read-only model cache. Không cần expose data ports.

## Cập nhật triển khai Prompt08

Đã có RAG metadata tùy chọn, tái sử dụng SearchService/active CLIP, batch evidence validation/current IDs, bounded context/prompts, Gemini/OpenAI-compatible adapter, citation validation, JSON/SSE và React explanation panel. Không gửi ảnh sang provider hoặc thay Fast Search/ranking. Gemini key ở backend; generator tắt/lỗi giữ ảnh. Với corpus10 ảnh không caption/tags, chưa thể xác minh nội dung thị giác. [Kiến trúc](../features/RAG_ARCHITECTURE.md), [API hiện hành](../features/RAG_API.md), [cấu hình](../features/RAG_IMPLEMENTATION.md), [đánh giá](../research/RAG_EVALUATION.md), [nghiệm thu A–L](../archive/PHASE08_TEST_REPORT.md). Không triển khai Prompt09.

Ngày06/11, Prompt08 bổ sung [COCO downloader/corpus caption/offline review](../research/RAG_DATASET.md) và [nghiệm thu mới](../archive/PHASE08_COMPLETION_REPORT.md). Default RAG generation8s/request12s. Lượt thực510 ảnh đã verify/activate, baseline được giữ.


## Frontend Phase10

Giao diện hiện tại chạy trên Compose frontend `127.0.0.1:5173`; đường dẫn `/evaluation` là dashboard private. Vite proxy `/api` sang backend; không cấu hình API_TOKEN/Gemini key trong biến `VITE_*`. Nhập read token vào input password trong UI, chỉ giữ trong memory.

`EVALUATION_RESULTS_DIR=evaluation/results` dùng native; Compose đặt `/evaluation/results` và mount read-only. Đọc [FRONTEND_TESTING.md](../testing/FRONTEND_TESTING.md) để cài/chạy browser engines, xử lý thư viện WebKit và phân biệt các loại bằng chứng. Fixture dataset rỗng riêng ở [FRONTEND_EMPTY_DATASET_MODE.md](../features/FRONTEND_EMPTY_DATASET_MODE.md). Không cần chạy lại indexing hoặc đổi model để nâng cấp giao diện.
