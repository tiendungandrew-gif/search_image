# Báo cáo triển khai và nghiệm thu Prompt 04

> Tài liệu lịch sử theo phase; lệnh trong nội dung giữ tên đường dẫn cũ. Hướng dẫn hiện hành tại [danh mục tài liệu](../README.md) và [scripts](../../scripts/README.md).

Ngày 2026-11-03 · **Hoàn thành pipeline ingestion/CLIP/vector indexing và nghiệm thu bằng Docker/model thật.** Full verifier có status pass: [summary.json](../verification/phase04/summary.json); [runtime cuối](../verification/phase04/runtime_state.json), [HTTP ingestion thực](../verification/phase04/http_ingestion.json) và [final review](../verification/phase04/final_review.json). Prompt 05 chưa bắt đầu.

## Checklist nghiệm thu Phase 04 — 9/9 đạt

Đối chiếu với full Docker acceptance đã lưu và kiểm tra lại cross-storage hiện tại. Unit/integration results và throughput là số đo của lượt nghiệm thu, không phải kiểm thử hoặc benchmark mới trong lần đối chiếu checklist.

- [x] Đã load được model CLIP thực tế — pretrained CLIP ViT-B/32, pinned revision, chạy CPU.
- [x] Đã tạo image embeddings hợp lệ — 512 chiều, finite, L2-normalized, kiểm tra readback.
- [x] Đã lưu ảnh gốc vào MinIO — 10 originals private, retrieval/hash khớp bytes nguồn.
- [x] Đã lưu metadata vào PostgreSQL — image identities/metadata/object receipts và jobs được kiểm chứng.
- [x] Đã tạo collection Qdrant đúng kích thước vector — `images_clip_v1_da55a7d099fd`, 512 chiều/Cosine, manifest khớp.
- [x] Đã indexing được dataset ảnh mẫu — 10 ảnh thành công, job succeeded, exact vector count10.
- [x] Đã kiểm tra retry và xử lý ảnh trùng lặp — transient failure/lease recovery tests pass; repeat nhận10 duplicates, không tăng vectors.
- [x] Đã chạy unit tests và integration tests — 52 backend unit + 4 real integration = 56 passed.
- [x] Đã đo throughput của quá trình indexing — 1,794 ảnh/s CPU cho10 ảnh; worker5,574s, không gồm model init.

## A. Tóm tắt triển khai

Đã triển khai upload và local dataset ingestion, validation subprocess có giới hạn tài nguyên, SHA-256 dedup, private original storage, PostgreSQL durable jobs/attempts/leases, CLIP batch inference thật, model/index registry, Qdrant compatibility/upsert/readback/queryability, retry/recovery/reindex và reconciliation/repair. Không dùng BackgroundTasks làm durable queue, không random/mock vectors trong production, không tự sinh captions/tags hoặc tự chuyển sang semantic search.

Bộ nghiệm thu Docker hiện đã build API/worker, chạy unit/integration với CLIP thật, HTTP smoke, frontend static/unit/build, source batch10 ảnh, cross-storage verification và repeat idempotency. Worker đang chạy liên tục bên cạnh năm foundation containers; worker không có container healthcheck riêng nên không gọi cả sáu containers là healthy.

## B. Files tạo và thay đổi

| Nhóm | Artifact |
| --- | --- |
| Validation/storage | [decoder.py](../../backend/app/services/ingestion/decoder.py), [validator.py](../../backend/app/services/ingestion/validator.py), [storage.py](../../backend/app/services/ingestion/storage.py) |
| Embedding | [ImageEncoder protocol](../../backend/app/services/embeddings/base.py), [ClipEncoder](../../backend/app/services/embeddings/clip_encoder.py), [explicit downloader](../../backend/app/cli/download_model.py) |
| Orchestration | [jobs.py](../../backend/app/services/indexing/jobs.py), [submission.py](../../backend/app/services/indexing/submission.py), [worker.py](../../backend/app/services/indexing/worker.py), [consistency.py](../../backend/app/services/indexing/consistency.py), [collection_manager.py](../../backend/app/services/indexing/collection_manager.py) |
| API/schema | [images.py](../../backend/app/api/v1/images.py), [indexing.py](../../backend/app/api/v1/indexing.py), [typed schemas](../../backend/app/schemas/ingestion.py), router/auth/settings/middleware/logging/errors |
| Data model | [7 ORM tables](../../backend/app/db/models/indexing.py), [migration](../../backend/alembic/versions/928b88dc3f68_indexing_pipeline.py), model registration/import và schema tests |
| CLI/worker | [indexing CLI](../../backend/app/cli/indexing.py), [launcher](../../workers/indexing_worker.py), workers README |
| Infrastructure | [Dockerfile](../../backend/Dockerfile), [Compose](../../compose.yaml), [host override](../../compose.host.yaml), backend dependencies/uv.lock, env example/generator/ignore rules, Makefile |
| Dataset | [download script](../../scripts/data/download_sample_dataset.py), [manifest](../../datasets/sample_manifest.json), [dataset instructions](../../datasets/README.md); actual images/cache ignored |
| Verification | [verify_indexing.py](../../scripts/verification/verify_indexing.py), [index_sample_dataset.sh](../../scripts/data/index_sample_dataset.sh), [verify_index.sh](../../scripts/verification/verify_index.sh), ingestion/upload unit tests và [real-model integration test](../../backend/tests/integration/test_indexing.py) |
| Docs | [IMAGE_INDEXING](../features/IMAGE_INDEXING.md), [EMBEDDING_MODELS](../features/EMBEDDING_MODELS.md), [VECTOR_INDEX_DESIGN](../features/VECTOR_INDEX_DESIGN.md), report này và cập nhật README/SETUP/DEVELOPMENT/API/DATABASE/SAD/MASTER_SPEC/ROADMAP/DECISIONS |

Git nhánh main đã có từ Prompt03, source chưa commit. Không overwrite history, volumes, passwords hoặc collections ứng dụng. Source snapshot cuối nằm [source_snapshot.json](../verification/phase04/source_snapshot.json), không phải commit hash.

## C. Pipeline nhập ảnh thực tế

Upload write token + Idempotency-Key → actual content validation → SHA-256 identity → reserve image/job awaiting_input → PUT original theo UUID/hash → GET bytes/hash verify → transaction image_objects receipt + available/queued → worker SKIP LOCKED claim → EXIF/RGB/alpha preprocessing → official CLIP processor → batch image embeddings → shape/finite/L2 checks → Qdrant applied upsert/readback/exact queryability → image/item locks, nonce/lease/source revision checks → image_embeddings ready → job aggregate completion.

API chỉ trả202 khi bytes và job durable. Duplicate bytes dùng cùng image UUID/original và không overwrite metadata. Same key/body replay acceptance response; interrupted PUT retry giữ reserved IDs, request đang xử lý trả409 và Retry-After. Job progress được đọc qua GET endpoint/CLI; queued acceptance không tự có nghĩa searchable.

Giới hạn mặc định: JPEG/PNG/WebP một frame,20MiB/file,21MiB multipart,25 triệu pixels, cạnh10.000; metadata/JSON64KiB. Decoder process1GiB address space/3s CPU, parent timeout2s; upload total deadline30s, health/core2s. Worker batch4, CPU threads4, lease120s với heartbeat, max3 attempts và job execution timeout600s. CLI local root allowlist, recursive scan, không theo image symlink hoặc URL arbitrary fetch. Các default không là capacity benchmark.

## D. Model embedding

| Thuộc tính | Giá trị thực |
| --- | --- |
| Model | openai/clip-vit-base-patch32 |
| Revision | 3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268 |
| Processor | Official CLIPImageProcessor từ cùng pinned revision, config/hashes trong manifest |
| Dimension | 512, lấy từ loaded projection_dim và kiểm tra output thực |
| Precision/distance | float32 / cosine |
| Normalization | L2, reject NaN/Inf/zero norm |
| Device | CPU,4 threads; batch4/4/2 trong lượt cuối |
| Framework | PyTorch2.15.0+cpu, Transformers4.57.6, Pillow12.3.0, NumPy2.5.4 |
| Manifest SHA-256 | 7f843c0bf81c571eee3b12621fc41811cea174113e6802684e9063b447e707dc |

Nguồn và giới hạn model tại [EMBEDDING_MODELS](../features/EMBEDDING_MODELS.md). Weights tải explicit vào cache, chuyển từ pinned state dict bằng weights_only sang safetensors; runtime local-only, eval/inference_mode/deterministic algorithms. Không tải model theo mỗi ảnh. CUDA auto/config/OOM split có code paths nhưng **chưa nghiệm thu CUDA**; CPU lockfile cần runtime khác để chạy GPU. SigLIP 2 chỉ là extension port, chưa triển khai.

## E. Tích hợp ba kho dữ liệu

- PostgreSQL: migration `928b88dc3f68 (head)`, tổng13 ORM tables. Upgrade/compare_metadata/downgrade chạy trên disposable PostgreSQL database trong integration test; không rollback application DB.
- MinIO: originals byte-identical, private bucket, image_objects receipt, actual retrieval và SHA-256 khớp. Content proxy authenticated, private/no-store/nosniff; không trả data credentials/bearer URLs.
- Qdrant: collection `images_clip_v1_da55a7d099fd`,512 dimensions/Cosine, manifest/index/config metadata khớp, exact point count10. Applied writes, vectors/payloads/ID readback và exact queryability đã kiểm chứng.
- Index UUID `6c3a8404-2971-46bf-ac9c-5c09bdec42b5`, model UUID `02593ce4-5531-49eb-8b46-89e6ecaef50c`. Index đã ready sau validation. Active_search_index chưa được set; chưa có online encoder/search runtime.

Collection trước `images_clip_v1_64b85964aaf3` giữ nguyên10 vectors để đối chiếu reindex, không bị overwrite. Con số10 trong báo cáo là collection đích, không phải tổng points cộng mọi collection. Rollback/activation cần matching manifest/runtime ở Prompt05; chưa tự đổi active pointer.

## F. Kết quả indexing

| Lượt | Khám phá/valid | Thành công | Lỗi | Duplicate | Exact vectors collection đích |
| --- | --- | --- | --- | --- | --- |
| Nhập lần đầu bằng native CLI → Docker data services | 10/10 | 10 accepted rồi indexed | 0 | 0 | 10 ở collection baseline ban đầu |
| Docker source batch, dùng originals đã lưu | 10/10 | 10 indexed, job succeeded | 0 | 10 khi nhập lại originals | 10 ở collection manifest cuối |
| Repeat sau indexing | 10/10 | Reuse10 image identities | 0 | 10 | Vẫn10, IDs giữ nguyên |

Dataset là10 ảnh scikit-image v0.25.2, CC0/public-domain từng file ghi trong [sample manifest](../../datasets/sample_manifest.json); script đối chiếu SHA-256 registry upstream, không fabricate caption/tags. Không có relevance judgments hoặc quality claims từ dataset này.

Integration test còn tạo một corrupt-storage fixture UUID riêng: batch có1 ảnh hợp lệ và1 ảnh hỏng kết thúc partial_failed, succeeded1/failed1; ảnh hỏng không làm crash batch. Đây là lỗi được chủ đích tiêm vào test, đã cleanup đúng namespace, không là ảnh lỗi tồn đọng trong corpus.

Evidence: [initial ingestion](../verification/phase04/initial_ingestion_native.json), [Docker dataset](../verification/phase04/dataset.json), [job](../verification/phase04/job.json), [index](../verification/phase04/index.json), [repeat](../verification/phase04/repeat.json), [after repeat](../verification/phase04/index_after_repeat.json), [orphans](../verification/phase04/orphans.json). Không còn orphan originals hoặc target-collection orphan vectors trong lượt kiểm chứng.

## G. Số đo hiệu năng thực tế

Môi trường: Linux x86_64, Intel Core7 240H,16 logical CPUs, CPU threads4; Docker worker non-root; không CUDA. Versions/RAM/OS chi tiết tại [environment.json](../verification/phase04/environment.json). Worker xử lý10 existing originals trong3 batches4/4/2, cache model đã tải, không concurrent indexing worker. Đây là một lượt smoke nhỏ, không thí nghiệm throughput ổn định hoặc tối ưu hardware.

| Chỉ số | Số đo lượt Docker cuối |
| --- | --- |
| Model initialization | 2.154s |
| Decode/preprocess subprocess, tổng10 ảnh | 4094.290ms |
| Official processor, tổng3 batches | 55.837ms |
| CLIP inference forward, tổng3 batches | 456.586ms |
| Qdrant upsert + readback/query verification, tổng | 233.315ms |
| Average whole batch processing | 1688.216ms |
| Worker drain duration | 5.574s |
| Images indexed/second, sau model init | 1.794 ảnh/s |
| Peak RSS worker process | 1.082GiB, không gồm decoder child RSS |

Model initialization timer gồm cache integrity/model/processor/device init, **không gồm import Python/Torch hoặc container startup**. Worker timer bắt đầu sau encoder init, gồm collection check/claim/recovery/processing/final idle check. Decode/preprocess timer chưa gồm official processor; processor và inference được đo riêng. Batch timer gồm object/DB orchestration, không chỉ model forward. Model-download, original-ingestion và queue wait không nằm trong worker throughput trên. Raw từng batch tại [worker.json](../verification/phase04/worker.json).

Không có GPU number để so sánh; chưa đo large-corpus/concurrent/search workload. Các số này không chứng minh P90≤300ms, Recall@10 hoặc TTLast.

## H. Tests và lệnh đã thực thi

Full Docker acceptance đã chạy thành công:

```bash
python3 scripts/verify_indexing.py
```

Script build images và Compose start, tạm dừng worker đang chạy để tránh chạy tranh benchmark, sau đó khôi phục trong finally. Nó chạy các lệnh thực tương đương:

```bash
docker compose --profile indexing config --quiet
docker compose build backend indexing-worker
docker compose up -d --wait backend frontend
docker compose --profile indexing run --rm --no-deps -T -e RUN_INTEGRATION=1 -e RUN_INDEXING_E2E=1 indexing-worker pytest backend/tests/unit backend/tests/integration -q -p no:cacheprovider
docker compose exec -T backend ruff check backend scripts
docker compose exec -T backend ruff format --check backend scripts
# typecheck/lint/test/build trong frontend container; actual HTTP smoke;
# dataset/source/worker/job/verify/repeat/orphans qua CLI trong worker image.
```

| Lớp | Kết quả |
| --- | --- |
| Backend unit | 52 passed |
| Backend real integration | 4 passed, gồm model/storage/HTTP/worker fault/recovery/reindex/repair và PG migration |
| Backend tổng | 56 passed, real-model test được bật, không dùng skip làm pass |
| Frontend unit | 8 passed |
| Ruff/format, TypeScript/ESLint, Vite production build | PASS |
| Real HTTP live/ready/OpenAPI/Swagger/UI/proxy | PASS |
| Chromium desktop/mobile regression | 6 passed,0 skipped/failed/flaky |
| Full batch/repeat/IDs/hash/count/orphan verification | PASS |

Fault injection được ghi rõ: MinIO PUT bị ngắt, Qdrant upsert transient error, lease hết hạn bằng DB update và corrupt storage fixture. CLIP forward cùng PG/MinIO/Qdrant vẫn thật. Test xác nhận same-key409, crash-resume identity, stale-token refusal, bounded retries, job pagination, ảnh lỗi không phá ảnh hợp lệ, missing-vector repair, metadata dedup và old/new collection preservation. Không tuyên bố đây là actual daemon outage hoặc SIGKILL worker test.

Có Qdrant SDK warnings vì API key qua HTTP local; Compose data network private, chưa là TLS production. Một lượt unit trong sandbox bị treo khi dùng thread/subprocess; đã ngắt và chạy native ngoài sandbox, sau đó nghiệm thu lại trong containers thành công. Docker build từng fail vì hatchling chưa có trong offline cache; đã sửa bootstrap và build cuối pass. Không còn failures chưa giải quyết trong scope nghiệm thu này.

## I. Giới hạn đã biết

- Local single-tenant operator tokens, chưa public user/tenant auth/TLS/least-privilege service roles/quotas/backup hardening. Không dùng original EXIF-sensitive hoặc nonfixture data chưa chốt rights/privacy.
- Thumbnail generation optional chưa triển khai; content variant thumbnail fallback original. Original filename không là identity/path; CLI report giữ filename nguồn.
- Delete workflow, automatic garbage collection/scheduler, mutation catch-up journal và automatic active-index activation/rollback chưa triển khai. Delete kind fail closed409; orphan scans report-only, không xóa dữ liệu ứng dụng.
- Idempotency expires_at24h được lưu, chưa automatic TTL GC. Cursor bound job/watermark nhưng chưa có time-expiry policy; không tự reset về page1.
- CUDA, large corpus, process SIGKILL/concurrent live ingest stress và cross-browser matrix đầy đủ chưa được đo. Lease fencing/recovery được kiểm tra bằng state/nonce thật, không suy ra production reliability SLA.
- Cần review model trong-domain/language/domain bias và corpus/qrels/quality gates trước đánh giá retrieval. Chưa có online search, RAG hoặc Agent.

## J. Sẵn sàng cho Prompt 05

**Có nền tảng indexing sẵn sàng để triển khai Semantic Search khi người dùng yêu cầu.** Đã có10 image embeddings thật trong collection manifest cuối, verified metadata/originals, compatible CLIP text branch/tokenizer cache, model/index registry và private image content endpoints. Ingestion index cấu hình trong .env là UUID ở mụcE; write token riêng không được công bố trong report.

Prompt05 cần text/image query encoder ở online process, matching loaded-model capability và explicit active pointer activation, metadata eligibility/hydration/filter contracts, retrieval endpoint, genuine relevance tests và instrumentation latency. Không tự bật search-ready hoặc dùng worker như synchronous search engine. Prompt04 dừng tại đây.
