# Core Semantic Search — Phase 05

Tài liệu baseline Phase 05. Phần text/image core vẫn áp dụng; advanced fusion/multi-intent/reranking đã được triển khai ở Phase 06 theo [ADVANCED_SEARCH_API](ADVANCED_SEARCH_API.md), [MULTIMODAL_SEARCH](MULTIMODAL_SEARCH.md) và [báo cáo](../archive/ADVANCED_SEARCH_TEST_REPORT.md). Các đoạn “chưa triển khai Phase 06” bên dưới mô tả thời điểm bàn giao Phase 05.

Đã triển khai text-to-image và image-to-image bằng CLIP/Qdrant thật, trên index Phase 04. Không gọi LLM, RAG hoặc Agent; chưa có text+image fusion/multi-intent/reranking. Xem [API](SEARCH_API.md), [performance](../research/SEARCH_PERFORMANCE.md) và [test report](../archive/SEARCH_TEST_REPORT.md).

## 1. Khởi động

Giữ nguyên model cache và collection đã indexing. Cần index ready/đã verify theo [IMAGE_INDEXING](IMAGE_INDEXING.md).

```bash
docker compose build backend indexing-worker frontend
# CLI verify objects/vectors, load paired encoder, warmup, rồi mới publish active pointer.
docker compose --profile indexing run --rm --no-deps -T indexing-worker python -m app.cli.search --activate INDEX_UUID
```

Thay INDEX_UUID bằng registry ID thật, ví dụ index fixture được ghi trong SEARCH_TEST_REPORT. Đặt `SEARCH_ENABLED=true` trong `.env`, rồi:

```bash
docker compose up -d --wait backend frontend
```

API image hiện có extra ml và mount `.cache/clip` read-only. Mỗi API process load model/tokenizer một lần qua lifespan; indexing worker vẫn là process riêng. Cache sai/mất hoặc active index chưa ready thì process vẫn live nhưng search not_ready; không tự tải model, chọn collection khác hoặc kích hoạt index không kiểm chứng. Startup warmup synthetic tensor chỉ làm nóng kernels, không tạo hoặc lưu dữ liệu indexing.

UI tại http://localhost:5173: nhập read token vào ô Token truy cập, chọn text hoặc image, Top-K1…50 rồi submit. Token chỉ giữ trong memory; ảnh kết quả fetch Authorization → blob URL và revoke khi không dùng. Không có credentials trong VITE_* hoặc image URLs. Multimodal option bị disable vì fusion chưa triển khai.

## 2. Pipeline và modules

Text: auth/body/schema → NFC/whitespace validation → matching tokenizer, token-limit check → CLIP text tower → L2/finite/dimension validation → Qdrant candidates → deterministic dedup/ranking → batch PG metadata/eligibility → private object HEAD checks → result DTO → JSON serialization/final send.

Image upload: auth/multipart limits → memory/spooled temp file → cùng hàm resource-limited decode/RGB/EXIF/alpha preprocessing của Phase 04 trong decoder process đã preload → cùng CLIP image tower/processor → shared retrieval/enrichment path. Query bytes không được ghi vào corpus, MinIO, image/job rows hoặc history. Existing image_id dùng verified stored vector cùng index để tránh re-encode; có thể exclude query image qua exclude_self.

Modules: `schemas/search.py`, `embeddings/query_encoder.py`, `search/registry.py`, `runtime.py`, `vector_retriever.py`, `ranking.py`, `search_service.py` và `repositories/image_repository.py`. ClipQueryEncoder bọc ClipEncoder hiện có, không sửa image-encoder source fingerprint; vẫn dùng collection/manifests Phase 04, không reindex.

## 3. Tương thích và active index

Nguồn truth là PG active_search_index, generation và immutable model/index registry. Activation CLI full-verify và load đúng manifest trước transaction lock/swap. Runtime snapshot được pin lúc startup; mỗi search kiểm tra active generation/model/status và Qdrant dimension/Cosine/metadata. Search không auto-create/recreate collections. Pointer thay đổi trả INDEX_SWITCHING tới khi runtime được reload đúng model.

CLIPTokenizerFast/checkpoint/processor lấy từ cùng local pinned cache đã kiểm hash. Text max2.000 chars và77 model positions gồm special tokens; không silent truncation. Dimension lấy từ model projection_dim; fixture hiện512, float32/L2/Cosine. CPU baseline, CUDA path dùng runtime/device tương ứng nhưng chưa có CUDA measurements.

## 4. Retrieval, filters và eligibility

Default Top-K10, max50 (config max≤100 theo v1 baseline), candidates50 hoặc ít nhấtK, cap1.000. Qdrant query_points lấy actual scores; không relevance threshold chưa calibrated. Cosine không là xác suất. Rank descending score rồi UUID để tie ổn định trong candidate pool; dedup UUID, không pad kết quả để đủK.

Basic filters: source_dataset, media_types, tags_any/tags_all, city, width/height ranges, captured_from/to. Payload-supported fields được pushdown; tất cả predicates được PG recheck, captured_at dùng PG vì projection chưa có. Category chưa có schema/payload nên không nhận, không suy đoán từ caption hoặc query. Null metadata không thỏa positive predicate; không fabricate caption/tags.

Batch PG query join images available, image_embeddings ready đúng index/source SHA/metadata_revision, original receipt chưa deleted và matching hash. Tags lấy batch query thứ hai, không N+1 PG lookup. Payload phải khớp image/index/manifest/source/revision. Object HEAD xác minh existence/size trước result; missing object bị loại với warning, service outage trả503. API result không chứa object storage keys hoặc full image binaries. Content proxy có trong Phase 04, thumbnails vắng fallback originals.

Candidate pool có giới hạn: eligibility filtering có thể trả ít hơnK dù corpus còn eligible item ở sâu hơn. Response ghi effective candidate_count/truncated và warning khi pool chạm cap; không nới filter mù quáng hoặc fake results.

## 5. Admission, lifecycle và failures

Inference executor1 thread/API process,1 slot, tối đa8 waiting requests và queue wait50ms. Cancel/timeout không trả slot trước khi compute thật kết thúc; CPU/GPU thread không bị giả là đã dừng. Model init được lifespan tuần tự hóa, shutdown đợi executor rồi bỏ encoder/registry references. Online queue tách durable indexing worker; chưa có scheduler chia GPU giữa processes.

Errors phân biệt INVALID_INPUT/TEXT_TOKEN_LIMIT/CORRUPT_IMAGE, FEATURE_DISABLED, NOT_READY, MODEL_INDEX_MISMATCH, COLLECTION_UNAVAILABLE, INDEX_SWITCHING, INFERENCE_BUSY, INFERENCE_FAILED và dependency/timeouts. Empty eligible set là200 results=[], không dùng làm fallback cho failure. Search không log text/images/headers hoặc persist history mặc định. Bounded telemetry chỉ IDs, modality, versions, durations/status trong memory.

## 6. Decoder reuse sau baseline đo lường

Baseline đầu có image preprocessing median khoảng430ms. Profiling riêng xác nhận Pillow import/startup và PNG serialization tạo overhead. Search runtime hiện preload một decoder process riêng, gọi đúng hàm decode của Phase 04 và truyền JSON header + RGB bytes qua framed pipes, không pickle và không PNG re-encode. Input/file/dimensions/output byte lengths được kiểm tra; address-space1GiB, soft CPU deadline mỗi ảnh và parent deadline2s được giữ. Process lỗi/timeout bị terminate/kill, request tiếp theo có thể khởi tạo lại; runtime shutdown đóng process/pipes.

Đây là process nội bộ cho resource isolation, không thêm network service. Pixel-equivalence JPEG/PNG/WebP và process restart được test; image-encoder/decoder source fingerprints không đổi, không reindex. Benchmark trước/sau giữ cùng model/corpus/warmup/concurrency; không phải cache theo query ảnh. User image không được ghi vào permanent storage.
