# Vector indexing và tương thích storage

PostgreSQL là source of truth cho UUID/lifecycle/jobs/registry; MinIO chứa originals private, Qdrant là projection rebuildable. Không có distributed ACID; xem failure matrix tại [IMAGE_INDEXING](IMAGE_INDEXING.md).

## Collection và identity

Tên `images_<version>_<config_sha256_prefix12>`, mỗi immutable model/index riêng. CollectionManager lấy dimension từ model đã load, distance Cosine, metadata phải khớp toàn bộ manifest_sha256/index_id/config_sha256. Collection absent thì create; existing dimension/metric/metadata mismatch thì fail. Không recreate/delete collection ứng dụng, không arbitrary dimension hoặc random vectors.

Point ID là image UUID trong từng collection; cùng ảnh khác index dùng cùng UUID ở collection khác, không collision logical identity. Original key `images/original/<image_uuid>/<sha256>.<decoded_extension>` do server sinh, không dùng upload filename. Exact hash identity dùng một original, không coi ảnh tương tự thị giác/ngữ nghĩa là duplicate.

Payload allowlist: image_id, index_id, manifest_sha256, source_sha256, metadata_revision, image_status, width, height, media_type, tags; source_dataset/city chỉ khi có. Không đưa raw EXIF, captions dài, object paths hoặc auth vào payload. Chưa thêm payload indexes khi chưa có retrieval/filter workload; Prompt 05 bổ sung dựa vào query thực.

## Publication và kiểm chứng

Batch upsert wait=True yêu cầu UpdateStatus.COMPLETED, retrieve lại ID/payload/vector và so finite/shape/tolerance, rồi exact query với filter ID để xác nhận queryable. Chỉ sau đó transaction lock image rồi item, kiểm tra nonce/lease chưa hết, image available và source digest/revision còn khớp, mới ghi image_embeddings ready. PG authoritative eligibility phải được Prompt 05 recheck; vector payload riêng không đủ làm kết quả.

`verify` đối chiếu từng embedding ready với original bytes/PG receipts, vector digest/dimension/norm/payload, exact point count, expected item image IDs và live tasks. Orphan vectors report riêng, không xóa mù quáng. `verify --repair` hạ embedding lỗi và enqueue durable repair, giữ nguyên originals. Orphan MinIO original detection CLI riêng report-only; không garbage collect object từ writer đang sống.

## Reindex và active pointer

Register model/version mới → collection building mới → reindex từ original UUIDs → verify receipts/count/IDs → mark ready. Collection cũ giữ để đối chiếu và rollback. Active_search_index table đã có migration nhưng chưa tự set pointer; Prompt 05 phải load matching model/capability trước activation transaction. Không quảng bá search-ready vì chỉ có vector collection.

Local fixture corpus không có concurrent metadata mutation/delete API; catch-up mutation journal, deletion fencing/cleanup mọi index và automatic activation/rollback chưa là functionality của Prompt 04. Delete job endpoint trả FEATURE_DISABLED, không thực hiện destructive operations. Source/index manifests immutable, không silently mix embeddings.
