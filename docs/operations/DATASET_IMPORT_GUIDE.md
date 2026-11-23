# Nhập dữ liệu sau triển khai

Không có crawler ngầm. Dùng ảnh do người vận hành cung cấp, có nguồn/license phù hợp. Docker mount `DEPLOY_DATASET_PATH` vào `/datasets` read-only; CLI kiểm tra input nằm trong root được cấu hình, không theo symlink ra ngoài. Mặc định tối đa1000 JPEG/PNG/WebP mỗi lượt,20MiB/ảnh, giới hạn pixels/side/decode theo settings.

## Manifest và validation

Đặt ảnh trong thư mục, tùy chọn `metadata.jsonl`, mỗi dòng là object UTF-8 có filename tương đối duy nhất:

```json
{"filename":"photos/image-01.jpg","title":"Tiêu đề do nguồn cung cấp","caption":"Mô tả có nguồn","tags":["tag"],"license":"LICENSE-ID","rights_ref":"https://source.example/item"}
```

Đây là schema minh họa, không phải dữ liệu đã nhập. Filename phải tồn tại, không absolute/traversal/duplicate. Các metadata fields dùng `ImageMetadataInput`: unknown fields/control characters bị từ chối; caption multiline hợp lệ được giữ nguyên. City/captured_at/knowledge cần đúng contract riêng, không tự suy từ caption.

```bash
python3 scripts/deploy.py import --input /absolute/datasets/batch-v1 --name my_dataset --version v1 --license LICENSE-ID --rights-ref https://source.example/dataset --dry-run
```

Input phải nằm dưới DEPLOY_DATASET_PATH. Dry-run decode/hash/schema thật nhưng không khởi tạo data services, không upload, không đăng ký model/collection. Kết quả có discovered/validated/accepted/failed/ignored; accepted=0 trong dry-run. Bất kỳ ảnh lỗi nào khiến exit nonzero. Sửa nguồn rồi chạy lại; không đổi extension/MIME để né decoder.

## Model, ingestion và activation

Chuẩn bị đúng cache trước, rồi:

```bash
python3 scripts/deploy.py model-verify
python3 scripts/deploy.py import --input /absolute/datasets/batch-v1 --name my_dataset --version v1 --index-version my_dataset_v1 --batch-size 4 --license LICENSE-ID --rights-ref https://source.example/dataset
python3 scripts/deploy.py status
python3 scripts/deploy.py check
```

Index version chỉ lowercase/digits/underscore, tối đa40 ký tự. Model là CLIP đã được pin trong settings, không tự thay model khi lỗi. Import register collection bằng dimension/manifest thực; kế thừa ảnh available/ready của active index cũ bằng các reindex jobs, ingest ảnh mới qua pipeline hiện có, chờ worker hữu hạn, verify receipts/objects/points rồi activate. CLI restart API/worker để nạp generation mới; frontend không rebuild. Có thể có khoảng maintenance ngắn, không hứa zero downtime.

Index cũ và dữ liệu cũ giữ nguyên. Failed import không được tự activate; có thể đã có durable accepted jobs/objects để sửa và retry. Dùng version mới khi xây replacement index. Exact-byte identity dựa SHA-256; idempotency replay không có nghĩa accepted count là số ảnh mới. Không tự cập nhật metadata của ảnh trùng bytes bằng một manifest mới; đó là workflow sửa metadata/reindex cần review riêng.

## Đếm và đối chiếu

Ảnh gốc là stored object; thumbnail hiện được tạo theo yêu cầu từ original. Schema hỗ trợ nhiều roles, nhưng không giả định mỗi ảnh luôn có hai stored objects. Dataset còn có manifest object. Nhiều index có nhiều embedding receipts cho cùng image UUID. Vì vậy images, objects, receipts và tổng vectors mọi collection không bắt buộc bằng nhau. Gate activation so sánh **ready embeddings của target index**, đúng UUID/model/metadata revision/hash, không orphan/missing point và không live jobs. `status` tách active index với tất cả collections.

Khi có lỗi, xem `logs --service worker`, job IDs trong report và `app.cli.indexing job/retry/verify` qua private operator access. Không xóa collection/object thủ công để che lỗi. Model mismatch cần cache đúng hoặc replacement index/re-embedding, không đổi dimension của collection đang dùng.

## Tri thức quan hệ tùy chọn

Đặt file JSON dưới dataset root rồi:

```bash
python3 scripts/deploy.py knowledge --input /absolute/datasets/knowledge.json
python3 scripts/deploy.py knowledge --input /absolute/datasets/knowledge.json --apply
```

Lệnh đầu dry-run mặc định; apply ghi transaction. Schema có entities/aliases/types, relationships/source_ref/verified và image_entities liên kết UUID ảnh thật. [KNOWLEDGE_BASE_DESIGN](../features/KNOWLEDGE_BASE_DESIGN.md) mô tả schema đầy đủ. Phải có provenance và referential integrity; production từ chối fictional fixture knowledge. Caption không tự biến thành knowledge graph. Chỉ bật Agent khi dữ liệu/tool prerequisites phù hợp; import ảnh không tự bật RAG hoặc xác nhận mọi constraint.
