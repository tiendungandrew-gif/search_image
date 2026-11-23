# Corpus có caption cho RAG — Prompt08

Ngày06/11/2026. Dùng pipeline ingestion/indexing hiện có. JPEG và annotations tải về bị Git/Docker ignore, MinIO giữ bucket private.

## Nguồn và provenance

COCO val2017, chọn500 ảnh với seed42 và license IDs4/5/7/8. Caption dùng annotation ID nhỏ nhất; toàn bộ caption gốc được giữ trong provenance. Không tự tạo caption/tag hoặc coi imported captions là human judgments cho câu trả lời RAG. Câu trả lời tiếng Việt trích nguyên văn caption tiếng Anh.

Giữ license của từng ảnh, URL Flickr và stable source ID. Annotation CC-BY-4.0 không thay giấy phép ảnh: [điều khoản COCO](https://cocodataset.org/#termsofuse), [nguồn tải](https://cocodataset.org/#download). Dữ liệu nghiên cứu local, không tự publish ảnh.

Downloader đọc đúng member captions_val2017.json qua HTTP Range của bucket chính thức `images.cocodataset.org` tại S3 HTTPS; pin ETag, kiểm CRC và SHA-256. Checksum được quan sát trên dữ liệu tải qua TLS, không phải chữ ký nhà phát hành. Không tắt TLS verification.

```bash
backend/.venv/bin/python -m app.cli.download_coco --count 500
```

`datasets/coco_phase08_v1/` gồm images/, metadata.jsonl, selection.json, provenance.json và manifest.json. Metadata có caption_source và rights_ref. Chạy lại xác minh cache/checksum và tiếp tục phần thiếu; không overwrite file khác nội dung. Tập mới dùng `--output datasets/coco_phase08_v2 --seed ...`, tối đa1.000 ảnh/lượt.

## Nhập và chuyển corpus

```bash
docker compose build backend indexing-worker
python3 scripts/data/prepare_rag_corpus.py \
  --output docs/verification/phase08_corpus_run_v2 --activate
# Đặt INGESTION_INDEX_ID trong .env bằng target_index_id ở output/summary.json.
docker compose --profile indexing up -d --wait backend indexing-worker
docker compose restart backend
```

Script kiểm download hashes, baseline, tạo collection mới, nhập500 COCO, copy originals của10 ảnh cũ, chạy worker, verify rồi mới activate khi có cờ. Bỏ `--activate` để chuẩn bị riêng. Thư mục output phải mới; shell cần nhóm Docker, có thể dùng `sg docker -c 'LỆNH'`. Worker nền vẫn dùng INGESTION_INDEX_ID cấu hình; khi nhập tiếp cần chọn đúng UUID target. Index/model/ảnh cũ được giữ để rollback; không overwrite experiments hoặc snapshots cũ.

Caption attribution dùng cột caption_source có sẵn; `verified=false` vẫn giữ. Optional field không đổi fingerprint upload cũ khi thiếu attribution. Ảnh trùng SHA không ghi đè metadata. CLI chưa có workflow chỉnh sửa/xóa metadata hoàn chỉnh.

## Workload và human review

`evaluation/rag/test_cases/coco_v1.jsonl` có câu hỏi VI/EN về chó, xe đạp, đồ ăn và tàu; đây là inputs chờ đánh giá, không phải relevance labels.

```bash
backend/.venv/bin/python scripts/run_local.py --env-file .env -- \
  backend/.venv/bin/python -m app.cli.rag \
  --results evaluation/results/phase08_completion --requests 32 \
  --workload evaluation/rag/test_cases/coco_v1.jsonl
```

Mỗi câu hỏi chạy R1 search-only, R2 metadata, R3 cap3, R4 cap1. Giữ failures/timeouts và số đo từng request. Tạo trang review bằng frozen result:

```bash
backend/.venv/bin/python scripts/run_local.py --env-file .env -- \
  backend/.venv/bin/python -m app.cli.rag \
  --review-pack PATH_TO_FROZEN_RESULT.json \
  --output .cache/evaluation/rag_review_v2.html
```

HTML offline chứa ảnh thật, câu hỏi, answer và evidence; không chứa token và không tự lưu. Chấm relevance/faithfulness0…2 hoặc unknown, claims/unsupported claims; điền tên và xác nhận sau khi review đủ. Xuất draft để giữ tiến độ. CLI kiểm hash, coverage và schema:

```bash
backend/.venv/bin/python -m app.cli.rag \
  --review PATH_TO_VERIFIED_LABELS.json --experiment PATH_TO_FROZEN_RESULT.json
```

Chưa có human review thì semantic quality tiếp tục pending. Citation ID/quote checks không thay đánh giá nội dung hoặc Recall@10.
