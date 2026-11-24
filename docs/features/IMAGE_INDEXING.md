# Nhập ảnh và vận hành indexing

Phase 04 dùng PostgreSQL durable queue và worker process riêng trong modular monolith. API chỉ validate/decode có giới hạn và lưu original; không chạy CLIP trong HTTP request. Xem [model](EMBEDDING_MODELS.md), [vector](VECTOR_INDEX_DESIGN.md) và [kết quả nghiệm thu](../archive/INDEXING_TEST_REPORT.md).

## 1. Cài đặt và khởi động

Từ project root, cài Docker và prerequisites theo [SETUP](../operations/SETUP.md). Giữ `.env` hiện có; không chạy lại generator để đổi passwords của volumes. Project mới dùng `python3 scripts/init_env.py`; generator sinh read/write tokens riêng. Project từ Phase 03 cần thêm `WRITE_API_TOKEN` ngẫu nhiên >=24 ký tự trong `.env`, không dùng read token cho mutations. Không in token ra log/chat.

```bash
uv sync --project backend --extra dev --extra ml --frozen
# Download explicit; worker không tự tải model hoặc gọi mạng model hub.
uv run --project backend --extra ml python -m app.cli.download_model --output .cache/clip
python3 scripts/data/download_sample_dataset.py
docker compose build backend indexing-worker
docker compose up -d --wait
# Đăng ký manifest sau khi load/validate model thật, tạo collection nếu chưa tồn tại.
docker compose --profile indexing run --rm -T indexing-worker python -m app.cli.indexing register --version clip_v1
```

Lấy `index_id` từ output register, thêm `INGESTION_INDEX_ID=<UUID>` vào `.env`. Cache `.cache/clip` mount read-only tại `/models/clip`; weights public phải readable bởi UID10001, downloader đã đặt mode0644. Backend API không cài extra ml hoặc nạp weights; image worker dùng cùng Dockerfile với `INSTALL_ML=true`.

```bash
# Cập nhật env cho API và chạy worker liên tục.
docker compose up -d --wait backend
docker compose --profile indexing up -d indexing-worker
# Thay INDEX_UUID bằng UUID thật vừa register, không dùng literal placeholder.
bash scripts/data/index_sample_dataset.sh INDEX_UUID
bash scripts/verification/verify_index.sh INDEX_UUID
# Chỉ mark ready khi kiểm chứng trọn vẹn; không đổi active search pointer.
docker compose --profile indexing run --rm -T indexing-worker python -m app.cli.indexing verify --index INDEX_UUID --mark-ready
```

Lệnh `verify` trả nonzero khi chưa đạt: còn task sống, image embeddings thiếu, object/vector sai hoặc orphan vectors. Có thể chờ job bằng `python -m app.cli.indexing job --job JOB_UUID` qua cùng `docker compose ... run --rm -T indexing-worker`. Worker `--once` chạy hết items đến hạn hiện tại rồi thoát; không chờ retry_wait trong tương lai. Worker liên tục xử lý retry đúng hạn và phục hồi sau restart. Nhiều processes dùng `docker compose --profile indexing up -d --scale indexing-worker=2`; mỗi process giữ một model, RAM/batch cần được đo trước tăng scale.

## 2. API và quyền

`POST /api/v1/images`: multipart đúng một `image` và `metadata` JSON text. Metadata yêu cầu `source_dataset`, `license`, `rights_ref`, optional title/description/caption/tags/source_uri. Tags NFC/lowercase/trim, không tự tạo caption hoặc suy đoán quyền sử dụng. Tất cả mutations cần write Bearer token và `Idempotency-Key`; read token chỉ đọc. Swagger chứa upload form và typed response schemas.

- 202 chỉ sau original bytes đã PUT rồi GET/hash verify, PG receipt và queued job durable.
- Cùng key/body replay identity/response đã lưu; khác body trả409.
- SHA-256 toàn bytes gốc xác định một image UUID trong corpus. Duplicate không ghi đè metadata; target embedding ready trả200 available, live task trả cùng job, chưa indexed tạo task mới.
- Original available chưa có nghĩa searchable: cần embedding ready ở đúng index. Không có semantic search API trong Phase 04.
- GET image detail và authenticated content proxy trả private/no-store/nosniff. Thumbnail optional chưa tạo; variant thumbnail fallback original với đúng MIME. Không trả presigned/bearer URL hoặc bucket credentials.

`POST /api/v1/index/jobs` hỗ trợ registered source snapshot (`ingest_dataset`), `reindex` và `retry`. API không nhận filesystem path. Delete contract được giữ như feature disabled409; không enqueue hoặc xóa dữ liệu. GET job có aggregate counts toàn job, item page/cursor gắn job+watermark, started/finished times và safe error summary. Không lộ object paths hoặc claim tokens.

## 3. Workflow và khôi phục

Validate actual content trong subprocess giới hạn1GiB address space/3s CPU, deadline decode mặc định2s; JPEG/PNG/WebP một frame, 20MiB, 25 triệu pixels, cạnh10.000. EXIF transpose và alpha composite lên trắng, RGB, processor official. HTTP upload cap21MiB kể cả multipart, metadata64KiB, total deadline30s; health/core requests giữ deadline2s.

Reserve image/job awaiting_input trong PG → PUT immutable original theo UUID/hash → GET/hash verify → PG image_objects receipt, image available và item queued → claim SKIP LOCKED → decode/preprocess → batch CLIP → normalize/shape/finite checks → Qdrant wait applied + retrieve + exact queryability → claim/lease/source revision check → embedding ready và job terminal.

Item queued → processing → succeeded; transient failure → retry_wait với exponential backoff+jitter, tối đa3 attempts; permanent input/vector lỗi → failed. Job aggregate succeeded/partial_failed/failed. Heartbeat gia hạn lease120s; stale lease bị revoke, attempt cũ ghi lease_lost, claim cũ không publish được. Hard timeout600s kết thúc lượt worker; process restart phục hồi lease, không giả định cancel Python thread sẽ dừng compute ngay. DB/MinIO/Qdrant đều reusable clients/pools.

| Điểm lỗi | Khôi phục thực tế |
| --- | --- |
| DB reserve xong, original chưa có | awaiting_input không claim; retry upload cùng key hoặc watchdog kiểm tra object, quá grace600s thì item failed |
| PUT thành công, receipt/queued commit lỗi | Worker đọc deterministic original, verify hash và hoàn tất acceptance; không tạo identity mới |
| Preprocess/inference lỗi | Isolate input lỗi, retry transient hữu hạn, giữ original và attempt history |
| Qdrant write thành công, PG ready commit lỗi | PG embedding chưa ready; replay same UUID, verify rồi CAS publish |
| Worker chết | Lease timeout/reclaim, nonce cũ không được publish; vector payload revision được kiểm tra lại |
| Object/vector mất sau ready | `verify --repair` hạ đúng embedding và tạo repair job; giữ các index cũ |
| Orphan object/point | CLI report riêng, không tự xóa; cần recheck references và writer quiescence trước cleanup vận hành |

Reconcile thủ công hoặc scheduler vận hành gọi `verify --repair` theo từng index. Chưa cấu hình scheduler tự động/garbage collection hoặc deletion workflow. Không xóa originals khi gặp transient failure; `.env`, volumes và collections cũ được giữ.

## 4. CLI thực tế

Tất cả lệnh dưới bắt đầu bằng `python -m app.cli.indexing` trong worker image hoặc native environment có URL đúng theo SETUP:

| Command | Chức năng |
| --- | --- |
| register --version clip_v1 | Load model và đăng ký immutable manifest/index, không recreate collection |
| model | Xem manifests/config đã đăng ký |
| image --input /datasets/sample/coffee.png --index UUID --name samples --license CC0-1.0 --rights-ref datasets/sample_manifest.json | Nhập một ảnh |
| dataset --input /datasets/sample --index UUID --name samples --license per-file --rights-ref datasets/sample_manifest.json | Scan recursive, metadata.jsonl, report từng file, durable originals và đăng ký object manifest source |
| source --source UUID --index UUID --key KEY | Tạo batch job từ source đã materialize, không đọc arbitrary server path |
| job --job UUID | Tiến độ, counts và safe errors |
| retry --job UUID --items ITEM_UUID --key KEY | Job mới liên kết retry_of, chỉ failed recoverable items; history cũ giữ nguyên |
| reindex --index NEW_INDEX_UUID --images IMAGE_UUID --key KEY | Tạo job từ originals có sẵn, target building; không overwrite collection cũ |
| worker --index UUID [--once] | Worker liên tục hoặc drain các items đến hạn |
| verify --index UUID [--repair] [--mark-ready] | Đối chiếu receipts/hash/finite/dimension/IDs/exact count và sửa thiếu dữ liệu khi được yêu cầu |
| orphans | Scan tối đa10.001 original keys và so PG identities; report-only, không xóa |

Metadata CLI được materialize từ local files vào MinIO trước khi worker chạy. Dataset scan là administrative local CLI; API chỉ sử dụng registered object manifest checksum. Không cho untrusted clients tạo arbitrary source root. Dataset trên1.000 files cần chia manifest; ảnh lỗi được báo riêng, không giả accepted. Caption/tags optional không được tự fabricate.

## 5. Nghiệm thu và logging

`make verify-indexing` tương đương `python3 scripts/verification/verify_indexing.py`: build, actual model tests, batch source10 ảnh, repeat và cross-storage verify. Verifier tạm dừng worker đang chạy để worker benchmark không chạy tranh, rồi khôi phục trong finally. Lượt nghiệm thu ghi rõ worker_was_running/build_requested. Chuẩn bị cache/data/index trước; script không tự tải model hoặc thay active pointer.

Worker logs JSON ở stderr, CLI result JSON ở stdout: job_id/item_id/image_id/index_id/stage/attempt_no/error_category được allowlist, không log credentials/raw metadata. Stage timings trong worker report và source_ref nội bộ; API không expose source_ref. `make worker-logs` theo dõi worker; `make worker-up` khởi động profile.

Verifier full dùng collection fixture đúng10 ảnh; với corpus riêng lớn hơn, dùng `verify --index UUID` để kiểm chứng theo receipts/IDs thực tế, không xóa dữ liệu để khớp count10. Khi dừng toàn bộ stack có worker, dùng `docker compose --profile indexing down`; named volumes vẫn được giữ. `docker compose --profile indexing stop indexing-worker` chỉ dừng worker, jobs vẫn durable trong PostgreSQL.

Phase 08 bổ sung caption_source optional≤160 ký tự và GET image detail trả caption. Attribution không có nghĩa verified. Fingerprint upload cũ giữ nguyên khi không có caption_source. [Corpus COCO và index mới](../research/RAG_DATASET.md).
