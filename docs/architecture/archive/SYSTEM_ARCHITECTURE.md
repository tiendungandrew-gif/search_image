# Kiến trúc hệ thống và các luồng xử lý

**Phase10 — 07/11/2026:** giao diện Lens tích hợp typed JSON/SSE, private media/detail, dataset status và evaluation aggregates; [kiến trúc frontend](../../features/FRONTEND_ARCHITECTURE.md), [báo cáo nghiệm thu](../../archive/PHASE10_TEST_REPORT.md). Giữ PostgreSQL/Qdrant/MinIO, worker, active-index cutover và Fast/Agent separation.

## Hoàn thiện Phase 09 — 06/11/2026

Đã bổ sung bộ địa danh NPS có nguồn:3 ảnh thật,4 entities,3 quan hệ và3 liên kết ảnh. Index phục vụ hiện513 ảnh, generation3; index510 ảnh cũ giữ nguyên. Workflow Anh/Việt/alias, Gemini planner và RAG thật đã được kiểm tra. Planner có trace từng attempt; prompt tools và RAG context đã rút gọn, citation provenance vẫn giữ đầy đủ trên server. Bộ kiểm tra mới đạt200 backend,21 frontend unit và24 browser full tests cùng6 ca browser nhánh cuối. Chất lượng do người đánh giá vẫn chờ; số đo latency và trạng thái target3s xem [báo cáo Phase 09](../../archive/PHASE09_TEST_REPORT.md), dữ liệu/nguồn tại [PUBLIC_LANDMARK_DATASET](../../research/PUBLIC_LANDMARK_DATASET.md).

## Cập nhật runtime Phase 09

Agent endpoint/UI đã triển khai, dùng router → validated plan → allowlisted tools → request-local state → evidence revalidation → optional RagService. Core retrieval không phụ thuộc Agent; không có microservice/dependency orchestration mới. JSON và SSE là hai endpoints riêng; progress không có private reasoning. [Kiến trúc và sơ đồ Agent](../../features/AGENT_ARCHITECTURE.md), [sequence multi-hop](../../features/MULTI_HOP_SEARCH.md), [kết quả chạy](../../archive/PHASE09_TEST_REPORT.md). Phần thiết kế ban đầu bên dưới được giữ để đối chiếu, không coi mọi module tương lai là đã hiện thực.

Cập nhật triển khai Phase 06: multimodal late fusion, multi-intent/AND/OR và lightweight reranking đã được bổ sung trên core Phase 05. Fast path không gọi LLM hoặc tự fan-out query đơn giản. [Báo cáo Phase 06](../../archive/ADVANCED_SEARCH_TEST_REPORT.md) ghi tests/số đo/giới hạn; [API hiện hành](../../features/ADVANCED_SEARCH_API.md) bổ sung contracts. Các sections baseline/historical bên dưới giữ ngữ cảnh thiết kế, không phải bằng chứng triển khai mọi tính năng tương lai.

Phiên bản 1.1.0 · 2026-11-03 · Baseline thiết kế Phase 02; API/worker/storage/Core Search đã triển khai theo Phase 03–05, xem [INDEXING_TEST_REPORT](../../archive/INDEXING_TEST_REPORT.md). Đầu vào đã đối chiếu: [PRD](../PRD.md) và trách nhiệm/ports tại [SAD](../SAD.md). Diagrams nguồn tại `docs/diagrams/` là một phần của thiết kế.

## 1. C4: System Context, Container, Component

| Mức | Nội dung | Mermaid nguồn |
| --- | --- | --- |
| Context | Người tìm ảnh, admin, evaluator; hệ thống và generator tùy chọn | [system_context.mmd](../../diagrams/system_context.mmd) |
| Container | React, API, cùng-codebase worker, PostgreSQL, Qdrant, MinIO, evaluation runner | [container_architecture.mmd](../../diagrams/container_architecture.mmd) |
| Component | API/router/search orchestrator, encoders, vector/filter/fusion/metadata ports, optional agent/RAG | [component_architecture.mmd](../../diagrams/component_architecture.mmd) |
| Deployment | Linux local, browser/API boundary, network data private, volumes và device allocation | [deployment_architecture.mmd](../../diagrams/deployment_architecture.mmd) |

Các flowchart dùng ký hiệu Mermaid phổ thông để diễn đạt C4, không yêu cầu extension C4. Container ở đây là process/service boundary, không phải quyết định triển khai microservices. External generator chỉ hiện khi P2 bật, không nối vào encoder core.

## 2. High-level architecture

User → React Frontend → FastAPI Backend → Query Router → Search Orchestrator. Orchestrator điều phối retrieval typed; không đồng nghĩa AI Agent. Backend authorize/validate trước mọi route. Hai đường dùng cùng metadata repository, vector adapter, object access và active model/index registry:

- **Fast Search:** input processing → text/image paired encoder → Qdrant candidates → hard filter/authoritative eligibility → optional fusion/reranking → Top-K metadata/results.
- **Advanced Search:** explicit agent request → bounded planner → typed tools → dependent retrieval/lookup → evidence aggregation → optional RAG → validated results và trace.

Indexing không nằm trong latency-critical search path. Query image upload để tìm kiếm chỉ tồn tại trong request temp; upload vào corpus dùng endpoint khác và durable job.

## 3. Offline indexing

Dataset đăng ký hoặc upload → validate actual bytes/resources → SHA-256 và reserve UUID/dedup → staging durable → queued item → preprocessing theo model → image embedding → extract metadata khả dụng → immutable original/optional thumbnail → metadata receipt → Qdrant upsert applied → ready commit bằng current claim token.

Sequence: [image_ingestion_sequence.mmd](../../diagrams/image_ingestion_sequence.mmd). API có thể đọc kích thước/format ngay khi validate; worker xác nhận lại digest và decode trước inference. Metadata nguồn và metadata dẫn xuất được phân biệt; caption không bắt buộc. Khi PG identity đã có nhưng stage chưa xong, item là awaiting_input và worker không claim. Watchdog xử lý interrupted acceptance, không bỏ stranded rows.

| Cơ chế | Thiết kế |
| --- | --- |
| Async/durability | PostgreSQL job/items và MinIO staging; 202 chỉ sau durable queue commit; không phụ thuộc request process còn sống |
| Batch | Manifest nguồn allowlist và snapshot/hash; admin đăng ký source qua CLI; mỗi entry một item; giới hạn batch ban đầu 1.000 |
| Idempotency | Unique image hash, image/index, item job/source identity; Idempotency-Key cho mutation; cùng key khác body → 409 |
| Retry | Tối đa 5 attempts/item; transient exponential backoff full jitter với cap 60 s; decode/rights/unsupported không retry |
| Lease | Claim 60 s, heartbeat 10 s, item wall-clock 120 s; process bị timeout phải dừng/fence; không giữ DB transaction suốt inference |
| Failed/dead-letter | Item `failed` + safe error/history trong PG là dead-letter; không thêm broker; admin retry tạo job mới có `retry_of` |
| Partial recovery | Stage/object/vector receipt và progress persisted; recheck external state trước retry; upsert idempotent, ready CAS fenced |
| Reindex | New collection/index manifest; build snapshot, catch up changes, validate, activate pointer, drain old requests, rollback có model tương ứng |
| Reconciliation | Đối chiếu ready records ↔ object digest/point manifest; repair thiếu artifact; stale/orphan cleanup có grace/reference check |

Số attempts/deadlines trên là cấu hình khởi đầu, chưa có benchmark. Thời hạn TTL staging không được xóa object còn được live/retry job tham chiếu. Model/index migration không ghi vector mới vào collection cũ khác space.

## 4. Các đường online search

| Loại | Component và quy tắc | Diagram |
| --- | --- | --- |
| Text-to-image | API → normalize/token limit → capture active manifest → text encoder → Qdrant → PG eligibility → rank/Top-K | [text_search_sequence.mmd](../../diagrams/text_search_sequence.mmd) |
| Image-to-image | Multipart validate/decode hoặc authorized image_id → image encoder cùng manifest → Qdrant → hydrate/Top-K; temp cleanup | [image_search_sequence.mmd](../../diagrams/image_search_sequence.mmd) |
| Text + image | Encode riêng từng modality → candidate lists cùng index snapshot → union UUID → weighted RRF → filter/optional rerank | [multimodal_search_sequence.mmd](../../diagrams/multimodal_search_sequence.mmd) |
| Single-intent | Router chọn direct text/image; không planner/LLM; cùng flow text/image | text_search_sequence và image_search_sequence |
| Multi-intent | Normalize → constraint AST → bounded per-clause retrieval → evidence verify → merge/fusion → constraint tiers/rerank | [multi_intent_sequence.mmd](../../diagrams/multi_intent_sequence.mmd) |
| Agentic multi-hop | Explicit mode → resolve relation/entity → dùng output entity của hop trước tạo query sau → retrieval → evidence → optional generation | [multi_hop_agent_sequence.mmd](../../diagrams/multi_hop_agent_sequence.mmd) |

Mọi request pin một index/manifest; metadata hydration loại ảnh pending/deleting/deleted, embedding chưa ready hoặc payload_revision không khớp. Không tự mở rộng search sang index khác model để lấp K. Nếu C ứng viên không đủ ảnh eligible, trả ít hơn K với warnings/counts; có thể thử bounded refill khi còn deadline nhưng tổng candidates/calls không vượt caps. ANN có thể bỏ sót match; không claim exhaustiveness.

## 5. Multi-intent và constraint semantics

AST gồm group AND/OR và leaf `{id, kind: metadata|semantic, predicate/text, required}`. Tối đa 8 leaves, depth 2; deterministic extractor hỗ trợ conjunction/disjunction đơn giản, explicit constraints được ưu tiên. Metadata nằm trong filter riêng là hard AND với toàn query. Không hỗ trợ grammar/negation rõ ràng thì strict mode trả 422; best-effort giữ text và báo decomposition_partial. Không gửi LLM để đoán điều kiện trong fast path.

| Tình huống | Luật |
| --- | --- |
| AND | satisfied khi mọi leaf satisfied; violated nếu có leaf violated; còn lại unknown |
| OR | satisfied khi ít nhất một leaf satisfied; violated khi tất cả violated; còn lại unknown |
| Required metadata | Pushdown supported predicates và PG recheck. Missing/null không thỏa positive predicate; không âm thầm bỏ qua |
| Optional metadata | Không hard reject; evidence ảnh hưởng tier/secondary score theo method version |
| Required semantic | Không có verifier/evidence thì unknown. `require_verified=true` loại unknown/violated; best-effort giữ nhưng đánh dấu chưa xác minh |
| Optional semantic | Thêm preference; unknown không được tính là confirmed |
| Conflict | Hard filter contradiction có thể phát hiện → 200 empty với reason; invalid/malformed predicate → 422 |
| Merging | Union candidates theo UUID; lưu channel scores/ranks; không cộng số lần trùng như ảnh mới |

Candidate retrieval dùng query toàn văn và tối đa 4 channels tổng cộng, ưu tiên clauses required, caps tại PERFORMANCE_DESIGN. Nếu extraction nhiều clauses hơn retrieval channels, vẫn verify tất cả clauses, ghi coverage/truncated; bounded retrieval không đảm bảo tìm được mọi match AND. Structured predicate có thể kiểm tra chắc theo metadata; caption mention là evidence nguồn caption, không tự nâng thành xác minh thị giác. Một cosine cao không chứng minh tất cả leaf.

Initial ordering: hard eligibility → required-condition tier (all confirmed; partial/unknown; violated nếu best-effort cho phép) → weighted RRF hoặc native cosine → optional confirmed fraction → UUID. `constraint_satisfaction = confirmed_required / required_count`, kèm `unknown_count` và `violated_count`; required_count=0 thì satisfaction=null. Tỉ lệ này không phải xác suất và không thể dùng để che unknown. Khi `require_verified=true`, chỉ tier all-confirmed được trả; không có verifier phù hợp thì 409 VERIFIER_UNAVAILABLE thay vì giả vờ strict hoạt động.

## 6. Multimodal fusion

| Cách | Ưu/nhược và điều kiện |
| --- | --- |
| Early fusion | Chỉ dùng model có joint/compositional interface phù hợp đã đánh giá. CLIP paired encoders không tự cung cấp semantics chỉnh sửa bằng cộng vector |
| Late fusion | Kết hợp candidate/rank sau retrieval riêng; dễ thay encoder và đo ablation; có thể mất ảnh chỉ xuất hiện sâu ở một channel |
| Normalized score fusion | Cần normalization/calibration trên dev từng channel; min-max theo query có thể không ổn định khi outlier hoặc score range nhỏ |
| Rank fusion | Không cần cùng scale score; weighted RRF ban đầu; mất thông tin khoảng cách tuyệt đối giữa các scores |
| Constraint-aware reranking | Ưu tiên evidence/required clauses, có thể dùng reranker phù hợp; tốn inference và vẫn có unknown |

Đề xuất ban đầu weighted reciprocal rank fusion: `s(i) = Σ_m w_m / (60 + rank_m(i))`; missing channel đóng góp 0; weights không âm, tổng >0, chuẩn hóa tổng=1. Default text/image mỗi bên 0.5; cả hai phải >0 cho combined mode. Hằng 60 và weights là giả định dev, không benchmark optimum. Rank từng channel từ 1; UUID tie-break. Điểm fused được ghi `rrf`, không phải cosine/probability. Alternatives và weights chọn trên dev, final report dùng held-out queries. Rerank mặc định off.

## 7. Agentic multi-hop

AgentState gồm request/query ID, original query, index snapshot, plan steps, current hop, completed tool IDs, bindings entity từ bước trước, evidence refs, candidates, budget usage, deadline, errors/fallback và final resolution status. Không lưu chain-of-thought riêng tư; chỉ lưu kế hoạch/tool/evidence trace có thể kiểm tra.

| Tool | Typed input | Output / điều kiện |
| --- | --- | --- |
| `entity_lookup` | name, allowed entity type, locale | Candidates + provenance; ambiguous không tự chọn không có căn cứ |
| `get_related_entities` | entity_id, relation allowlist | Related entity IDs và relationship evidence |
| `semantic_image_search` | query, K, filters, pinned index | Core RetrievalBatch; cùng auth/deadline |
| `retrieve_image_metadata` | image_ids | Authorized metadata batch |
| `metadata_filter_search` | typed filter, bounded limit | Eligible IDs và structured evidence |
| `rerank_images` | candidate IDs, supported conditions | Versioned scores/assessments |

Ví dụ dependency: lookup Hoan Kiem Lake → relation located_in cho city → landmarks của city → ảnh landmarks. Không hardcode city vào kết quả hoặc xem đây là dữ liệu đã có. Nếu quan hệ không có evidence, kết thúc unresolved hoặc direct fallback có sự cho phép. Multi-intent parallel clauses không có output-binding dependency như vậy và không tính là multi-hop.

Defaults thiết kế: tối đa 3 hops phụ thuộc, 6 tool calls tổng (retries cũng tính), 512 output tokens, total deadline 5.000 ms; mục tiêu TTLast 3.000 ms vẫn riêng. Seed `entity_lookup` không tính hop; mỗi bước tiếp theo dùng binding của bước trước (relation traversal hoặc final retrieval) tăng hop một lần. Ví dụ lake → city → landmarks → image retrieval có 3 hops sau seed và 4 tool calls. Mỗi tool ≤ min(1.000 ms, remaining deadline); planner/generator chỉ dùng phần còn lại. Fallback default false; khi caller bật, workflow dành tối đa 1.000 ms cuối cho direct retrieval, không reset deadline và trả executed_mode/fallback_reason/unresolved_relations. Không có đủ thời gian thì 504, không bắt buộc fallback bằng mọi giá.

Initial Agent API synchronous JSON; TTFirst/TTLast lấy từ generator instrumentation nếu có, nếu không để null; không giả TTLast bằng full response. Streaming chưa nằm trong contract MVP; API trả 406 nếu yêu cầu SSE. Không phát token chưa qua grounding validation. Planner có thể là deterministic relational workflow; LLM planner chỉ optional, không bắt buộc cả agent tool execution.

## 8. Deployment và dependency validation

Local profile: UI/API trên host loopback, PG/Qdrant/MinIO private network và persisted volumes, worker cùng source image nhưng process riêng. Cấp encoder slot/device theo cấu hình; nếu dùng chung GPU phải có admission/serialization và worker không chiếm vô hạn tài nguyên search. Khi không đủ tài nguyên, giảm ingest concurrency hoặc pause indexing có theo dõi; không dùng benchmark idle để claim hiệu năng mixed workload.

Tài liệu lưu trữ tiếp theo phải cung cấp states, claims, versions, typed metadata, evidence relations và query/evaluation records cho các luồng này. API tiếp theo phải thể hiện multipart/JSON, scopes, async acceptance, partial timing, strict/best-effort semantics. Không có diagram nào được hiểu là container đã được deploy.

## Triển khai RAG Phase 08

RagService tùy chọn dùng lại SearchService, batch evidence từ PG/Qdrant/MinIO, context facts/provenance, Gemini native hoặc Chat Completions adapter, closed-ID citation validation và React explanation panel. Core path không gọi LLM, ảnh không gửi sang provider. Sơ đồ thành phần/sequence hiện hành tại [RAG_ARCHITECTURE](../../features/RAG_ARCHITECTURE.md); [nghiệm thu](../../archive/PHASE08_TEST_REPORT.md) ghi provider latency/browser gate còn mở. Không có Agent/multi-hop.
