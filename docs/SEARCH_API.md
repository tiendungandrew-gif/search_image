# Search API — Prompt 05

Tài liệu baseline Prompt05. Phần text/image core vẫn áp dụng; advanced fusion/multi-intent/reranking đã được triển khai ở Prompt06 theo [ADVANCED_SEARCH_API](ADVANCED_SEARCH_API.md), [MULTIMODAL_SEARCH](MULTIMODAL_SEARCH.md) và [báo cáo](ADVANCED_SEARCH_TEST_REPORT.md). Các đoạn “chưa triển khai Prompt06” bên dưới mô tả thời điểm bàn giao Prompt05.

Base `/api/v1`, Bearer API_TOKEN read hoặc operator write token. Canonical schemas giữ API_SPECIFICATION; các alias Prompt05 dưới là additions, không đổi field types v1. Search không yêu cầu Idempotency-Key và không tạo ingestion jobs.

## 1. Text search

`POST /api/v1/search`, application/json:

```json
{"text":"a cup of coffee","mode":"text","top_k":10,"candidate_count":50,"filters":{}}
```

Alias tương thích ví dụ Prompt05: `{query,search_mode:"semantic"}` được normalize thành `{text,mode:"text"}`; không gửi đồng thời text và query hoặc contradictory modes. Whitespace/NFC normalize, không lowercase semantic text. Empty/control-character/too-long input →422; vượt77 token positions CLIP →422 TEXT_TOKEN_LIMIT, không truncate. Top-K1…50 mặc định server, schema hard cap100 khi operator cấu hình; candidates1…1.000 và≥K. Không nhận arbitrary model/collection/path/URL.

## 2. Image search

Cả core `POST /search` và compatibility `POST /search/multimodal` nhận image-only multipart:

```text
image: <JPEG/PNG/WebP binary>
options: {"mode":"image","top_k":10,"exclude_self":false}
```

Legacy multipart thay options bằng `top_k` và `search_mode=image_similarity` được hỗ trợ. Không trộn options với legacy fields; chỉ một file và known fields. `/search/multimodal` image-only là compatibility addition theo Prompt05; text+image fusion vẫn FEATURE_DISABLED409. Core JSON existing-image input:

```json
{"image_id":"00000000-0000-4000-8000-000000000040","mode":"image","top_k":5,"exclude_self":true}
```

UUID trên chỉ minh họa shape, phải thay bằng actual image_id. Existing-image query lấy verified stored vector. exclude_self defaulttrue, áp dụng image_id hoặc SHA match của query upload; UI gửi false để hiển thị exact self match. Query uploads không tự index/persist; multipart spool được đóng khi parse xong. Raw filenames/MIME không thay content validation. File20MiB/body21MiB, one frame,25M pixels/side10.000, decoder process bounds dùng lại Prompt04.

## 3. Filters và advanced fields

Filters: source_dataset, city, media_types, tags_any, tags_all, min/max_width, min/max_height, captured_from/to (timezone-aware). Ranges phải có thứ tự; tags NFC/lowercase/trim,≤20 entries, mỗi tag≤64. Unknown fields bị reject. Basic filters có thể tắt bằng config; khi tắt nonempty filter →409. Constraints/nonempty AST, require_verified, rerank.enabled, explain.enabled, agent/multi_intent/multimodal modes chưa hỗ trợ →409 FEATURE_DISABLED. Không có combined fusion, semantic constraints hoặc LLM fallback.

## 4. Response

Response schema SearchResponse trong Swagger:

- query_id/request_id, requested_mode, canonical search_mode=text|image, service_class=fast.
- index_id/model_id/manifest_sha256 pin runtime/index.
- results: image_id,1-based rank, actual finite score, score_type=cosine, ranking_version=cosine-v1, image_url/thumbnail_url authenticated proxy, metadata và constraint_assessments=[]. Metadata caption/title/tags/source/city/license chỉ khi có, không fake.
- total_results bằng số results; kết quả≤K, IDs unique.
- effective_settings ghi K/candidates/channel1/total cap1.000/ranking/truncation, không optional agent/fusion được thực thi.
- latency.processing_ms và latency_ms là cùng processing boundary tới DTO trước response serialization; latency.server_response_ms=null vì final send chưa xảy ra. stages có actual durations. Full ASGI samples ở bounded operator endpoint dưới.
- warnings cho missing objects/candidate cap; explanation/agent=null.

Image URLs relative `/api/v1/images/{uuid}/content?variant=original|thumbnail`, không có token/credentials/MinIO hostname. Browser fetch Authorization rồi render blob; không gắn Bearer token vào URL. Cosine score không là probability. `200 results=[]` nghĩa không có eligible candidates; lỗi hạ tầng không được giấu thành empty set.

## 5. Health, errors và diagnostics

`GET /health?check=search` private trả200 khi model/active index/required stores ready; nếu chưa sẵn sàng trả503 HealthSummary. Public `/health` không query dependencies, flags là cached loaded capabilities; text_search/image_search có thể true, advanced flags false. `/health/ready` vẫn là infrastructure probes riêng, không chứng minh search-ready.

Errors giữ envelope chuẩn:401 UNAUTHENTICATED;409 FEATURE_DISABLED/MODEL_INDEX_MISMATCH;413 PAYLOAD_TOO_LARGE;415 UNSUPPORTED_MEDIA;422 INVALID_INPUT/TEXT_TOKEN_LIMIT/CORRUPT_IMAGE;500 INFERENCE_FAILED;503 NOT_READY/COLLECTION_UNAVAILABLE/INDEX_SWITCHING/DEPENDENCY_UNAVAILABLE/INFERENCE_BUSY;504 DEADLINE_EXCEEDED/VECTOR_TIMEOUT. Request timeout2s mặc định full ASGI gồm body/decode; timeout không đảm bảo thread/GPU đã cancel nên slot được giữ đến compute completion.

`GET /system/search-metrics?limit=1000` private read diagnostics addition, limit1…10.000, ring capacity10.000/process. Chỉ trả request/query/model/index IDs, modality, stages, status, complete flag, full server_response_ms và serialization_send_ms. Không text/images/headers/credentials; không là durable metrics backend. Benchmark join X-Request-ID để phân biệt server full-response với client latency.
