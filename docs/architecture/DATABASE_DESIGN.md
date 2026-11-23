# Thiết kế PostgreSQL, Qdrant và MinIO

Cập nhật tài khoản/UI 08/11/2026: xem [thiết kế quyền](../architecture/ACCESS_CONTROL.md) và [hướng dẫn đăng nhập](../operations/ACCOUNTS.md). Các hướng dẫn dùng data token trước đây chỉ áp dụng khi bật legacy; mặc định mới dùng session tài khoản.
## Hoàn thiện Prompt 09 — 06/11/2026

Đã bổ sung bộ địa danh NPS có nguồn:3 ảnh thật,4 entities,3 quan hệ và3 liên kết ảnh. Index phục vụ hiện513 ảnh, generation3; index510 ảnh cũ giữ nguyên. Workflow Anh/Việt/alias, Gemini planner và RAG thật đã được kiểm tra. Planner có trace từng attempt; prompt tools và RAG context đã rút gọn, citation provenance vẫn giữ đầy đủ trên server. Bộ kiểm tra mới đạt200 backend,21 frontend unit và24 browser full tests cùng6 ca browser nhánh cuối. Chất lượng do người đánh giá vẫn chờ; số đo latency và trạng thái target3s xem [báo cáo Prompt09](../archive/PHASE09_TEST_REPORT.md), dữ liệu/nguồn tại [PUBLIC_LANDMARK_DATASET](../research/PUBLIC_LANDMARK_DATASET.md).

## Schema runtime Prompt09 — 06/11/2026

Migration `20261106_agent_knowledge` cộng thêm entities/entity_relationships/image_entities, khớp nhu cầu đã thiết kế ở Prompt02. Không sửa dữ liệu ảnh/embedding/index; tổng runtime hiện16 bảng. [KNOWLEDGE_BASE_DESIGN](../features/KNOWLEDGE_BASE_DESIGN.md) ghi chính xác fields/indexes/provenance/import guard và chiến lược đồng bộ PG–Qdrant–MinIO. Serving DB có510 ảnh, knowledge vẫn0 entities/0 relationships/0 links. Thiết kế ER đầy đủ bên dưới gồm cả phạm vi các phase sau.

Phiên bản 1.1.0 · 2026-11-03 · Logical schema Prompt02; migration/implementation hiện hành xem mục8/9. Đã đối chiếu data contracts tại [SAD](SAD.md) và luồng tại [SYSTEM_ARCHITECTURE](SYSTEM_ARCHITECTURE.md).

## 1. Quy ước và nguồn sự thật

PostgreSQL là nguồn identity/lifecycle/metadata/job/index registry; Qdrant là vector + payload projection có thể tái tạo; MinIO là bytes private. Không có distributed ACID. Một `images.id` UUID cũng là Qdrant point ID trong mỗi collection và thành phần object key. Single-tenant corpus `default`; nếu thêm tenancy phải đổi uniqueness và mọi authorization predicate trước.

Ký hiệu schema dưới: `!` = NOT NULL, `?` = nullable; `PK`, `FK`, `UQ` có nghĩa SQL thông thường. Tất cả PK/FK đều được ghi; các field không có dấu `?` không được hiểu ngầm là nullable. UUID sinh server; timestamp dùng `timestamptz`, duration dùng millisecond `double precision` finite ≥0; JSON dùng `jsonb` với object-shape validation ở application. ID trạng thái là `text` có CHECK allowlist, tránh migration enum khó sửa. Hash SHA-256 dạng `char(64)` kiểm tra lowercase hex. Tất cả FK không ghi CASCADE mặc định `ON DELETE RESTRICT`; tạo B-tree index cho FK phục vụ join/cleanup trừ khi đã là prefix PK/UQ. Không lưu vector lớn trong PG.

## 2. PostgreSQL schema

### 2.1 `images` — identity và lifecycle

| Cột | Kiểu / ràng buộc |
| --- | --- |
| id | uuid ! PK |
| sha256 | char(64) ? UQ khi non-null; chỉ nullable sau purge của tombstone deleted |
| status | text ! CHECK pending_upload/pending/available/deleting/deleted/failed |
| media_type | text ! CHECK image/jpeg, image/png, image/webp |
| byte_size | bigint ! CHECK >0 |
| width, height | integer ! CHECK >0, <= giới hạn cấu hình khi ingest |
| metadata_revision | bigint ! default 1 CHECK >0 |
| created_by | text ! principal cấu hình, không FK tới bảng user chưa có |
| created_at, updated_at | timestamptz ! |
| deleted_at | timestamptz ? |

CHECK sha256 không null trừ khi status=deleted; CHECK deleted_at hiện diện cho deleting/deleted. Index `(status,created_at,id)` và partial `(sha256) WHERE sha256 IS NOT NULL` unique. `available` chỉ nói original đã xác minh; searchable còn cần image_embeddings ready cho pinned index. Retention originals đến explicit delete; tombstone ID có thể giữ để bảo toàn FK, purge hash/metadata theo policy. Reupload hash còn tombstone trả 409 IMAGE_DELETED, không tự phục hồi nội dung đã xóa.

### 2.2 `image_metadata` — quan hệ 1:1 với ảnh

Cột: `image_id uuid ! PK FK images.id`; `title text ?` (≤256 ký tự); `description text ?` (≤4.000); `caption text ?`; `caption_source text ?`; `source_dataset text ?`; `source_uri text ?` (chỉ provenance, không tự fetch); `license text ?`; `rights_ref text ?` (bắt buộc bởi app cho dữ liệu nonfixture); `captured_at timestamptz ?`; `country_code char(2) ?`; `city text ?`; `extra jsonb ! default {}`; `updated_at timestamptz !`.

Index `(city)`, `(source_dataset)`, `(captured_at)`; không thêm GIN extra nếu chưa có query cần. Không lặp width/hash/version tại đây. Nullable metadata không chứng minh semantic condition. Rights/source được app bắt buộc cho dữ liệu nonfixture. Retention đi theo ảnh; xóa caption/EXIF-sensitive và provenance cá nhân theo yêu cầu rights, không phát raw extra ra API nếu chưa allowlist.

### 2.3 `image_tags`

Cột: `image_id uuid ! FK images.id`; `tag text !`; `source text !`; `verified boolean ! default false`; `created_at timestamptz !`. PK `(image_id,tag)`; CHECK tag đã NFC/lowercase/trim, 1…64 ký tự. Index `(tag,image_id)`. Tag duplicate từ nguồn khác được xử lý update provenance có kiểm soát, không thêm row trùng. Retention theo ảnh; verified chỉ nghĩa nguồn annotation được duyệt, không mặc định model caption là visual truth.

### 2.4 `entities`

Cột: `id uuid ! PK`; `canonical_name text !`; `entity_type text !` CHECK city/landmark/person/object/other; `locale text !`; `external_key text ? UQ`; `aliases jsonb ! default []`; `provenance jsonb !`; `created_at timestamptz !`. UQ `(canonical_name,entity_type,locale)`; index `(entity_type,canonical_name)`. Names/aliases lookup theo normalization do app quy định. Retention facts giữ theo rights của nguồn; không tự suy ra entity từ tên không rõ.

### 2.5 `entity_relationships`

Cột: `id uuid ! PK`; `subject_id uuid ! FK entities.id`; `predicate text !` allowlist located_in/has_landmark/depicts/related_to; `object_id uuid ! FK entities.id`; `source_ref text !`; `evidence jsonb !`; `verified_at timestamptz ?`; `created_at timestamptz !`. UQ `(subject_id,predicate,object_id,source_ref)`; index `(subject_id,predicate)` và `(object_id,predicate)`. Không coi quan hệ hai chiều nếu không có rule đã khai báo. Retention provenance bắt buộc; hết quyền sử dụng thì disable/remove facts và invalidate affected G5 runs, không bịa evidence thay thế.

### 2.6 `image_entities`

Cột: `image_id uuid ! FK images.id`; `entity_id uuid ! FK entities.id`; `relation text !` CHECK depicts/located_in/associated_with; `source_ref text !`; `verified boolean ! default false`. PK `(image_id,entity_id,relation)`; index `(entity_id,relation,image_id)`. Retention theo ảnh/source; chỉ verified/source phù hợp mới được dùng làm hard evidence theo policy.

### 2.7 `embedding_models`

Cột: `id uuid ! PK`; `model_name text !`; `model_revision text !`; `processor_revision text !`; `dimension integer ! CHECK >0`; `precision text !`; `normalization text ! CHECK l2`; `distance_metric text ! CHECK cosine`; `manifest jsonb !`; `manifest_sha256 char(64) ! UQ`; `license_ref text !`; `created_at timestamptz !`.

Manifest chứa tokenizer, image resolution/crop/normalization, max text tokens, code/processor hashes và inference policy. Row bất biến sau khi index tham chiếu. Không chọn dimension bằng phỏng đoán; lấy từ checkpoint pinned và runtime assertion. Retention suốt đời index/experiment tham chiếu; không xóa model artifact được báo cáo nhưng không lưu weights trong Git.

### 2.8 `search_indexes` và `active_search_index`

`search_indexes`: `id uuid ! PK`; `model_id uuid ! FK embedding_models.id`; `collection_name text ! UQ`; `status text !` CHECK building/validating/ready/retired/failed/deleting; `config jsonb !`; `config_sha256 char(64) !`; `corpus_snapshot_ref text !`; `validated_at timestamptz ?`; `created_at timestamptz !`; `retire_after timestamptz ?`. Index `(model_id,status)`. Ready chỉ sau validation report; config bất biến đối với semantic space. Giữ versions cũ đến khi drain/rollback horizon đã quyết định.

`active_search_index`: `corpus_key text ! PK CHECK corpus_key='default'`; `index_id uuid ! FK search_indexes.id`; `generation bigint ! CHECK >0`; `activated_at timestamptz !`. Duy nhất một active pointer; pointer không tự làm ready row trong table khác. Activation transaction lock row này, kiểm tra index ready + matching loaded-model capability trước publish. Lịch sử activation nằm audit/run artifact; không dùng boolean active trên nhiều rows dễ đua.

### 2.9 `image_embeddings`

Cột: `image_id uuid ! FK images.id`; `index_id uuid ! FK search_indexes.id`; `status text !` CHECK pending/processing/ready/failed/deleting; `source_sha256 char(64) !`; `metadata_revision bigint !`; `vector_sha256 char(64) ?`; `verified_at timestamptz ?`; `last_error_code text ?`; `updated_at timestamptz !`. PK `(image_id,index_id)`; index `(index_id,status,image_id)`. Ready yêu cầu vector hash/verified_at non-null; model ID suy ra từ index, không duplicate FK dư thừa. Vector hash dùng representation canonical được version trong manifest. Chỉ row ready + image available + payload revision/digest đúng được hydrate thành kết quả. Retention theo index/image; deletion cleanup các index kể cả retired.

### 2.10 `image_objects`

Cột: `id uuid ! PK`; `image_id uuid ! FK images.id`; `role text !` CHECK original/thumbnail; `derivative_version text !` (`original` cho raw); `bucket text !`; `object_key text !`; `sha256 char(64) !`; `media_type text !`; `byte_size bigint ! CHECK >0`; `verified_at timestamptz !`; `deleted_at timestamptz ?`. UQ `(bucket,object_key)`, UQ `(image_id,role,derivative_version)`. Original receipt bất biến; preview có transform version. Original byte digest khớp images.sha256; derivative digest khác được phép. Retention theo ảnh; xóa object trước đánh dấu receipt deleted sau khi xác nhận. Staging không là final image_objects; nằm source_ref trong item để cleanup không nhầm.

### 2.11 `dataset_sources`

Cột: `id uuid ! PK`; `name text ! UQ`; `kind text !` CHECK local_manifest/object_manifest; `root_config_key text !`; `manifest_ref text !`; `manifest_sha256 char(64) !`; `rights_ref text !`; `enabled boolean ! default false`; `created_at timestamptz !`. Index enabled nếu cần, UQ name đủ lookup. Chỉ admin CLI đăng ký từ root allowlist, API nhận source_id, không nhận arbitrary path/URL. Retention ít nhất tới khi source jobs và experiments được archive; root_config_key là tên cấu hình, không secret.

### 2.12 `indexing_jobs`

Cột: `id uuid ! PK`; `kind text !` CHECK ingest_upload/ingest_dataset/reindex/delete/retry; `status text !` CHECK awaiting_input/queued/running/succeeded/partial_failed/failed; `source_id uuid ? FK dataset_sources.id`; `target_index_id uuid ? FK search_indexes.id`; `retry_of uuid ? FK indexing_jobs.id`; `created_by text !`; `request_id uuid !`; `total_items integer ! CHECK >=0`; `created_at,updated_at timestamptz !`; `finished_at timestamptz ?`; `input_manifest_sha256 char(64) ?`.

Index `(status,created_at,id)` và `(created_by,created_at,id)`. CHECK nguồn/target theo kind: ingest/reindex có target, delete không cần target; retry tham chiếu job cũ. Counts chi tiết lấy aggregate item states, không coi cached counts là nguồn duy nhất. Retention đề xuất 30 ngày sau terminal; audit manifest giữ theo rights/reproduction, không xóa job còn được live retry tham chiếu.

### 2.13 `indexing_job_items`

Cột: `id uuid ! PK`; `job_id uuid ! FK indexing_jobs.id`; `image_id uuid ? FK images.id`; `index_id uuid ? FK search_indexes.id`; `source_identity text !`; `source_ref jsonb !` (private staging key hoặc registered manifest entry); `status text !` CHECK awaiting_input/queued/processing/retry_wait/succeeded/failed; `stage text !` CHECK validate/deduplicate/preprocess/embed/metadata/object/vector/verify/delete; `attempt_count integer ! default 0`; `next_attempt_at timestamptz ?`; `claim_token uuid ?`; `lease_owner text ?`; `lease_expires_at timestamptz ?`; `last_error_code text ?`; `created_at,updated_at timestamptz !`.

UQ `(job_id,source_identity)`; index `(status,next_attempt_at,created_at,id)`; `(lease_expires_at) WHERE status='processing'`; partial unique `(image_id,index_id) WHERE status IN ('queued','processing','retry_wait') AND index_id IS NOT NULL`. Một live task/image/index; job mới gặp task đang sống trả conflict hoặc liên kết existing job, không giả tạo item succeeded. processing yêu cầu token/lease/owner non-null; claim CAS guards update. Retention theo job; source_ref xóa khi terminal/retention hết, staging chỉ cleanup khi không còn active reference. `image_id` nullable cho manifest entry chưa validate/dedup.

### 2.14 `job_item_attempts`

Cột: `item_id uuid ! FK indexing_job_items.id`; `attempt_no integer ! CHECK >0`; `claim_token uuid !`; `started_at timestamptz !`; `finished_at timestamptz ?`; `outcome text ?` CHECK succeeded/transient_failure/permanent_failure/lease_lost/timeout; `stage text !`; `error_code text ?`. PK `(item_id,attempt_no)`, UQ `(claim_token)`; index `(started_at)`. Safe errors, không raw decoder stack/paths. Retention 30 ngày terminal, có thể archive technical counts; không reset attempt history khi retry job mới.

### 2.15 `search_queries`

Cột: `id uuid ! PK`; `request_id uuid ! UQ`; `principal_id text !`; `requested_mode text !`; `executed_mode text ?`; `query_text text ?`; `reference_image_id uuid ? FK images.id`; `history_opt_in boolean ! default false`; `options jsonb !` (safe config only); `index_id uuid ? FK search_indexes.id`; `outcome text !`; `processing_ms double precision ?`; `response_ms double precision ?`; `created_at timestamptz !`.

Index `(created_at,id)`, `(principal_id,created_at,id)`. CHECK query_text/reference_image_id null khi history_opt_in=false; không persist query upload bytes/hash. `response_ms` chỉ cập nhật sau final send; `processing_ms` không đại diện full API latency. Telemetry persistence best-effort, không được biến successful search thành error khi ghi audit lỗi; metric sink có bounded buffer/drop counter. Retention kỹ thuật đề xuất 30 ngày; history mặc định off và cần policy riêng trước khi bật.

### 2.16 `search_results`

Cột: `query_id uuid ! FK search_queries.id`; `rank integer ! CHECK >0`; `image_id uuid ! FK images.id`; `score double precision !` finite; `score_type text !`; `ranking_version text !`; `constraint_assessment jsonb ! default {}`. PK `(query_id,rank)`, UQ `(query_id,image_id)`; index `(image_id)`. Đây là dữ liệu history opt-in, không bắt buộc persist mọi search. Retention theo query; FK có thể CASCADE khi xóa query đã hết retention, riêng FK image vẫn RESTRICT/tombstone. Metadata shown không duplicate snapshot tự do; khi cần research snapshot dùng immutable evaluation artifacts.

### 2.17 `evaluation_datasets`

Cột: `id uuid ! PK`; `name text !`; `version text !`; `manifest_sha256 char(64) ! UQ`; `license_ref text !`; `corpus_snapshot_ref text !`; `annotation_guide_ref text !`; `label_policy jsonb !`; `frozen_at timestamptz ?`; `created_at timestamptz !`. UQ `(name,version)`. Frozen dataset không sửa in-place; tạo version mới. Giữ artifacts theo rights và thời gian nghiên cứu đã thỏa thuận; không hứa giữ dữ liệu bị yêu cầu xóa.

### 2.18 `evaluation_dataset_images`

Cột: `dataset_id uuid ! FK evaluation_datasets.id`; `image_id uuid ! FK images.id`; `role text !` CHECK corpus/reference; `split text !` CHECK dev/test; `content_sha256 char(64) !`; `metadata_snapshot jsonb !`. PK `(dataset_id,image_id,role)`; index `(dataset_id,split,role)`, `(image_id)`. App đảm bảo checksum/role đúng và leakage grouping trên near-duplicates. Retention theo frozen dataset; delete nguồn khiến run cần đánh dấu not_reproducible nếu không có bản snapshot hợp pháp, không tự bỏ qua.

### 2.19 `evaluation_queries`

Cột: `id uuid ! PK`; `dataset_id uuid ! FK evaluation_datasets.id`; `external_id text !`; `group_code text !` CHECK G1/G2/G3/G4/G5; `split text !` CHECK dev/test; `locale text !`; `query_text text ?`; `reference_image_id uuid ? FK images.id`; `constraints jsonb ! default {}`; `eligible_filter jsonb ! default {}`; `expected_relations jsonb ! default []`; `annotation_status text !` CHECK draft/adjudicated; `query_sha256 char(64) !`. UQ `(dataset_id,external_id)` và `(id,dataset_id)` để composite FK. Index `(dataset_id,split,group_code)`. Group-specific validation: G3 có reference, G4 cả text/reference, G5 relation evidence. App xác nhận reference thuộc cùng dataset/role; không coi text hash là đủ bảo vệ privacy. Retention theo dataset.

### 2.20 `evaluation_relevance_labels`

Cột: `dataset_id uuid !`; `query_id uuid !`; `image_id uuid !`; `image_role text ! CHECK image_role='corpus'`; `grade smallint ! CHECK 0<=grade AND grade<=3`; `constraint_labels jsonb ! default {}`; `judge_ref text !`; `adjudicated boolean !`; `updated_at timestamptz !`. PK `(query_id,image_id)`; composite FK `(query_id,dataset_id)` → evaluation_queries `(id,dataset_id)`; FK `(dataset_id,image_id,image_role)` → evaluation_dataset_images `(dataset_id,image_id,role)`. Index `(dataset_id,query_id,grade)`, `(image_id)`. Một final judgment/query-image sau adjudication; annotator disagreements nằm annotation artifact, không ghi đè không có version. Absence row = unjudged, không phải grade 0. Retention bất biến sau freeze, theo dataset rights.

### 2.21 `benchmark_runs`

Cột: `id uuid ! PK`; `dataset_id uuid ! FK evaluation_datasets.id`; `index_id uuid ! FK search_indexes.id`; `experiment text !` CHECK E1/E2/E3/E4; `config jsonb !`; `config_sha256 char(64) !`; `source_snapshot_sha256 char(64) !`; `environment jsonb !`; `seed bigint !`; `status text !` CHECK planned/running/succeeded/failed/invalidated; `started_at timestamptz ?`; `finished_at timestamptz ?`; `metrics jsonb ?`; `artifact_ref text ?`. Index `(dataset_id,experiment,started_at)`. Không UQ config: repeated runs được phép. environment chứa hardware/package/precision/load/cache; metrics không có khi planned. Retention đề xuất ≥ thời gian bảo vệ/đánh giá, exact duration do owner chốt; references dữ liệu bị xóa làm run invalidated.

### 2.22 `benchmark_query_results`

Cột: `run_id uuid ! FK benchmark_runs.id`; `query_id uuid ! FK evaluation_queries.id`; `sample_no integer ! CHECK >0`; `outcome text !`; `duration_ms double precision !`; `ranking jsonb !`; `metrics jsonb ?`; `tool_trace_ref text ?`; `error_code text ?`. PK `(run_id,query_id,sample_no)`; index `(query_id,run_id)`. App kiểm tra query thuộc run dataset và split phù hợp; ranking lưu IDs/scores/grade coverage/version, không fake run response. Retention theo run; raw high-volume load samples có thể ở artifact file riêng checksum để không phình PG.

### 2.23 `idempotency_records`

Cột: `principal_id text !`; `endpoint text !`; `key text !`; `request_sha256 char(64) !`; `status text !` CHECK processing/completed; `response_status integer ?`; `response_ref jsonb ?`; `created_at,expires_at timestamptz !`; `lease_expires_at timestamptz ?`. PK `(principal_id,endpoint,key)`; index `(expires_at)`. TTL khởi đầu 24 giờ, không xóa processing/live mutation mù quáng. Same key/body trả response identity cũ; body khác 409; in-flight trả 409 IDEMPOTENCY_IN_PROGRESS + Retry-After. response_ref chỉ IDs/safe status; không token/raw images. Payload fingerprint gồm canonical options và file SHA-256. Crash-resume gắn job/identity đã reserve, không tạo job khác; natural uniqueness vẫn bảo vệ khi TTL hết.

## 3. ER diagram và chính sách schema

ER nguồn đầy đủ: [database_erd.mmd](../diagrams/database_erd.mmd), chứa cả 24 tables (mục 2.8 có hai bảng). Relationships trong diagram bám FK trên, không dùng diagram thay thế nullability/CHECK/UQ. Các bảng optional history/entities/evaluation có thể migration theo phase; chúng không trở thành dependency LLM của core.

Logical design chưa được chạy qua PostgreSQL hoặc Alembic. Prompt 03 pin version và migration test; Prompt 04 kiểm tra uniqueness/leases. Dùng application validation cho cross-table invariants không biểu đạt được bằng CHECK; bắt buộc transaction/row locking cho publish/activate. Publish-ready lock image và item theo cùng thứ tự, kiểm tra claim token/lease còn hiệu lực, image không deleting/deleted, digest/metadata_revision/manifest vẫn khớp rồi mới commit. Worker không được chuyển deleting/deleted về available. Delete transaction dùng cùng image lock để serialize với publish. GIN/partitioning chỉ thêm theo query plan thực tế.

## 4. Qdrant collection và payload

Collection immutable naming: `img_<index_uuid_hex>`; PG registry lưu full name. Một collection có một dense vector config `size=embedding_models.dimension`, metric Cosine. Không hardcode dimension khi checkpoint chưa chọn. Qdrant hỗ trợ UUID point IDs; `point.id = images.id` theo [tài liệu points](https://qdrant.tech/documentation/concepts/points/). Model khác dimension hoặc cùng dimension khác manifest vẫn phải collection riêng. Application l2-normalize và finite-check; metric cấu hình được assert lúc startup.

| Payload field | Kiểu / mục đích |
| --- | --- |
| image_id | UUID dạng keyword, bằng point ID |
| index_id, manifest_sha256, source_sha256 | keyword compatibility/digest |
| metadata_revision | integer, so với PG khi hydrate |
| image_status | keyword projection, không nguồn truth |
| width, height | integer range filter |
| media_type, source_dataset, city | keyword, nullable field được bỏ khỏi payload |
| tags | keyword array normalized |
| captured_at | RFC3339 datetime payload khi có; client mapping version được test |

Payload indexes cho fields thực sự filter, khởi đầu image_status/source_dataset/media_type/city/tags và width/height/captured_at nếu workload dùng. Không copy raw EXIF, caption dài hoặc auth secrets. HNSW `m`, `ef_construct`, query `hnsw_ef`, on-disk và exact-search threshold được lưu config, pin service defaults trong run; chưa chọn optimum/hardware mode. C ban đầu 100, query override có cap; E1 so exact neighbor trên sample phù hợp. [Qdrant collections](https://qdrant.tech/documentation/manage-data/collections/) mô tả dimension/metric; baseline policy index isolation là quyết định của dự án.

Migration: create collection → build/fill → verify applied upserts/count/ID/digest + smoke quality → catch-up mutation journal/PG updated_at watermark không mất deletion → ready → preload matching encoder → PG active-pointer swap → drain → retire. Không có alias làm nguồn truth thứ hai. Nếu rollback, preload lại model đúng index cũ rồi swap, không chỉ đổi tên collection.

## 5. MinIO structure, access và deletion

Bucket private `image-search` (tên cấu hình, không credentials). Object keys do server sinh:

```text
staging/<item_uuid>/source.<validated_extension>
images/original/<image_uuid>/<sha256>.<validated_extension>
images/thumbnails/<image_uuid>/<transform_version>.webp
evaluation/<dataset_uuid>/<artifact_checksum>.json
```

Content-Type lấy từ decoded format allowlist, không tin extension client; upload original giữ bytes đã validate, EXIF không được phát qua metadata API và thumbnail strip EXIF. Original access chỉ theo quyền; nếu cần loại EXIF ngay cả file gốc phải có policy derived sanitized-original riêng, không gọi nó byte-identical raw hash. Chưa nhận ảnh người dùng thật trước khi policy quyền/privacy được xác nhận.

URL trả cho browser là `/api/v1/images/{id}/content?variant=thumbnail|original`, đi qua auth proxy; không đưa bucket/key/presigned URL vào response hoặc log. GET proxy validate ID/status, authorized scopes, stream bounded bytes; thumbnail vắng trả original nếu policy cho phép và Content-Type đúng. Query-upload temp không vào bucket corpus. Duplicate bytes dùng cùng original UUID, không upload một copy final mới; metadata request duplicate không được tự ghi đè bản đã có.

Deletion nhận qua admin indexing job kind=delete: transaction tombstone image `deleting`, tăng metadata_revision, fence/cancel pending writers → chặn search/content ngay → drain/terminate các writer liên quan → xóa points ở **mọi** active/building/retired collections → xóa originals/thumbnails/staging được tham chiếu → xác minh absence → status deleted và receipt deleted_at → purge sensitive metadata/hash theo policy. Mất service thì retry, tombstone vẫn chặn đọc; không báo cleanup xong trước verification. Không dùng eventual lifecycle bucket rule thay thế application deletion, và backup retention phải công bố riêng.

## 6. State machine và failure matrix

Item transitions: awaiting_input → queued → processing → succeeded; processing → retry_wait → processing hoặc failed; expired lease → retry_wait sau revoke claim; permanent error → failed. Job running tổng hợp succeeded nếu mọi item succeeded, partial_failed nếu có cả success/failure, failed nếu toàn bộ failure. `duplicate` là outcome trong response/result, không phải image lifecycle độc lập. Image_embeddings pending → processing → ready/failed; ready không bị hạ toàn image khi một reindex mới lỗi.

| Lỗi/điểm crash | Hành vi phục hồi |
| --- | --- |
| Reserve identity xong, staging chưa có | awaiting_input không claim; watchdog HEAD staging, tiếp tục nếu đầy đủ hoặc mark failed sau acceptance grace; client retry idempotency |
| Staging có, queued commit lỗi | Giữ deterministic source ref; reconcile complete queue hoặc dọn orphan không có live ownership |
| Original có, PG receipt chưa có | HEAD/check digest rồi insert receipt; put immutable không tạo asset ID mới |
| Qdrant applied, PG ready commit lỗi | Point không eligible vì embedding chưa ready; retry verify và CAS publish |
| PG ready nhưng object/vector mất về sau | Content/vector error và reconciliation hạ readiness đúng record, repair; không invent matches |
| Lease cũ còn external write | Claim CAS chặn publish; payload revision/PG recheck loại stale; cleanup/delete cần writer quiescence và sweep lại |
| Delete nửa chừng | Tombstone tiếp tục chặn đọc; replay delete idempotent, xóa đủ mọi index/object rồi mới finalized |
| Activate model/index lỗi | Pointer cũ giữ nguyên hoặc trả INDEX_SWITCHING; không dùng encoder/index khác space |

Reconciliation scheduled khởi đầu mỗi 15 phút, cộng repair theo event; full corpus scan chia page và giới hạn I/O. Grace orphan khởi đầu 24 giờ nhưng không xóa object/index còn job/run/reference hoặc writer sống. Hai pass sau quiescence và reference recheck trước destructive cleanup. Đây là đề xuất cấu hình, không phải RPO/SLA. Dataset snapshot/reindex không giữ metadata sửa/xóa vô hạn: watermark/catch-up và mutation fencing được kiểm tra ở Prompt 04/11.

## 7. Handoff sang API

Schema cung cấp image/job/query IDs, metadata allowlist, claims, index/model versions, error/status và benchmark manifests cần cho contracts. Job status có cursor theo `(created_at,id)` trong items; API không nhận bucket key/server path. Các object/evaluation refs là server-internal. Retention lịch sử và experiments cần owner chốt trước nonfixture data; schema giữ nullability/opt-in để không thu dữ liệu nhạy cảm mặc định.

## 8. Phạm vi migration Prompt 03

Revision `0001_foundation` hiện tạo sáu bảng: images, image_metadata, embedding_models, indexing_jobs, search_indexes và dataset_sources. Bốn bảng đầu là scope ưu tiên; hai bảng cuối cần để giữ foreign keys đã thiết kế. Không tạo toàn bộ24 bảng sớm, không seed model/image, không gọi SDK tạo vector collection. Model dimension bắt buộc nhập thật khi có model được chọn, không default placeholder.

ORM và migration dùng CHAR(64) cho hashes, CHAR(2) cho country_code, PostgreSQL JSONB/UUID/timestamptz, constraints/indexes có tên; transactions và migration rollback đã có. Integration test tạo database ngẫu nhiên, upgrade, compare_metadata với ORM rồi downgrade/drop; không downgrade DB ứng dụng. `updated_at` tự cập nhật bởi ORM, chưa có DB trigger. Schema24 bảng bên trên vẫn là target xuyên các phase;18 bảng còn lại bổ sung khi implementation cần, chủ yếu Prompt04 và evaluation/entities sau đó.

Real PostgreSQL verification, migration upgrade/compare/downgrade và dependency connectivity đã qua cả native lẫn Docker. Năm containers khởi động healthy; PG/MinIO markers và Qdrant volume file còn nguyên sau force-recreate, sau đó được dọn đúng namespace lượt test. Không tạo vector collection hoặc dữ liệu semantic. Xem [PHASE03_REPORT](../archive/PHASE03_REPORT.md).

## 9. Migration và storage implementation Prompt 04

Revision `928b88dc3f68_indexing_pipeline` bổ sung image_tags, image_objects, image_embeddings, indexing_job_items, job_item_attempts, idempotency_records và active_search_index, tổng13 bảng ORM. Giữ nguyên revision0001 và dữ liệu có sẵn. Upgrade/ORM compare/downgrade chỉ kiểm tra rollback trên disposable DB. Active pointer chưa tự set; online activation thuộc Prompt05.

Acceptance upload dùng final original key xác định thay vì staging copy riêng: PG awaiting_input reserve trước PUT → GET/hash verify → receipt và queued cùng transaction. Crash có thể phục hồi từ key UUID/hash, không tạo identity khác. Bản gốc chưa durable không được trả202. SHA uniqueness, live image/index partial unique, SKIP LOCKED, claim nonce/lease và publication source revision checks đã có. Metadata duplicate không overwrite. File upload gốc giữ nguyên bytes; filename chỉ ở CLI report, không là storage path hoặc identity.

Model/collection manifest được đăng ký từ loaded CLIP projection dimension thật. Qdrant wait applied, ID/vector/payload retrieval và exact query kiểm tra trước PG ready. Reindex không thay collection cũ. Reconcile/repair là CLI có chủ đích; orphan scans report-only, chưa scheduled garbage collection/deletion. Chi tiết trạng thái hiện hành tại [VECTOR_INDEX_DESIGN](../features/VECTOR_INDEX_DESIGN.md) và [INDEXING_TEST_REPORT](../archive/INDEXING_TEST_REPORT.md).

## 10. Query/activation Prompt05

Không thêm hoặc âm thầm sửa schema/migration. Dùng active_search_index đã tạo ở Prompt04; CLI lock/validate ready/model trước create/swap generation. Search batch join image/object/embedding receipts, filter lại source hash/metadata revision/status và payload compatibility. Query images và text không persist vào PG/MinIO; full-response telemetry nằm bounded memory rồi benchmark xuất artifact không có raw user inputs. Dữ liệu/index collections có sẵn giữ nguyên.

## 11. Prompt06 — không thay đổi schema/index

Advanced retrieval reuse immutable model/search index/active pointer và image metadata/embedding/object receipts Prompt04–05. Không migration mới, không thêm captions/tags/license hoặc object labels suy đoán. Multi-query candidates/fusion/reranking/query analysis là dữ liệu request-scoped; không ghi search history/query image hoặc evaluation labels vào các store. Query telemetry bounded trong API memory, artifacts nghiên cứu ghi vào evaluation/results bằng CLI. Actual tri-state metadata evidence và missing-data policy tại [MULTI_INTENT_SEARCH](../features/MULTI_INTENT_SEARCH.md).
