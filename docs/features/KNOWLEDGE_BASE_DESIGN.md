# Kho tri thức quan hệ

Prompt 02 đã thiết kế ba bảng nhưng runtime trước Prompt 09 chưa tạo chúng. Migration cộng thêm `20261106_agent_knowledge` (parent `928b88dc3f68`) hiện thực ba bảng, không sửa/xóa dữ liệu ảnh hoặc active index. Tổng schema runtime sau migration: 16 bảng; thiết kế đầy đủ các phase sau vẫn là mục tiêu.

## Schema runtime

| Table | Identity và dữ liệu | Ràng buộc/index |
| --- | --- | --- |
| entities | UUID, canonical_name, normalized name_key, entity_type, locale, aliases JSONB, external_key nullable, provenance JSONB, created_at | PK, unique(canonical_name,entity_type,locale), external_key unique, name_key index, aliases GIN, type allowlist |
| entity_relationships | UUID, subject_id/object_id, predicate, source_ref, evidence JSONB, verified_at nullable, created_at | FKs entities; unique(subject,predicate,object,source); không self-edge; subject/predicate và object/predicate indexes |
| image_entities | image_id, entity_id, relation, source_ref, verified=false | Composite PK(image,entity,relation), FKs images/entities, relation allowlist |

Entity types: city, landmark, country, location, person, object, organization, category, other. Predicates: located_in, contains, part_of, has_landmark, depicts, related_to, associated_with. Image-link relations: depicts, located_in, associated_with. Alias/canonical lookup normalize Unicode NFC + casefold; không fuzzy inference và không xác nhận alias do LLM đề xuất.

`verified_at` và `verified` là attestation của người nhập/nguồn được tin cậy, không là nhãn do hệ thống tự chứng minh. Source/provenance phải được giữ để audit. Runtime chỉ traverse quan hệ có verified_at và nguồn; chỉ dùng links verified. Aggregator đọc lại facts/links/ảnh trước response. Canonical entity không tự chứng minh một quan hệ. Similarity cao cũng không chứng minh `located_in`.

## Đồng bộ với ảnh và vectors

PostgreSQL giữ facts và image associations; Qdrant giữ embedding và payload retrieval; MinIO giữ originals. Không duplicate knowledge graph trong vector payload. Tool resolve target IDs → PG verified links → Qdrant HasIdCondition → PG predicate recheck → EvidenceRetriever kiểm tra ảnh/vector/object. Link tới ảnh chưa indexed/đã unavailable không thành final result. Import không thay active pointer hoặc rebuild embeddings.

## Import có nguồn

CLI quản trị `app.cli.knowledge --input <local-json>` validate mặc định, `--apply` ghi một transaction. JSON gồm `entities`, `relationships`, `image_entities` theo Pydantic models ở `repositories/knowledge_import.py`; tối đa 1 MiB và 1.000 records mỗi nhóm. Replay cùng identity/nội dung là idempotent; identity có nội dung khác bị reject để tránh sửa ngầm provenance. Thay đổi dữ liệu cần bản import/review riêng; CLI này chưa có revision/update/delete workflow.

```bash
# File đã được người quản trị review; đây là đường dẫn ví dụ.
docker compose cp evaluation/agent/verified_knowledge.json backend:/tmp/verified_knowledge.json
docker compose exec backend python -m app.cli.knowledge --input /tmp/verified_knowledge.json
docker compose exec backend python -m app.cli.knowledge --input /tmp/verified_knowledge.json --apply
```

`verified_knowledge.json` là đường dẫn minh họa. Gói thực hiện có tại `evaluation/agent/datasets/nps_v1_knowledge.json`; helper `app.cli.prepare_landmark_knowledge` tạo gói từ source catalog và image receipts đã verify. Không chạy với fictional fixture trong DB ứng dụng. Fixture import chỉ cho `APP_ENV=test`, `AGENT_ALLOW_FIXTURE_KNOWLEDGE=true` và database prefix `agent_test_`. Runtime thông thường loại fixture provenance/source. Fixture command và cleanup nằm trong `scripts/verification/verify_agent_fixtures.py`.

## Dữ liệu hiện tại và phần chưa xác minh

Serving corpus hiện513 ảnh indexed và503 captions. Sau lựa chọn nguồn công khai của người dùng, đã nhập4 entities,3 located_in relationships và3 verified image links từ NPS. Dataset nhỏ này kiểm chứng workflow thật; chưa có human relevance labels để đánh giá semantic quality. [PUBLIC_LANDMARK_DATASET](../research/PUBLIC_LANDMARK_DATASET.md) ghi catalog, giấy phép, receipts và cách tái lập. Không có Agent tool crawl/import; connector tải NPS là CLI quản trị allowlist, tối đa20 ảnh và không follow redirect. Index cũ510 ảnh giữ nguyên, không cần thay kiến trúc repository để thêm dữ liệu.

Import guard và normal repository cùng loại fixture flags/source prefix; aggregator đối chiếu lại provenance/timestamp của relations và verified image links trước response. `fixture:` không được dùng làm source của knowledge thật.
