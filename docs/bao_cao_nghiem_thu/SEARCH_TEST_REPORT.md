# Báo cáo nghiệm thu Phase 05 — Core Semantic Search

> Tài liệu lịch sử theo phase; lệnh trong nội dung giữ tên đường dẫn cũ. Hướng dẫn hiện hành tại [danh mục tài liệu](../README.md) và [scripts](../../scripts/README.md).

Ngày thực thi: 2026-11-03. Kết luận: hoàn thành chức năng core text-to-image và image-to-image trên model, index và ảnh thật của Phase 04; các kiểm tra cuối đã qua. Không triển khai Phase 06. [Tổng kết verifier](../verification/phase05/summary.json) ghi build, browser và benchmark đều đã chạy. Đây là baseline trên corpus mẫu nhỏ, chưa phải kết luận chất lượng retrieval hoặc SLA production.

## A. Tóm tắt triển khai

Đã bật tìm kiếm bằng văn bản, ảnh upload và existing image_id. CLIP sinh query embeddings thật; Qdrant trả candidates thật; PostgreSQL cung cấp metadata và trạng thái hợp lệ; MinIO cung cấp ảnh qua authenticated content proxy. UI React hiển thị ảnh thực, Top-K, điểm cosine, loading, empty và lỗi. Không tự ingest query image, không dùng filename matching hoặc kết quả hardcode trong ứng dụng.

Có basic metadata filters, deterministic ranking/dedup, encoder/index compatibility checks, bounded inference admission, standardized errors và đo latency tới final ASGI send. Quality metric code và benchmark scripts đã có; actual retrieval accuracy chưa đo khi thiếu human-verified judgments.

## B. Các tệp tạo hoặc sửa

| Nhóm | Tệp chính và thay đổi thực tế |
| --- | --- |
| Query/encoder | `backend/app/schemas/search.py`, `backend/app/services/embeddings/query_encoder.py`: typed validation, matching text tower/tokenizer và reuse image encoder |
| Search runtime | `backend/app/services/search/registry.py`, `runtime.py`, `query_decoder.py`, `decoder_process.py`: pin active index, preload/warmup, admission và resource-limited decoder reuse |
| Retrieval | `backend/app/services/search/vector_retriever.py`, `ranking.py`, `search_service.py`, `backend/app/repositories/image_repository.py`: Qdrant, filters, batch metadata, eligibility và private URLs |
| API/lifecycle | `backend/app/api/v1/search.py`, `backend/app/api/v1/health.py`, `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/core/middleware.py`, `backend/app/cli/search.py`: endpoints, OpenAPI, capabilities, full-response metrics và activation CLI |
| Frontend | `frontend/src/features/search/SearchWorkspace.tsx`, `ResultImage.tsx`, `frontend/src/app/App.tsx`, `frontend/src/services/api/client.ts`, `frontend/src/types/api.ts` và tests: nhập text/upload image, gọi API và tải preview có Authorization |
| Tests | `backend/tests/unit/test_search.py`, `backend/tests/integration/test_real_search.py`, cập nhật foundation/API tests và `frontend/e2e/foundation.spec.ts` |
| Evaluation | `backend/app/evaluation/metrics.py`, `evaluation/scripts/benchmark_search.py`, `evaluate_search.py`, smoke queries, labels template và results |
| Chạy/kiểm tra | `scripts/verify_search.py`, `verify_search.sh`, `benchmark_search.sh`, `.env.example`, `compose.yaml`, `Makefile` |
| Tài liệu | [SEMANTIC_SEARCH](../features/SEMANTIC_SEARCH.md), [SEARCH_API](../features/SEARCH_API.md), [SEARCH_PERFORMANCE](../research/SEARCH_PERFORMANCE.md), báo cáo này; cập nhật README, MASTER_SPEC, ROADMAP, SAD, SYSTEM_ARCHITECTURE, API_SPECIFICATION, DATABASE_DESIGN, DECISIONS, SETUP, DEVELOPMENT và PERFORMANCE_DESIGN |

Danh mục và SHA256 của source bàn giao: [source_snapshot.json](../verification/phase05/source_snapshot.json). Giữ nguyên source fingerprint của CLIP image encoder và ingestion decoder thuộc manifest Phase 04; không migration, không reindex hoặc xóa collection có dữ liệu. Không tạo commit trong lượt triển khai này.

## C. Kiến trúc Semantic Search đã chạy

Text: auth/body/schema → NFC/whitespace/token limit → CLIP text tower → float32/L2/finite/dimension checks → Qdrant query_points → dedup/ranking → batch PG metadata và authoritative eligibility/filter recheck → private object HEAD/URLs → response → serialization/final send.

Ảnh upload: multipart bounds → cùng hàm decode/RGB/EXIF/alpha của Phase 04 trong decoder process → cùng image processor/tower → đường retrieval/enrichment chung. JPEG/PNG/WebP pixel-equivalence và decoder restart đã có tests. Bytes upload chỉ phục vụ query, không tạo image/object/index-job rows. Existing image_id lấy stored vector đã xác minh cùng index; exclude_self mặc định bật.

Model/tokenizer preload một lần/API process. Một inference slot, queue tối đa8 và chờ50ms; cancel request giữ slot tới khi computation thật hoàn tất. Outer request deadline2s, Qdrant timeout1s. Khi active generation đổi, runtime cũ trả INDEX_SWITCHING tới khi reload. Search không tự tạo collection hoặc chọn model khác để vượt compatibility checks.

Basic filters dựa trên dữ liệu có thật: source_dataset, media_types, tags_any/all, city, kích thước và captured_at. Category chưa có schema/payload, không nhận rồi tự suy đoán. Batch PG join và query tags thứ hai tránh N+1 metadata queries. Candidates không eligible/mất object bị loại, không bù kết quả giả cho đủK. Xem chi tiết tại [SEMANTIC_SEARCH](../features/SEMANTIC_SEARCH.md).

## D. Model, vector và môi trường

| Thuộc tính | Giá trị đã kiểm chứng |
| --- | --- |
| Model | `openai/clip-vit-base-patch32` |
| Model registry ID | `02593ce4-5531-49eb-8b46-89e6ecaef50c` |
| Checkpoint/tokenizer/processor revision | `3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268` |
| Active index / generation | `6c3a8404-2971-46bf-ac9c-5c09bdec42b5` / 1 |
| Manifest SHA256 | `7f843c0bf81c571eee3b12621fc41811cea174113e6802684e9063b447e707dc` |
| Collection | `images_clip_v1_da55a7d099fd` |
| Embedding / metric | 512 dimensions, float32, L2 normalized / Cosine |
| Corpus / exact vector count | 10 ảnh / 10 points, license/provenance tại dataset manifest Phase 04 |
| Device / CPU threads | CPU / 4 Torch threads; chưa chạy CUDA benchmark |
| CPU / RAM | Intel Core 7 240H, 16 logical CPUs / 15.11GiB tổng RAM theo MemTotal |
| OS / Python | Linux 6.17.0-1033-oem x86_64; container Python3.12.12 |
| Packages | Torch2.15.0+cpu, Transformers4.57.6, Pillow12.3.0, NumPy2.5.4, qdrant-client1.20.0, FastAPI0.162.0 |

[Environment/model artifact](../verification/phase05/environment_model.json) ghi các giá trị và encoder hashes. [Activation](../verification/phase05/activation.json) verify10 ảnh trước khi active, model initialization/warmup **6.973,2ms**; đây không phải container cold-start benchmark. Re-activate cùng index giữ generation1. [Index verification](../verification/phase05/index_preserved.txt) sau toàn suite vẫn10 images/10 points, không orphan hoặc thiếu embedding, cùng index/manifest. Collection baseline cũ được giữ nguyên.

[Trạng thái runtime cuối](../verification/phase05/final_runtime.json): backend, frontend, PostgreSQL, Qdrant và MinIO đều running/healthy; indexing-worker running nhưng chưa có container healthcheck, worker heartbeat trong health summary vẫn unknown. Search readiness HTTP200 xác nhận metadata/objects/vectors/encoder/index healthy. Alembic giữ `928b88dc3f68 (head)`. Docker Engine29.8.0, Compose5.5.1.

## E. Kết quả API và giao diện

| Kiểm tra thực | Kết quả |
| --- | --- |
| Text `POST /api/v1/search` | HTTP200, query text được encode thật, kết quả có UUID/metadata/private URL và cosine giảm dần; aliases query/search_mode được hỗ trợ |
| Image `POST /api/v1/search/multimodal` | HTTP200, image-only multipart; cùng ảnh coffee tìm lại chính nó với cosine>0.99 trong integration test |
| Existing image_id | Stored vector cùng index, exclude_self loại chính ảnh query |
| Object/color+object/scene/action smoke | Đã chạy coffee, brown cat, galaxies, rocket launch; đây là functional smoke, không phải human relevance judgments hoặc đảm bảo action understanding |
| Content delivery | Authenticated image URL đọc được bytes thật; browser giải mã preview thành công; không public bucket hoặc expose storage keys |
| Validation và empty | Text rỗng/quá giới hạn, Top-K sai và ảnh hỏng bị reject; filter không có eligible images trả200/results=[] |
| Unavailable/incompatible collection | Missing collection trả503; isolated test collection sai dimension trả409, chỉ cleanup collection riêng của test |
| Advanced request | Text+image fusion/advanced features trả409 FEATURE_DISABLED; không giả vờ đã hỗ trợ |
| UI desktop/mobile | Text và image search trả ảnh thật; invalid token hiển thị lỗi; không overflow hoặc persist token vào local/sessionStorage |

[First text response](../verification/phase05/first_text.json) lưu một request thật với Top-K3; query_id/request_id/actual UUIDs/nullable metadata và processing_ms có trong artifact. Các benchmark giữ actual returned UUIDs cho từng request. Preview fallback dùng ảnh original vì fixture chưa có thumbnails. Caption/title/city có thể null và tags rỗng; không tạo caption/category để làm kết quả trông đầy đủ. Cosine score không là xác suất relevance.

Ảnh chụp giao diện cuối: [desktop](../verification/phase05/desktop.png), [mobile](../verification/phase05/mobile.png), ô token được mask. API schema/contracts/examples và errors tại [SEARCH_API](../features/SEARCH_API.md); OpenAPI tại `http://localhost:8000/docs`, UI tại `http://localhost:5173`.

## F. Chất lượng retrieval

Đã triển khai và unit-test Recall@1/5/10, Precision@10, MRR@10 và nDCG@10 có graded relevance. Precision@10 chia10; duplicates chỉ tính lần đầu, giữ vị trí; no-answer queries tách khỏi recall aggregation. Harness kiểm corpus IDs, human_verified và exhaustive judgments trước khi đánh giá.

**Recall@1/5/10, Precision@10, MRR và nDCG thực tế: chưa đo.** Chưa có nhãn do người đánh giá xác nhận, không suy ra chất lượng từ self-match, smoke text hoặc latency. [quality_status.json](../../evaluation/results/quality_status.json) ghi not_measured; [evaluation README](../../evaluation/README.md) hướng dẫn tạo ground truth và chạy evaluation; template chưa được gắn human_verified.

## G. Số đo hiệu năng thực tế

Điều kiện chung: corpus10, K10/C50, một request đồng thời, warm model/pools, warmup5 riêng và100 measured requests mỗi modality, không query-result cache. Text luân phiên4 smoke queries; image gửi coffee.png qua decode/inference thật mỗi lần. Server latency tính từ ASGI request arrival tới final body send; client latency đo từ HTTP request tới full response và được ghi riêng. Percentiles nearest-rank ceil(p*n) trên successful samples; không cộng stage percentiles. Mỗi run join đủ100 server samples bằng request_id.

| Phiên bản / modality | Requests / errors | Server P50 ms | Server P90 ms | Server P95 ms | Requests/s |
| --- | --- | --- | --- | --- | --- |
| Trước decoder reuse — text | 100 / 0 | 128.02 | 136.17 | 138.00 | 7.572 |
| Trước decoder reuse — image | 100 / 0 | 565.22 | 595.47 | 612.00 | 1.739 |
| Sau tối ưu — text | 100 / 0 | 126.81 | 134.70 | 140.78 | 7.645 |
| Sau tối ưu — image | 100 / 0 | 169.08 | 205.89 | 222.70 | 5.593 |

Sau tối ưu client P50/P90/P95: text130.47/138.51/144.55ms, image173.05/208.74/225.93ms. Error rate0% ở cả4 runs. Raw samples: [text trước](../../evaluation/results/text_before_decoder_reuse.json), [image trước](../../evaluation/results/image_before_decoder_reuse.json), [text sau](../../evaluation/results/text_baseline.json), [image sau](../../evaluation/results/image_baseline.json).

Bottleneck đầu là decoder process startup/Pillow import và encode PNG IPC; image preprocessing median giảm từ430.14 xuống16.99ms sau preload/reuse process và truyền RGB có kiểm length. Vẫn dùng nguyên hàm decode đã pin, resource limits, same model/index, không cache theo ảnh hoặc loại object checks để giảm số đo. Unit tests xác minh pixel equivalence và restart. Text không có cải thiện tail nhất quán; không kết luận image optimization làm text nhanh hơn.

**Đã quan sát P90≤300ms và P95≤500ms cho cả text và image trong baseline sau tối ưu này.** Không suy ra SLA trên corpus lớn, concurrency cao, cold model, mixed indexing/search, CUDA hoặc query distributions khác. Chưa đo confidence intervals hoặc sustained stress. [SEARCH_PERFORMANCE](../research/SEARCH_PERFORMANCE.md) giải thích boundaries, reproduction và giới hạn.

## H. Kiểm thử đã chạy

| Suite/check | Kết quả cuối | Bằng chứng |
| --- | --- | --- |
| Backend unit + real integration | **74 passed**: 69 unit +5 integration, 0 skipped trong lượt full | [pytest log](../verification/phase05/backend_tests.txt), [summary](../verification/phase05/backend_tests.json) |
| Frontend unit / type / lint / build | **9 unit passed**, TypeScript/ESLint/Vite build qua | [log](../verification/phase05/frontend_checks.txt) |
| Playwright Chromium desktop/mobile | **6 passed**, 0 skipped/flaky/unexpected | [browser summary](../verification/phase05/browser.json), [log](../verification/phase05/browser.txt) |
| Python Ruff lint/format | Qua backend và scripts trong container; final host check mở rộng workers/evaluation scripts | [lint](../verification/phase05/python_lint.txt), [format](../verification/phase05/python_format.txt) |
| Compose build/start và HTTP smoke | Qua API/UI build, startup, live/ready/OpenAPI/docs/UI/proxy | [build](../verification/phase05/build.json), [startup](../verification/phase05/startup.json), [HTTP smoke](../verification/phase05/http_smoke.txt) |
| Benchmark | 100 text +100 image sau tối ưu, 0 lỗi, server coverage100/100 mỗi run | Raw samples ở mụcG |
| Data/index preservation |10 ảnh/10 vectors verified, không thiếu receipt/embedding hoặc orphan point | [index verify](../verification/phase05/index_preserved.txt) |

Unit mocks chỉ dùng kiểm module/validation/metrics/lifecycle; integration và browser dùng CLIP, PostgreSQL, Qdrant và MinIO thật. Regression indexing Phase 04 gồm batch/retry/idempotency/recovery/repair vẫn qua. Image search test kiểm không tăng corpus/jobs. Test queue cancellation kiểm slot không nhả sớm. CUDA execution, mất model cache giữa runtime và mọi tổ hợp dependency outage chưa được thực thi riêng trong môi trường này.

[Final checks](../verification/phase05/final_checks.json) ghi Ruff mở rộng cho backend/scripts/workers/evaluation, shell syntax, source fingerprint, JSON artifact consistency, relative links/requirement IDs/14 JSON examples, secret scan và immutable encoder/decoder checks. Structural checks11 Mermaid sources không được ghi nhận thành render mới; bằng chứng render Phase 03 vẫn giữ nguyên.

Lượt pytest đầu bị collection error vì hai file unit/integration cùng basename `test_search.py`; đã đổi tên integration thành `test_real_search.py` và full run sau qua74 tests. [Log lỗi đầu đã redact](../verification/phase05/backend_tests_initial_collection_failure.txt) được giữ; đây là lỗi đã giải quyết. Còn warning SDK Qdrant về API key trên HTTP local/private Docker network; không có failed test do warning này. Chưa cấu hình public TLS trong phạm vi local MVP.

Lệnh nghiệm thu lại từ project root:

```bash
python3 scripts/verify_search.py --requests 100
# Hoặc bash scripts/verify_search.sh; cần Docker access, host backend venv/HTTPX,
# Node/npm và Playwright Chromium theo docs/SETUP.md.
bash scripts/benchmark_search.sh text --requests 100 --concurrency 1
bash scripts/benchmark_search.sh image --requests 100 --concurrency 1
```

Các script đọc secret qua env/child environment, không truyền token qua CLI arguments hoặc lưu raw auth headers trong reports. Máy nghiệm thu hiện dùng `sg docker -c` vì process đang mở chưa refresh group membership; đây là yêu cầu shell của máy, không thay đổi ứng dụng.

## I. Hạn chế và vấn đề còn mở

Không còn lỗi test chưa giải quyết trong các suite đã thực thi. Các giới hạn còn lại:

- Corpus10 quá nhỏ để kết luận HNSW scalability, accuracy hoặc quality gates; chưa có human judgments, multilingual/Vietnamese evaluation hay train/dev/test split.
- Baseline chỉ CPU warm/concurrency1; cần cold-start, corpus lớn, tải hỗn hợp, nhiều clients và CUDA measurements ở Phase 07 trước cam kết SLA.
- Fixture thiếu captions/tags/category và thumbnails; UI có fallback original và nullable metadata. Chưa tối ưu ảnh preview cho corpus lớn.
- Bounded candidate pool có thể trả ít hơnK sau eligibility/post-filter; không đảm bảo full-corpus recall khi pool bị giới hạn. Object HEAD checks còn tạo network overhead có chủ đích.
- Decoder/model mỗi API process và worker indexing riêng cần profiling khi scale; chưa có scheduler chia GPU giữa processes. Runtime phải reload khi active generation đổi.
- Auth local static tokens/in-memory rate limits chưa thay thế public multi-tenant auth/TLS. Bounded telemetry không persist query text/images hoặc lịch sử search mặc định.
- Chưa có calibrated cosine threshold; chưa có combined fusion, semantic constraint verification, reranking, RAG hoặc Agent.

## J. Sẵn sàng cho Phase 06

Core đã có paired text/image encoders cùng manifest, typed request/options, candidate retrieval/ranking dùng chung, metadata filters/eligibility, disabled advanced capability flags, instrumentation và regression suite. Có thể tiếp tục xây combined text+image, multi-intent/query decomposition, candidate fusion và constraint-aware reranking trên các extension points này khi được yêu cầu.

Các chức năng trên **chưa được triển khai hoặc nghiệm thu** trong Phase05. Trước khi bật cần bổ sung API semantics, fusion/ranking versions, labels/constraint evidence và tests tương ứng; không đưa LLM vào fast path hiện tại. Dừng tại Phase 05.
