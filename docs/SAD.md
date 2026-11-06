# SAD — Thiết kế kiến trúc phần mềm

Cập nhật triển khai Prompt06: multimodal late fusion, multi-intent/AND/OR và lightweight reranking đã được bổ sung trên core Prompt05. Fast path không gọi LLM hoặc tự fan-out query đơn giản. [Báo cáo Prompt06](ADVANCED_SEARCH_TEST_REPORT.md) ghi tests/số đo/giới hạn; [API hiện hành](ADVANCED_SEARCH_API.md) bổ sung contracts. Các sections baseline/historical bên dưới giữ ngữ cảnh thiết kế, không phải bằng chứng triển khai mọi tính năng tương lai.

Phiên bản thiết kế1.1.0 · 2026-11-03 · Baseline Prompt02. Foundation Prompt03 đã nghiệm thu API/config/data adapters/health, frontend responsive và năm Docker services với persistence/outage tests; Worker ingestion/CLIP/indexing hiện có ở Prompt04; Core Semantic Search text/image hiện có Prompt05; advanced intelligence ports còn là target phase sau. [SEARCH_TEST_REPORT](SEARCH_TEST_REPORT.md) ghi evidence mới. [INDEXING_TEST_REPORT](INDEXING_TEST_REPORT.md) ghi evidence mới. Chi tiết implementation/evidence tại [PHASE03_REPORT](PHASE03_REPORT.md).

## 1. Đầu vào và ranh giới

Đầu vào là [PRD](PRD.md) và baseline Prompt 01. Các nhóm FR-001…024 và NFR-001…012 đã được xác định; ID cũ vẫn truy được. Thiết kế không yêu cầu thêm broker, cache service, graph database hoặc inference microservice. Các giá trị giới hạn khởi đầu tại [PERFORMANCE_DESIGN](PERFORMANCE_DESIGN.md) là giả định có thể override qua cấu hình có kiểm tra, không phải capacity được chứng minh.

## 2. Architectural style

Modular monolith phù hợp nhóm làm đồ án và tài nguyên vận hành hạn chế: một codebase backend, interface nội bộ typed, deploy API/worker thành hai process riêng. Tránh network hops giữa các business module, dễ chạy integration tests và thay adapter. Đổi lại cần kỷ luật dependency, kiểm soát shared CPU/GPU và không scale từng module độc lập. Có thể tách encoder/worker sau khi profile chứng minh nhu cầu; chưa thiết kế microservices giả định.

Frontend React chỉ gọi HTTP API. API xử lý validation/auth/deadline; application orchestrator gọi domain ports; adapter triển khai SQLAlchemy/Qdrant/MinIO/Transformers. Domain/retrieval không import optional agent/generator. Dùng PostgreSQL durable jobs cho offline worker, không dùng FastAPI in-process background task làm durable queue.

## 3. Cấu trúc module dự kiến

```text
backend/app/
  api/                 routes, DTO, auth, middleware
  core/                config, errors, deadlines, tracing
  query/               normalization, routing, constraint AST
  embeddings/          manifest, paired encoder port, Transformers adapter
  retrieval/           candidates, vector port, fusion, filtering, ranking
  ingestion/           validation, identity, job service, worker, reconciliation
  metadata/            repository ports, SQLAlchemy adapters
  storage/             private object port, MinIO adapter
  intelligence/        optional tools, workflow, evidence, generation
evaluation/            manifests, judgments, metrics, load harness
frontend/              typed API client, search/details/capability views
infra/                 Compose/build definitions ở Prompt 03
```

Đây là sơ đồ thư mục trong tài liệu; không tạo application source ở Prompt 02. Migrations nằm backend; tests tách unit/integration/model/e2e. Phiên bản package/container được pin tại Prompt 03, model artifact tại Prompt 04.

## 4. Data contracts nội bộ

| Kiểu | Trường quan trọng và invariant |
| --- | --- |
| RequestContext | request_id UUID, principal_id, scopes, monotonic deadline, cancellation; không truyền token raw xuống log |
| SearchCommand | requested_mode, text hoặc validated image/image_id, K, C, filters, constraint AST, rerank policy; dùng contract API |
| EmbeddingManifest | id/hash, model/revision/processor revision, dimension d > 0, dtype, preprocessing hash, normalization=l2, metric=cosine, tokenizer/truncation policy |
| QueryEmbedding | finite normalized vector[d], manifest_hash; chỉ được query index có cùng manifest |
| Candidate | image_id UUID, channel, native_score/type, rank, payload_revision, index_id; không có probability |
| ConstraintAssessment | clause_id, satisfied/violated/unknown, evidence_ref, evidence_kind, confidence nếu có nguồn hiệu chuẩn; mặc định không có confidence |
| RetrievalBatch | candidates, index snapshot, ranking/fusion versions, eligible counts, truncated flag, warnings |
| EvidenceRecord | evidence_id, image/entity ID, source/provenance, assertion, timestamp/version, verification state |
| IndexItem | job_id, item_id, image_id, index_id, stage, claim_token, attempts, source_ref, last_error; READY phải có object và point xác nhận |

Mỗi request capture active `index_id` và manifest một lần, sau đó query trực tiếp collection cụ thể. Không query collection alias đang đổi rồi dùng manifest cũ. Các interface nhận deadline còn lại thay vì tạo timeout mới cho từng bước.

## 5. Trách nhiệm, interface và vận hành

Mọi interface dưới là thiết kế, không phải method đã tồn tại. Duration dùng monotonic; chỉ log ID, outcome và counts an toàn. Timeout cụ thể và caps ở PERFORMANCE_DESIGN.

| Component | Trách nhiệm / public interface / I/O | Dependency | Failure / timeout | Observability |
| --- | --- | --- | --- | --- |
| React UI | `submitSearch`, `getImage`, `pollJob`; form → typed DTO → grid/details/preview | API và authenticated content proxy | abort/stale response, decode preview, 401/empty; client deadline lớn hơn server có kiểm soát | Client latency, render duration, safe request ID |
| FastAPI API | `search`, `upload`, `job`, `health`; HTTP → DTO/context → response/error | App services, auth config | 400/401/403/413/415/422/429/503/504; body parser nằm trong deadline | Full ASGI latency, status, request ID, bytes |
| Query processor/router | `normalize`, `route`, `extractConstraints`; SearchCommand → normalized query/AST | Rules/tokenizer limits | unsupported grammar/negation → warning hoặc reject strict; không tự gọi LLM | Route, clause count, processing span |
| Search orchestrator | `execute(command, context)` → SearchResult | Encoder/retrieval/ranking/metadata ports | thiếu index/model, deadline, insufficient candidates; chỉ explicit agent endpoint gọi optional workflow | Stage spans, executed mode, versions |
| Embedding adapter | `encode_text`, `encode_image`, `describe`; validated input → QueryEmbedding | Pinned paired model/processors, PyTorch | model load/OOM/nonfinite/truncation; bounded queue, inference slot; timeout không đồng nghĩa GPU đã cancel | Load/inference duration, queue wait, device/memory, manifest |
| Vector adapter | `search`, `upsert`, `delete`, `verify`; vector/filter → candidate list/write ack | Qdrant | connection/timeout/schema mismatch; bounded C/fan-out; write phải applied trước ready | Query/upsert duration, C, index/version, ack state |
| Filtering/fusion/reranking | `eligible`, `fuse`, `rerank`; candidates + AST → ranked list | Metadata/evidence, optional reranker | stale payload, missing metadata, unknown semantics, reranker unavailable; fail/fallback theo policy | Removed counts/reasons, constraint coverage, method version |
| Metadata repository | `get_many`, `reserve_identity`, `publish_ready`, `lookup_relation`; typed IDs → records | PostgreSQL | outage, conflicts, lock/statement timeout; batch hydrate, CAS ownership | DB spans, conflict/fence failures, query count |
| Object adapter | `stage`, `put_immutable`, `head`, `get`, `delete`; bytes/key → receipt/content | Private MinIO | unavailable, digest mismatch, missing object; bounded size/stream duration | Object operation duration, bytes, repair events; không URL/token |
| Ingestion/job worker | `accept`, `claim`, `process`, `reconcile`; source/item → progress | Validation, all three stores, encoder | lease expiry/crash/partial writes/invalid file; finite retry/item deadline | Queue age, stage, attempts, claim token hash, failed items |
| Evidence/RAG | `explain(evidence, image_ids)` → validated explanation/citations | Optional generator; evidence ports | insufficient evidence, provider timeout, bad citation; optional output budget | TTFirst/TTLast nếu adapter hỗ trợ, grounding failures |
| Agent workflow/tools | `run(plan,state)`, allowlisted tools → evidence/results | Core retrieval, PostgreSQL relations; RAG optional | unknown/ambiguous relation, loop/budget/tool failure; shared total deadline | Tool/hop spans, evidence refs, fallback reason; không chain-of-thought |
| Evaluation harness | `evaluate(run_manifest)` → metrics/raw artifacts | Corpus/query/qrels, API/model harness | incomplete judgments, version drift, failed load; abort invalid run, không thay bằng số giả | Manifest hashes, sample/error counts, resource samples |

## 6. Fast path, query routing và search readiness

`auto` chỉ chọn text/image/multi_intent theo input và patterns hỗ trợ; cả text+image phải dùng multimodal endpoint. Agent chỉ qua `/search/agent`. Query nhiều điều kiện không kích hoạt LLM. Nếu patterns mơ hồ: giữ query gốc làm semantic text; trả warning khi không extract được toàn bộ điều kiện. `require_verified=true` yêu cầu clause rõ/được hỗ trợ; không âm thầm claim verification.

Liveness chỉ kiểm tra process. `ingest_ready` cần PostgreSQL và MinIO, worker heartbeat được báo riêng. `search_ready` cần PostgreSQL, Qdrant, active manifest/index khớp và encoder đã load; kiểm tra object service readiness vì results phải truy cập được. Không bắt buộc có ảnh trong index: index rỗng hợp lệ trả empty. Bootstrap chưa có model/index không làm liveness thất bại. Optional agent/generator có capability riêng. Health cached probes ngắn; search vẫn xử lý lỗi dependency thực tế, không dựa tuyệt đối vào cached health.

Search hydrate metadata một lần theo batch, kiểm tra active-version readiness, object receipt và metadata revision. Không HEAD từng MinIO object cho mọi kết quả; worker xác nhận object lúc ready và reconciliation phát hiện drift. Content proxy trả 503 cho kho lỗi, 404 và enqueue repair khi object mất. Vì vậy stale external deletion có thể khiến result vừa trả không tải được; đây là cửa sổ eventual consistency được báo, không cam kết transaction toàn hệ thống.

## 7. Offline consistency, concurrency và lifecycle

Upload API validate/spool/hash trong bounds; reserve image/job ở PostgreSQL dưới trạng thái `awaiting_input`; ghi object staging bằng key UUID đã lưu; commit `queued` chỉ sau staging receipt. Trả 202 sau cả staging durable và job queued. Crash trước commit được watchdog kiểm tra object và đưa tiếp queued hoặc fail có lý do; không tuyên bố acceptance nếu chỉ có queue trong RAM. Upload duplicate đang ready trả 200 và không thay metadata asset cũ bằng metadata từ request mới. Stage orphan được dọn theo grace và reference check.

Worker claim item bằng transaction ngắn `FOR UPDATE SKIP LOCKED`, set lease/claim_token/attempt; commit trước external I/O. Renew lease, cập nhật state bằng compare-and-swap với token hiện tại. `SKIP LOCKED` dành cho queue, không dùng làm snapshot nhất quán cho evaluation. Cơ chế này dựa trên [PostgreSQL SELECT](https://www.postgresql.org/docs/current/sql-select.htm).

Một image/index chỉ có một task live theo partial unique constraint. Stale worker không được publish ready. Object gốc bất biến theo hash; embedding cùng manifest/digest là cùng identity. Upsert point có thể replay; `wait=true` và xác minh manifest/digest trước commit ready theo [Qdrant upsert](https://api.qdrant.tech/api-reference/points/upsert-points). Claim token không tự fence được external store: stale payload vẫn có thể xuất hiện, nên PG recheck metadata_revision/lifecycle và repair bắt buộc. Delete tombstone chặn đọc ngay; cleanup cuối chỉ sau khi các writer cũ đã drain/được dừng và được xác minh, không chỉ chờ lease hết.

Reindex build collection riêng, đối chiếu corpus snapshot + catch-up metadata/deletion changes, xác nhận coverage/config/smoke, preload model mới rồi chuyển active pointer bằng PG transaction. Request đang chạy pin index cũ; giữ collection/model cũ tới khi in-flight drain. API có thể trả `503 INDEX_SWITCHING` ngắn khi tài nguyên không cho giữ hai model; không dùng model cũ query index mới. Chi tiết state/recovery tại DATABASE_DESIGN.

## 8. Security và data governance

Single-tenant local MVP dùng opaque Bearer scopes; compare secret an toàn, token không ở Git/log/URL. Chỉ API được expose cho browser; data ports private, không public MinIO/Qdrant/PostgreSQL. Media qua authenticated proxy, không signed URL mặc định; browser dùng fetch với Authorization rồi tạo blob URL và revoke khi hết dùng. Content response `Cache-Control: private, no-store`, `X-Content-Type-Options: nosniff`; không render SVG hoặc HTML từ upload. Restrict CORS origin cụ thể; không wildcard cùng credentials.

SEC-01: content decode JPEG/PNG/WebP static, byte/pixel/side/frame limits và isolation decoder; format unsupported trả 415, hỏng trả 422, oversized trả 413. SEC-02: generated keys, source registry chỉ admin, canonical-path confinement và symlink escape check. SEC-03/04: private buckets, least privilege, roles/quota. SEC-05: whitelist filter fields/operators, parameterized SQL, sanitized errors. SEC-06: bounded queue/deadlines, resource isolation. SEC-07: untrusted metadata/evidence không thay system instruction; typed tool allowlist. SEC-08: rights manifest trước corpus thật; indexed originals giữ tới explicit delete, query upload không được tự index và bị xóa khỏi temp ngay khi request kết thúc; crash cleanup có TTL tối đa 1 giờ cho temp có owner không còn sống.

Search telemetry mặc định chỉ technical fields, không lưu text/raw image hay query-image hash. History opt-in bằng policy riêng và quyền chủ sở hữu; default disabled. Không có multi-tenancy/ownership isolation giữa corpus trong thiết kế này; nếu thêm phải thay dedup scope, object authorization và tất cả queries.

## 9. Quality attributes và tradeoffs

| Đánh đổi | Quyết định thiết kế | Bằng chứng cần ở phase sau |
| --- | --- | --- |
| Latency / relevance | Candidate depth và reranking có caps, không bật rerank cho mọi query | E3 ablation chất lượng + P90/P95 |
| Accuracy / compute | CLIP baseline; model lớn/multilingual là E2, không assume tốt hơn | Cùng judgments, resource và latency |
| ANN speed / recall | Tune HNSW/search ef trên dev, so exact neighbor khi phù hợp | ANN neighbor recall tách khỏi relevance Recall@10 |
| Reranker / deadlines | `off` mặc định; explicit fallback policy khi bật | Added latency, failure và joint relevance |
| Local / external model | Core local; external generator optional, data egress phải được chấp thuận | Token timing, rights/privacy và vận hành |
| Simplicity / scalability | Một codebase, PG jobs, private services; scale API/worker khi resource cho phép | Queue age, DB contention, model memory/replica cost |
| Reasoning depth / response time | Max 3 hops, 6 tool calls, total deadline 5 s dự kiến; không reset khi fallback | E4 success, tool timing, TTLast và deadline misses |
| Consistency / latency | Ready receipts + authoritative PG recheck; không transaction liên kho | Fault injection, stale-object window, reconciliation report |

## 10. Dependency validation và handoff

PRD có đủ 12 nhóm, typed contracts và acceptance inventory. SYSTEM_ARCHITECTURE tiếp theo mô tả các luồng dùng đúng ports này; DATABASE_DESIGN phải chứa identity/manifest/item leases và API phải phản ánh scope, transport, partial timer, disabled modes. Các điểm chưa chốt: corpus/hardware/language/quality gate, exact dependency/model pins và public deployment. Không xem đó là runtime đã hoạt động.

## Cập nhật triển khai Prompt07

Evaluation chạy qua CLI riêng trong cùng modular monolith, tái sử dụng encoder/registry/durable reindex/repositories và API thật. Fast Search giữ CLIP512/generation1; SigLIP2-768 là research index riêng, không activate. Có safe runtime endpoint, offline annotation, immutable source/results, load và report generation; không đưa model so sánh hoặc logic chấm điểm vào request path. Object-check window1/2 có giới hạn, mặc định1 sau ABBA không chứng minh full-latency gain. [Báo cáo nghiệm thu](PHASE07_TEST_REPORT.md) ghi pending human-quality gate; Agentic Search/RAG vẫn chưa triển khai.

## Cập nhật triển khai Prompt08

Đã có RAG metadata tùy chọn, tái sử dụng SearchService/active CLIP, batch evidence validation/current IDs, bounded context/prompts, Gemini/OpenAI-compatible adapter, citation validation, JSON/SSE và React explanation panel. Không gửi ảnh sang provider hoặc thay Fast Search/ranking. Gemini key ở backend; generator tắt/lỗi giữ ảnh. Với corpus10 ảnh không caption/tags, chưa thể xác minh nội dung thị giác. [Kiến trúc](RAG_ARCHITECTURE.md), [API hiện hành](RAG_API.md), [cấu hình](RAG_IMPLEMENTATION.md), [đánh giá](RAG_EVALUATION.md), [nghiệm thu A–L](PHASE08_TEST_REPORT.md). Không triển khai Prompt09.
