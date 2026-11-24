# Đặc tả REST API v1

Cập nhật tài khoản/UI 08/11/2026: xem [thiết kế quyền](../architecture/ACCESS_CONTROL.md) và [hướng dẫn đăng nhập](../operations/ACCOUNTS.md). Các hướng dẫn dùng data token trước đây chỉ áp dụng khi bật legacy; mặc định mới dùng session tài khoản.
## Ingress triển khai Phase12

Contracts FastAPI giữ nguyên. Nginx production phục vụ `/api/v1` cùng origin với SPA, chuyển Authorization/request ID và không buffer SSE. Ingress chặn mutation `/images` và `/index/`; import/activation dùng CLI vận hành trong network riêng. Các health/runtime/workspace vẫn phân biệt infrastructure, empty data và model/index readiness. [FINAL_SYSTEM_ARCHITECTURE](FINAL_SYSTEM_ARCHITECTURE.md), [DEPLOYMENT_GUIDE](../operations/DEPLOYMENT_GUIDE.md) và [SECURITY_DEPLOYMENT](../operations/SECURITY_DEPLOYMENT.md) mô tả ports/TLS/auth; không suy ra public access từ các endpoint internal.

## Cập nhật validation và OpenAPI Phase11

`GET /system/workspace` và `/system/evaluation` có response DTO/OpenAPI (`WorkspaceSnapshot`, `EvaluationSummary`), JSON shape không đổi. Metrics không finite hoặc count âm trong artifacts không được công bố. Content-Length malformed/quá giới hạn trả413 theo envelope; filter/ingestion metadata chứa control characters không hợp lệ trả422 trước database. Caption multiline hợp lệ và idempotency hash được giữ nguyên. Xem [BUG_FIX_REPORT](../archive/BUG_FIX_REPORT.md), [nghiệm thu](../archive/PHASE11_TEST_REPORT.md). Không đổi public search request/ranking contracts.

## Hoàn thiện Phase 09 — 06/11/2026

Đã bổ sung bộ địa danh NPS có nguồn:3 ảnh thật,4 entities,3 quan hệ và3 liên kết ảnh. Index phục vụ hiện513 ảnh, generation3; index510 ảnh cũ giữ nguyên. Workflow Anh/Việt/alias, Gemini planner và RAG thật đã được kiểm tra. Planner có trace từng attempt; prompt tools và RAG context đã rút gọn, citation provenance vẫn giữ đầy đủ trên server. Bộ kiểm tra mới đạt200 backend,21 frontend unit và24 browser full tests cùng6 ca browser nhánh cuối. Chất lượng do người đánh giá vẫn chờ; số đo latency và trạng thái target3s xem [báo cáo Phase 09](../archive/PHASE09_TEST_REPORT.md), dữ liệu/nguồn tại [PUBLIC_LANDMARK_DATASET](../research/PUBLIC_LANDMARK_DATASET.md).

## Hợp đồng Agent hiện hành Phase 09

`POST /search/agent` JSON và `POST /search/agent/stream` SSE đã được triển khai, cùng GET status/samples có read auth. Request nhận query hoặc text, alias search_mode/max_hops, budgets giới hạn và explanation tùy chọn; AgentResponse nằm ở root với status/query_success riêng. [AGENT_API](../features/AGENT_API.md) và OpenAPI runtime mô tả schema đầy đủ. Các đoạn reserved/không hỗ trợ SSE/AgentSummary ở thiết kế Phase 02 bên dưới được thay thế cho riêng Agent bởi hợp đồng runtime này. Core Search API không đổi entrypoint hoặc tự bật Agent.

Phiên bản 1.1.0 · 2026-11-03 · Contract thiết kế Phase 02; trạng thái routes đã triển khai xem mục12–14. Đã đối chiếu [PRD](PRD.md), [DATABASE_DESIGN](DATABASE_DESIGN.md) và [SAD](SAD.md). Các UUID, scores và timing trong ví dụ chỉ minh họa schema, không là dữ liệu tìm kiếm hay kết quả benchmark.

## 1. Quy ước chung

Base path `/api/v1`; JSON UTF-8, timestamp RFC3339 UTC, UUID chuẩn, unknown fields bị reject. `Authorization: Bearer <opaque-token>` ánh xạ server-side principal/scopes; browser không nhận secret của data services. CORS chỉ origins cấu hình; không auth cookie trong MVP. `X-Request-ID` server sinh/validate UUID và echo response. Body JSON tối đa 64 KiB; multipart tối đa 21 MiB gồm file tối đa 20 MiB và options tối đa 64 KiB. Giới hạn là dev defaults, có thể đổi cùng validation/docs; chi tiết PERFORMANCE_DESIGN.

Mọi API trừ health live yêu cầu auth như bảng endpoint. Không có search cursor pagination: Top-K cố định cho một request. Job items có opaque cursor. Mutation `/images`, `/index/jobs` **bắt buộc** `Idempotency-Key` 1…128 ASCII printable; scope theo principal/endpoint, TTL 24h; cùng key/body trả lại identity/status cũ, khác body 409; đang xử lý 409 IDEMPOTENCY_IN_PROGRESS + Retry-After. Search không cần key và không tự persist upload thành corpus.

### Error envelope áp dụng cho mọi endpoint

```json
{"error":{"code":"INVALID_INPUT","message":"Tham số không hợp lệ","request_id":"00000000-0000-4000-8000-000000000001","retryable":false,"details":[{"field":"top_k","reason":"out_of_range"}]}}
```

`details` chỉ safe field/reason, không stack/secret/internal paths. Tất cả endpoint dùng schema này cho lỗi HTTP trước khi gửi body. Connection loss sau khi content streaming đã bắt đầu không thể đổi status thành JSON; log incomplete và client báo download failure.

| HTTP | Code tiêu biểu / nghĩa |
| --- | --- |
| 400 | MALFORMED_JSON/MALFORMED_MULTIPART/IDEMPOTENCY_KEY_REQUIRED |
| 401 / 403 | UNAUTHENTICATED / FORBIDDEN; không retry tự động bằng cùng credentials |
| 404 | IMAGE_NOT_FOUND/JOB_NOT_FOUND; gồm image deleted không được đọc |
| 406 | NOT_ACCEPTABLE: không hỗ trợ SSE/representation được yêu cầu |
| 409 | FEATURE_DISABLED, MODEL_INDEX_MISMATCH, VERIFIER_UNAVAILABLE, IDEMPOTENCY_CONFLICT, IDEMPOTENCY_IN_PROGRESS, INDEX_JOB_CONFLICT, IMAGE_DELETED |
| 413 / 415 / 422 | PAYLOAD_TOO_LARGE / UNSUPPORTED_MEDIA / INVALID_INPUT hoặc CORRUPT_IMAGE |
| 429 | RATE_LIMITED; Retry-After giây nguyên |
| 500 | INTERNAL_ERROR hoặc INFERENCE_FAILED không có chi tiết nhạy cảm |
| 503 | DEPENDENCY_UNAVAILABLE, NOT_READY, INFERENCE_BUSY, INDEX_SWITCHING; retryable theo ngữ cảnh, Retry-After nếu xác định được |
| 504 | DEADLINE_EXCEEDED; không có guarantee external compute đã bị cancel, capacity được fence |

## 2. Schema dùng chung

### SearchOptions

| Field | Kiểu / default / validation |
| --- | --- |
| mode | enum auto/text/image/multi_intent; default auto trên core; multimodal/agent chỉ đúng endpoint riêng |
| text | string nullable, trim/NFC, 1…2.000 chars nếu có; không tự lowercase semantic text; vượt tokenizer model → 422 TEXT_TOKEN_LIMIT, không truncate âm thầm |
| image_id | UUID nullable; ảnh corpus được phép đọc và original available; không nhận file path, URL hoặc base64 |
| top_k | integer default 10, 1…100 |
| candidate_count | integer default max(100,top_k), top_k…1.000 mỗi channel, bị giảm để tổng candidate entries mọi channels ≤1.000; response ghi effective settings |
| filters | FilterSpec default {}; P1 field nonempty khi feature tắt →409 |
| constraints | ConstraintSpec nullable; tối đa 8 leaves/depth 2, strict grammar; P1 |
| require_verified | boolean default false; chỉ có nghĩa với semantic constraints; verifier unavailable khi strict →409 |
| rerank | `{enabled:boolean=false,on_failure:error|skip=error}`; true chỉ khi configured; skip phải warning nếu reranker lỗi |
| explain | `{enabled:boolean=false,on_failure:error|omit=error}`; P2 optional, thêm generation sau retrieval; disabled feature →409; omit giữ ảnh và warning khi provider lỗi |

File multipart là field `image`, options field là JSON text được parse đúng một lần theo SearchOptions. Multipart giới hạn một file; file và image_id là mutually exclusive. JSON text-only và JSON existing-image-reference tách khỏi multipart. Text+image không được gửi lén qua core endpoint; dùng multimodal route. Unknown/contradictory mode-input combination →422. `auto` không bao giờ chọn agent. Nếu multi-intent feature chưa bật, auto xử lý query như direct text, báo `constraints_not_verified` khi relevant; không claim decomposition.

FilterSpec: `source_dataset?: string[1..128]`, `media_types?: array` allowlist JPEG/PNG/WebP; `tags_any?: string[]`, `tags_all?: string[]` tối đa 20 mỗi array; `city?: string[1..128]`; `min_width?,max_width?,min_height?,max_height?: positive int`; `captured_from?,captured_to?: datetime`. Các field AND; tags_any là OR, tags_all là AND; min>max hoặc time range đảo →422. Missing field không thỏa positive predicate. Không nhận raw SQL/Qdrant filter. normalized tags theo DATABASE_DESIGN, PG recheck toàn bộ predicate.

ConstraintSpec: group `{op:and|or,clauses:[group|leaf]}`; leaf semantic `{id,text,kind:semantic,required:boolean}` hoặc metadata `{id,kind:metadata,filter:FilterSpec,required:boolean}`. ID unique ≤64 chars. Semantic verification tri-state và strict policy theo SYSTEM_ARCHITECTURE. Nếu khai báo AST và text, AST là explicit conditions, text vẫn retrieval context; không tự bỏ AST khi router mơ hồ.

### SearchResponse

| Field | Kiểu / ý nghĩa |
| --- | --- |
| query_id, request_id | UUID; query_id luôn có ngay cả khi history không persist |
| requested_mode, search_mode | requested và executed mode; search_mode text/image/multi_intent/multimodal/agent |
| service_class | fast hoặc augmented; explain/agent là augmented, đo riêng full response latency |
| index_id, model_id, manifest_sha256 | pinned registry/version; không cho client ép model tùy ý trong production API |
| results | SearchResult[], 0…K, unique UUID, rank bắt đầu 1 |
| effective_settings | K/C/channel count/total candidate cap, fusion/ranking versions, constraints mode, truncation flag |
| latency | `{processing_ms:number>=0,server_response_ms:null}`; complete metric chỉ có sau final send và join qua request_id |
| explanation | null hoặc `{text,citations:[{image_id,evidence_id}],grounding_status:validated|insufficient_evidence}` |
| warnings | array `{code,message}`, không dữ liệu nhạy cảm |
| agent | null hoặc AgentSummary tại mục 5 |

SearchResult: `image_id:UUID`, `rank:positive int`, `image_url:string`, `thumbnail_url:string`, `score:finite number`, `score_type:cosine|rrf|reranker`, `ranking_version:string`, `metadata:{title:string|null,width:int,height:int,media_type:string,tags:string[],source_dataset:string|null,city:string|null,license:string|null}`, `constraint_assessments:[{clause_id,status:satisfied|violated|unknown,evidence_ref:string|null}]`. Scores không là calibrated relevance probabilities. Image URLs là relative authenticated content proxy, không bearer URLs; client fetch Authorization → blob URL.

### JobResponse

`job_id:UUID`, `kind`, `status:awaiting_input|queued|running|succeeded|partial_failed|failed`, `target_index_id:UUID|null`, `counts:{total,queued,processing,retry_wait,succeeded,failed}`, `created_at`, `updated_at`, `items:JobItem[]`, `next_cursor:string|null`.

JobItem: `{item_id,image_id:UUID|null,index_id:UUID|null,status,stage,attempt_count,last_error_code:string|null,next_attempt_at:datetime|null}`. Không lộ source_ref/bucket/server path/lease token. `total` gồm awaiting_input; khi có item awaiting_input counts có thêm `awaiting_input` field để tổng không sai. Counts là toàn job, items chỉ page.

## 3. `POST /api/v1/search` — text hoặc image-only

**Quyền:** `search:read`. **Content-Type:** application/json hoặc multipart/form-data. **Request:** SearchOptions; JSON phải có đúng text hoặc image_id; multipart phải có image file và không có text. Mode auto/text/image/multi_intent; multi_intent cần P1. Text-only không phải upload corpus.

**Response:** 200 SearchResponse, kể cả no-match. **Validation:** schema chung, compatible active index, content decode/frame/pixel limits. **Lỗi:** common error envelope; thường 400/401/403/409/413/415/422/429/500/503/504. Multipart image request được tính body parse/decode trong core response latency. Khi explain enabled, full request được phân loại augmented, không đưa vào fast-path percentile để che generation cost; vẫn lưu full timer.

Ví dụ JSON request:

```json
{"mode":"text","text":"a red motorcycle on a street","top_k":10,"rerank":{"enabled":false}}
```

Ví dụ response hợp lệ khi không có eligible matches (số timing chỉ minh họa contract):

```json
{"query_id":"00000000-0000-4000-8000-000000000010","request_id":"00000000-0000-4000-8000-000000000001","requested_mode":"text","search_mode":"text","service_class":"fast","index_id":"00000000-0000-4000-8000-000000000020","model_id":"00000000-0000-4000-8000-000000000030","manifest_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","results":[],"effective_settings":{"top_k":10,"candidate_count":100,"channels":1,"total_candidate_cap":1000,"ranking_version":"cosine-v1","fusion_version":null,"constraints_mode":"best_effort","truncated":false},"latency":{"processing_ms":12.0,"server_response_ms":null},"explanation":null,"warnings":[],"agent":null}
```

Ví dụ image-only multipart (ký hiệu phần body, boundary do HTTP client sinh):

```text
Content-Type: multipart/form-data; boundary=generated-by-client
options (text): {"mode":"image","top_k":10}
image (file): reference.jpg, Content-Type image/jpeg, <binary bytes>
```

Response dùng cùng SearchResponse với search_mode=image; không bắt buộc text. File hỏng →422 CORRUPT_IMAGE, unsupported format →415.

## 4. `POST /api/v1/search/multimodal` — kết hợp hai modality

**Quyền:** `search:read`, feature multimodal enabled. **Content-Type:** application/json khi tham chiếu existing image_id; multipart/form-data khi upload query image. **Request:** SearchOptions với `mode:multimodal`, text bắt buộc và đúng một image_id/file; thêm `fusion:{method:weighted_rrf,text_weight:number>0,image_weight:number>0}` default 0.5/0.5, weights được normalize; method khác chưa bật →422. **Response:** 200 SearchResponse, score_type=rrf hoặc reranker. **Lỗi:** common envelope, 409 FEATURE_DISABLED khi chưa có P1; các lỗi content/validation/auth/dependency như core.

Ví dụ request multipart:

```text
options (text): {"mode":"multimodal","text":"similar scene with a red motorcycle","top_k":10,"fusion":{"method":"weighted_rrf","text_weight":0.5,"image_weight":0.5}}
image (file): scene.png, Content-Type image/png, <binary bytes>
```

Ví dụ response đầy đủ theo SearchResponse (dữ liệu chỉ minh họa contract):

```json
{
  "query_id": "00000000-0000-4000-8000-000000000010",
  "request_id": "00000000-0000-4000-8000-000000000001",
  "requested_mode": "multimodal",
  "search_mode": "multimodal",
  "service_class": "fast",
  "index_id": "00000000-0000-4000-8000-000000000020",
  "model_id": "00000000-0000-4000-8000-000000000030",
  "manifest_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "results": [
    {
      "image_id": "00000000-0000-4000-8000-000000000040",
      "rank": 1,
      "image_url": "/api/v1/images/00000000-0000-4000-8000-000000000040/content?variant=original",
      "thumbnail_url": "/api/v1/images/00000000-0000-4000-8000-000000000040/content?variant=thumbnail",
      "score": 0.016,
      "score_type": "rrf",
      "ranking_version": "weighted-rrf-v1",
      "metadata": {
        "title": null,
        "width": 640,
        "height": 480,
        "media_type": "image/png",
        "tags": [],
        "source_dataset": null,
        "city": null,
        "license": null
      },
      "constraint_assessments": []
    }
  ],
  "effective_settings": {
    "top_k": 10,
    "candidate_count": 100,
    "channels": 2,
    "total_candidate_cap": 1000,
    "ranking_version": "weighted-rrf-v1",
    "fusion_version": "weighted-rrf-v1",
    "constraints_mode": "best_effort",
    "truncated": false
  },
  "latency": {
    "processing_ms": 12.0,
    "server_response_ms": null
  },
  "explanation": null,
  "warnings": [],
  "agent": null
}
```

Đây là ví dụ contract, không phải ảnh/mức chất lượng được tạo sẵn cho application. Response có search_mode=multimodal, fusion_version=weighted-rrf-v1 và effective channel depth theo caps.

## 5. `POST /api/v1/search/agent` — optional bounded multi-hop

**Quyền:** `search:read`, feature agent enabled. **Content-Type/Accept:** application/json. **Transport initial:** synchronous JSON; SSE/WebSocket chưa hỗ trợ, `Accept: text/event-stream` →406. Do không stream nên không có partial/token/final/error SSE events trong v1; nếu thêm sau phải version contract events và grounding trước phát nội dung. TTFirst/TTLast chỉ đo nội bộ nếu provider có token hooks, nếu không null; không thay bằng response latency.

**Request:** `{mode:agent,text:string,top_k:int=10,filters:FilterSpec={},allow_fallback:boolean=false,explain:{enabled:false,on_failure:error},budgets?:{max_hops:int<=3,max_tool_calls:int<=6,max_output_tokens:int<=512,deadline_ms:int<=5000}}`. Client chỉ giảm, không tăng server caps; min hop/calls/tokens/deadline >0. Không image input trong relational MVP; muốn query joint dùng endpoint multimodal. AgentSummary: `{resolution:resolved|unresolved|fallback,hops:int,tool_calls:int,trace:[{step_id,tool_name,duration_ms,outcome,evidence_ids}],unresolved_relations:string[],fallback_reason:string|null,timing:{ttfirst_ms:number|null,ttlast_ms:number|null,complete_response_ms:null}}`.

**Response:** 200 SearchResponse + AgentSummary; search_mode=agent khi chạy workflow, hoặc direct mode text khi fallback, requested_mode vẫn agent; service_class=augmented. Unknown relation →200 resolution=unresolved, results=[] và warning; dependency failure không có consent/time fallback →503/504. Không đánh dấu fallback là multi-hop thành công. **Lỗi:** common envelope; 409 FEATURE_DISABLED, 422 bad budgets, 406 SSE, 500/503/504 tool/provider failure. Mọi tool retry tính vào cap và cùng deadline.

Ví dụ request:

```json
{"mode":"agent","text":"Find landmarks in the city where Hoan Kiem Lake is located","top_k":10,"allow_fallback":false,"explain":{"enabled":false},"budgets":{"max_hops":3,"max_tool_calls":6,"max_output_tokens":512,"deadline_ms":5000}}
```

Ví dụ response đầy đủ cho dataset chưa có relation (chỉ minh họa contract):

```json
{
  "query_id": "00000000-0000-4000-8000-000000000010",
  "request_id": "00000000-0000-4000-8000-000000000001",
  "requested_mode": "agent",
  "search_mode": "agent",
  "service_class": "augmented",
  "index_id": "00000000-0000-4000-8000-000000000020",
  "model_id": "00000000-0000-4000-8000-000000000030",
  "manifest_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "results": [],
  "effective_settings": {
    "top_k": 10,
    "candidate_count": 100,
    "channels": 1,
    "total_candidate_cap": 1000,
    "ranking_version": "cosine-v1",
    "fusion_version": null,
    "constraints_mode": "best_effort",
    "truncated": false
  },
  "latency": {
    "processing_ms": 12.0,
    "server_response_ms": null
  },
  "explanation": null,
  "warnings": [
    {
      "code": "RELATION_UNRESOLVED",
      "message": "Chưa có evidence cho quan hệ được yêu cầu"
    }
  ],
  "agent": {
    "resolution": "unresolved",
    "hops": 0,
    "tool_calls": 1,
    "trace": [
      {
        "step_id": "s1",
        "tool_name": "entity_lookup",
        "duration_ms": 5.0,
        "outcome": "not_found",
        "evidence_ids": []
      }
    ],
    "unresolved_relations": [
      "location_of_query_entity"
    ],
    "fallback_reason": null,
    "timing": {
      "ttfirst_ms": null,
      "ttlast_ms": null,
      "complete_response_ms": null
    }
  }
}
```

## 6. `POST /api/v1/images` — nạp ảnh vào corpus

**Quyền:** `images:write`. **Content-Type:** multipart/form-data, `Idempotency-Key` bắt buộc. **Request:** `image` một file; `metadata` JSON text `{title?,description?,tags?:string[],source_dataset?,source_uri?,license?,rights_ref?}`; nonfixture yêu cầu provenance/rights_ref. title≤256, description≤4.000, tags≤20, mỗi tag≤64. Không cho client tự set lifecycle/hash/dimensions/verified. Metadata chỉ set khi identity mới; duplicate không ghi đè metadata cũ.

**Processing:** validate actual content/hash, reserve pending identity/job, durable stage, commit queued. **Response:** 202 `{image_id,duplicate:false,job_id,status:queued,status_url}`; existing ready identity →200 `{image_id,duplicate:true,job_id:null,status:available,status_url:null}`; live indexing có thể trả 202 existing job ref sau auth/ownership check. Target index lấy từ configured ingestion index; bootstrap chưa có target →503 NOT_READY. **Lỗi:** common envelope, 400 missing key, 409 duplicate tombstone/idempotency conflict, 413/415/422 content/rights, 503 staging/DB. Không trả 202 nếu bytes/job chưa durable.

Ví dụ request:

```text
Idempotency-Key: upload-opaque-key-001
metadata (text): {"title":"Dataset image","source_dataset":"approved-fixtures","license":"project-owned","rights_ref":"fixture-manifest-v1"}
image (file): sample.jpg, Content-Type image/jpeg, <binary bytes>
```

Ví dụ response:

```json
{"image_id":"00000000-0000-4000-8000-000000000040","duplicate":false,"job_id":"00000000-0000-4000-8000-000000000050","status":"queued","status_url":"/api/v1/index/jobs/00000000-0000-4000-8000-000000000050"}
```

## 7. `GET /api/v1/images/{id}` — metadata/detail

**Quyền:** `search:read`; admin có scope này để xem cả pending/failed, người chỉ search chỉ thấy available. **Request:** không body, Accept application/json, UUID path. **Response:** 200 `{image_id,status,sha256?:string,metadata:ResultMetadata,created_at,indexing:[{index_id,status}],image_url:string|null,thumbnail_url:string|null}`; sha256/indexing chỉ admin scope; pending không có content URL. **Lỗi:** error envelope, 401/403/404, 422 UUID, 503 DB; deleting/deleted luôn404 với readers.

Ví dụ request: `GET /api/v1/images/00000000-0000-4000-8000-000000000040` với Bearer read scope.

```json
{"image_id":"00000000-0000-4000-8000-000000000040","status":"available","metadata":{"title":null,"width":640,"height":480,"media_type":"image/jpeg","tags":[],"source_dataset":"approved-fixtures","city":null,"license":"project-owned"},"created_at":"2026-11-03T03:00:00Z","image_url":"/api/v1/images/00000000-0000-4000-8000-000000000040/content?variant=original","thumbnail_url":"/api/v1/images/00000000-0000-4000-8000-000000000040/content?variant=thumbnail"}
```

### Supporting endpoint `GET /api/v1/images/{id}/content`

Cần để triển khai private access đã chọn; không thay tám core endpoints. Auth `search:read`, không body, `variant=original|thumbnail`, default thumbnail. 200 binary content với validated MIME, byte limits, private/no-store/nosniff; chưa hỗ trợ Range (trả full 200), không inline SVG. Missing thumbnail fallback authorized original, MIME theo bytes thật. 401/403/404/422/503/504 dùng error envelope nếu headers chưa gửi. Request ví dụ URL trong detail ở trên; response ví dụ `Content-Type: image/jpeg` + `<binary bytes>`, không JSON. Content download có full server timer riêng, không trộn vào search latency.

## 8. `POST /api/v1/index/jobs` — batch/reindex/delete/retry

**Quyền:** `index:manage`, Idempotency-Key bắt buộc. **Content-Type:** application/json. **Request:** discriminated union, unknown fields rejected:

- `ingest_dataset`: `{kind,source_id:UUID,target_index_id:UUID}`; source phải registered/enabled/rights-approved; tối đa 1.000 entries/request manifest.
- `reindex`: `{kind,target_index_id:UUID,image_ids:UUID[]}` tối đa 1.000, min1, distinct; target building và manifest đã pinned.
- `delete`: `{kind,image_ids:UUID[]}` min1/max1.000 distinct; transaction tombstone trước enqueue cleanup; tombstone idempotent.
- `retry`: `{kind,retry_of:UUID,item_ids:UUID[]}` chỉ items terminal failed của job đó, tạo job mới và history liên kết; không reset/retry invalid input không đổi nguồn.

**Response:** 202 `{job_id,status:queued,status_url}`; dataset entries chưa materialize durable snapshot không được coi accepted. **Validation:** kind-specific fields, active/live item conflict409, target/source missing404, incompatible target409, batch over cap422. **Lỗi:** common envelope 400/401/403/404/409/422/429/503; image delete tombstone commit và durable job cùng PG transaction. Kết thúc cleanup được theo dõi bằng job, không đồng nghĩa202 đã xóa mọi object.

Ví dụ request:

```json
{"kind":"reindex","target_index_id":"00000000-0000-4000-8000-000000000020","image_ids":["00000000-0000-4000-8000-000000000040"]}
```

```json
{"job_id":"00000000-0000-4000-8000-000000000050","status":"queued","status_url":"/api/v1/index/jobs/00000000-0000-4000-8000-000000000050"}
```

Index activation/rollback/source registration là admin CLI nội bộ ở MVP, không nhận raw collection names/paths qua API.

## 9. `GET /api/v1/index/jobs/{id}` — tiến độ

**Quyền:** `index:manage`, hoặc `images:write` chỉ job upload do chính principal tạo. **Request:** không body, query `limit:int=50` range1…100, `cursor?:opaque-string`; cursor bound job ID, watermark và sort key `(created_at,id)`, không offset. **Response:**200 JobResponse với item page, counts toàn job; limit không ảnh hưởng counts. New items của manifest phải materialize trước durable acceptance nên pagination ổn định theo insertion watermark. **Lỗi:** common envelope 401/403/404/422 invalid cursor/503 DB. Cursor expired trả422 CURSOR_EXPIRED, không tự trả page1 làm trùng.

Ví dụ request: `GET /api/v1/index/jobs/00000000-0000-4000-8000-000000000050?limit=50`.

```json
{"job_id":"00000000-0000-4000-8000-000000000050","kind":"reindex","status":"queued","target_index_id":"00000000-0000-4000-8000-000000000020","counts":{"total":1,"awaiting_input":0,"queued":1,"processing":0,"retry_wait":0,"succeeded":0,"failed":0},"created_at":"2026-11-03T03:00:00Z","updated_at":"2026-11-03T03:00:00Z","items":[{"item_id":"00000000-0000-4000-8000-000000000060","image_id":"00000000-0000-4000-8000-000000000040","index_id":"00000000-0000-4000-8000-000000000020","status":"queued","stage":"embed","attempt_count":0,"last_error_code":null,"next_attempt_at":null}],"next_cursor":null}
```

## 10. `GET /api/v1/health` — live/readiness/capabilities

**Quyền:** public live và safe capabilities; `check=ingest|search` yêu cầu search:read hoặc index:manage. **Request:** không body, query `check=live|ingest|search`, default live. **Response:**200 khi check đạt,503 khi chưa ready, `{status:ok|not_ready,check,capabilities:{text_search,image_search,multimodal,multi_intent,rerank,explanations,agent},dependencies?:{metadata,objects,vectors,encoder,index},worker:{state:unknown|fresh|stale}}`. Live không query dependencies, worker state từ cached status; ingest không cần model load; search cần model/index/required services. Không công bố hosts/credentials/stack/config secrets. Capability là tính năng khả dụng, không suy ra từ UI chỉ có nút.

Ví dụ request `GET /api/v1/health?check=live`:

```json
{"status":"ok","check":"live","capabilities":{"text_search":false,"image_search":false,"multimodal":false,"multi_intent":false,"rerank":false,"explanations":false,"agent":false},"worker":{"state":"unknown"}}
```

Lỗi schema chung cho query sai422/auth401/403; readiness503 có body HealthResponse thay vì ErrorEnvelope là **ngoại lệ contract đã khai báo**, để probes đọc trạng thái. Liveness sống không đồng nghĩa model/index đã sẵn sàng.

## 11. Compatibility và validation kế tiếp

API v1 không thay field type/semantics âm thầm; additions optional được document. Không gọi token stream marker là TTFirst nếu chỉ là status message. API examples là shape minh họa, không dùng làm application fixtures trả cứng. Phase 03 tạo skeleton/OpenAPI với routes theo phase; FR-001/002 thuộc Phase 05, optional endpoints báo disabled trước khi triển khai. Kiểm chứng runtime auth/upload/deadline/content proxy và generated OpenAPI ở Phase 03–11, chưa thực hiện tại Phase 02.

## 12. Trạng thái implementation Phase 03

Mục1–11 là contract mục tiêu theo phase. Hiện chỉ đăng ký bốn foundation endpoints dưới đây cùng `/docs` và `/openapi.json`; search/images/index jobs/content chưa đăng ký, trả404 NOT_FOUND theo error envelope, không trả empty results giả. Feature-disabled409 chỉ áp dụng sau khi route tương ứng được triển khai/gated.

| Endpoint thực | Auth | Response / readiness policy |
| --- | --- | --- |
| GET /api/v1/health/live | Public | 200 `{status:alive,service}`; không probe data services |
| GET /api/v1/health/ready | Bearer local | 200/503 `{status:ready|not_ready,dependencies:{postgresql,qdrant,minio}}`; từng dependency healthy/unhealthy/timeout; kiểm tra hạ tầng thực, chưa model/index |
| GET /api/v1/health | Public khi check=live; Bearer khi ingest/search | Giữ HealthSummary contract; mọi capability search=false; check=search503 với encoder=not_implemented/index=not_initialized; worker unknown |
| GET /api/v1/system/info | Bearer local | 200 app_name/app_version/environment/api_version; không URL/credentials/config dump |

Liveness/readiness routes mới chi tiết hóa yêu cầu Phase 03, không thay `/health` cũ. Request ID UUID hợp lệ được echo, ID không hợp lệ được thay; errors có code/message/request_id/retryable/details. OpenAPI định nghĩa ErrorEnvelope cho validation/auth/generic timeout; health503 là readiness model đã document. Trong phase này token local được cấu hình bởi API_TOKEN và chỉ có read diagnostics, chưa user/scope administration. CORS chỉ GET/OPTIONS vì chưa có write/search endpoints.

REQUEST_TIMEOUT_SECONDS mặc định2s, ba dependency probes chạy song song với deadline0,75s mỗi probe. MinIO SDK blocking I/O có HTTP bounds và giữ executor slot tới khi I/O xong dù caller timeout. Duration chốt tại final response send, không bao gồm công việc sau body. Test/runtime evidence và các phần chưa kiểm chứng tại [PHASE03_REPORT](../archive/PHASE03_REPORT.md).

## 13. Trạng thái implementation Phase 04

Đã đăng ký POST /images, GET /images/{image_id}, GET /images/{image_id}/content, POST /index/jobs và GET /index/jobs/{job_id}. Health/system routes Phase 03 giữ tương thích. Swagger có multipart upload và typed upload/job responses; chưa có /search routes.

Local auth dùng hai opaque operator tokens: API_TOKEN chỉ read; WRITE_API_TOKEN cấp read + images:write/index:manage, mutations fail closed khi chưa cấu hình. Chưa có multi-user/tenant/scoped token database. Nonfixture metadata yêu cầu source_dataset/license/rights_ref; bổ sung caption optional được cung cấp bởi operator, không tự sinh. Upload total deadline30s, core/health vẫn2s; file/body/JSON/pixel limits theo IMAGE_INDEXING. Content proxy buffer bounded bởi20MiB, thumbnail fallback original; chưa Range hoặc thumbnail generation.

Idempotency lưu body fingerprint, reserved image/job identities và acceptance response trước external I/O. Same key đang xử lý trả409 IDEMPOTENCY_IN_PROGRESS + Retry-After:1; known failure giải phóng upload lease, crash-resume sau lease vẫn cùng identities. expires_at24h được lưu nhưng chưa auto-GC; retained completed records replay an toàn. Dataset API chỉ nhận registered object manifest source; CLI materialize bytes trước khi đăng ký. Reindex target building, retry tạo job mới liên kết history; delete kind được nhận diện nhưng trả409 FEATURE_DISABLED và không xóa dữ liệu.

Job response bổ sung started_at/finished_at và error_summary; counts là aggregate toàn job, item cursor theo(created_at,id), bound job và total-items watermark. Không reset attempt history của job cũ khi retry. Body/fields/limits/errors được kiểm tra runtime; commands và evidence tại [IMAGE_INDEXING](../features/IMAGE_INDEXING.md) / [INDEXING_TEST_REPORT](../archive/INDEXING_TEST_REPORT.md). Mô tả đầy đủ các phase khác ở trên vẫn là contract thiết kế, không là claim implementation.

## 14. Implementation Phase 05

POST /search thực thi canonical text/image-only; POST /search/multimodal nhận image-only compatibility route theo Phase 05, text+image fusion vẫn409 FEATURE_DISABLED. Query/search_mode legacy aliases normalize sang text/mode canonical; response vẫn search_mode=text|image. Top-K mặc định10, runtime max50/config≤100; basic filters được bật với PG authoritative recheck. Thêm exclude_self, total_results và latency_ms processing alias; không đổi semantics canonical fields. Chi tiết actual contracts và errors tại [SEARCH_API](../features/SEARCH_API.md).

Private GET /system/search-metrics là diagnostic addition để join full-response samples sau final send; không query text/images/credentials. Ring10.000/process, không durable history. Search health text/image flags từ loaded runtime, advanced flags false. Active pointer publish qua CLI sau full verify/model preload; query không nhận arbitrary model/collection. Query uploads không tạo image/jobs/index records. API image nay chứa paired CLIP runtime; không cần phụ thuộc Agent/LLM.

## 15. Cập nhật implementation Phase 06

POST search giữ core text/image contracts, thêm search_mode aliases auto/multi_intent và rerank boolean alias. Text+image paired dùng multimodal route, không core. POST search/multimodal hiện nhận text-only/image-only hoặc combined; đây là compatible extension của image-only Phase 05 và paired design Phase 02. Fusion có RRF/weighted_rrf alias/weighted_score, request weights có bounds và được normalize, no all-zero. Typed recursive constraint AST giữ depth2/leaves8/unique IDs, thêm negated/weight. Required semantics không được verify chỉ bằng CLIP; strict required semantic leaf trả409 VERIFIER_UNAVAILABLE.

Response bổ sung query_analysis, contributing_branches, score_components và constraint_evidence uppercase alias; canonical constraint_assessments satisfied/violated/unknown giữ nguyên. Score_type thêm weighted_score, service_class advanced cho advanced paths. Actual validation/error/limits, optional failure policy và complete-response telemetry tại [ADVANCED_SEARCH_API](../features/ADVANCED_SEARCH_API.md), evidence tại [ADVANCED_SEARCH_TEST_REPORT](../archive/ADVANCED_SEARCH_TEST_REPORT.md). Baseline examples/capability flags trong phần thiết kế trước giữ lịch sử, không mô tả đầy đủ trạng thái hiện tại.

## 15. Runtime profiling Phase 07

`GET /api/v1/system/search-runtime` cần read Bearer token như diagnostic search endpoints. Không nhận query/body. Response200 có status, pid/python/platform/logical_cpus, CPU user/system seconds, process_memory_kib(VmRSS/VmHWM), process_threads, model_initialization_ms, safe settings, model/index/revision/dimension/device/generation khi sẵn sàng và gpu_measurements=null ở máy CPU hiện tại. Không trả secret, query data hoặc storage keys. Thiếu/sai token trả401 theo error envelope. Các counters là snapshot, không là per-query memory allocation. Benchmark join full ASGI timing vẫn qua search samples; endpoint này chỉ lấy tài nguyên/runtime. OpenAPI hiện hành tại `/openapi.json`; contract và integration test nằm trong `api/v1/system.py` và `test_real_evaluation.py`.

## Cập nhật triển khai Phase 08

Đã có RAG metadata tùy chọn, tái sử dụng SearchService/active CLIP, batch evidence validation/current IDs, bounded context/prompts, Gemini/OpenAI-compatible adapter, citation validation, JSON/SSE và React explanation panel. Không gửi ảnh sang provider hoặc thay Fast Search/ranking. Gemini key ở backend; generator tắt/lỗi giữ ảnh. Với corpus10 ảnh không caption/tags, chưa thể xác minh nội dung thị giác. [Kiến trúc](../features/RAG_ARCHITECTURE.md), [API hiện hành](../features/RAG_API.md), [cấu hình](../features/RAG_IMPLEMENTATION.md), [đánh giá](../research/RAG_EVALUATION.md), [nghiệm thu A–L](../archive/PHASE08_TEST_REPORT.md). Không triển khai Phase 09.


## Bổ sung tương thích Phase10 — 07/11/2026

- `GET /api/v1/system/workspace`: `require_read_access`, read-only. Trả dataset state/counts/index generation, capabilities của search/RAG/Agent, giới hạn top_k/image_bytes và dependency observation; không gọi LLM. Lỗi dependency trả trạng thái `unavailable`, count không biết là null. Không suy ra dữ liệu rỗng từ lỗi.
- `GET /api/v1/system/evaluation`: `require_read_access`, read-only. Trả `state`, `skipped`, `experiments[]` từ evaluation root cố định của server, allowlist aggregate numeric metrics; không cho client chỉ định đường dẫn hoặc đọc samples/secret. Không có nhãn chất lượng thì Recall@10 không công bố.
- `GET /api/v1/images/{id}`: metadata thiếu được biểu diễn nullable thay vì dereference lỗi. Content proxy và quyền truy cập giữ nguyên; thumbnail vẫn cho phép fallback original.

Response shape, state enum, error/streaming integration và ví dụ thực xem [FRONTEND_API_INTEGRATION.md](../features/FRONTEND_API_INTEGRATION.md). Không đổi established search/RAG/Agent request contract, không migration Phase10.
