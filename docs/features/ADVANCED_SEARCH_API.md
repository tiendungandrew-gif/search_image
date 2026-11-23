# Advanced Search API — Prompt 06

Base `/api/v1`, Bearer read/operator token, common ErrorEnvelope và request IDs giữ nguyên. Prompt05 text/image clients tiếp tục hoạt động. Search không persist history/query image hoặc yêu cầu idempotency key. [SEARCH_API](SEARCH_API.md) giữ chi tiết baseline; tài liệu này là phần mở rộng hiện hành.

## Endpoints và requests

`POST /search`: JSON text/existing image_id hoặc image-only multipart. Text+image kết hợp phải dùng `/search/multimodal`, gửi qua core bị422. Modes canonical auto/text/image/multi_intent, agent vẫn409. Legacy search_mode semantic→text, image_similarity→image; thêm auto/multi_intent/multimodal/text/image. query alias text không được gửi đồng thời. Boolean rerank alias thành `{enabled:boolean}`; canonical object vẫn giữ on_failure:error|skip, candidate_limit và timeout_ms. Explain/RAG/agent chưa bật.

```json
{"query":"coffee and a brown cat","search_mode":"multi_intent","top_k":10,"rerank":{"enabled":true,"on_failure":"skip"}}
```

`POST /search/multimodal`: hỗ trợ text-only, image-only giữ compatibility Prompt05, hoặc paired text+image. JSON khi dùng existing image_id; multipart khi có upload. Tối thiểu một input, không đồng thời file và image_id; explicit mode phải khớp input. auto tự chọn text/image/paired hoặc supported multi-intent; không chọn agent. File validation/bounds/proxy access như Prompt05.

Multipart canonical: image file(optional nếu có text), options JSON SearchRequest. Flat aliases: query/text, top_k, search_mode, fusion_strategy, text_weight, image_weight, rerank(JSON boolean). Không trộn options với flat fields, không duplicate/unknown field, tối đa1 file/12 fields; malformed boolean/numeric/JSON trả422.

```text
image: <JPEG/PNG/WebP bytes>
options: {"text":"similar scene but red","mode":"multimodal","top_k":10,"fusion":{"method":"rrf","text_weight":0.4,"image_weight":0.6},"rerank":{"enabled":true,"on_failure":"skip"}}
```

Fusion method rrf/weighted_rrf/weighted_score, k1…1.000(default60), weights[0,1] tổng>0 được normalize. Flat fusion_strategy/text_weight/image_weight là aliases không được trộn fusion object. Fusion dùng cho advanced paths; explicit basic text/image vẫn cosine và không fan-out vì thêm options không cần thiết.

Top-K default10/runtime1…50(config≤100), candidate_count≥K≤1.000. Server channel cap4/tổng requested candidates≤1.000, advanced union cap100(default). rerank request candidate_limit1…100≤server limit(default50),≥K; timeout_ms1…1.000(default200). Rerank off/request default; lỗi theo on_failure(error/skip); omit là legacy OptionalFeature value được parse nhưng reranker chỉ coi skip là fallback. Paired search chỉ nhận retrieval_strategy=fused; text experiments nhận whole_query/multi_query/fused.

## Constraints

Canonical group/semantic/metadata leaf trong OpenAPI; tối đa8 leaves/depth2, unique IDs; `whole`/`image` là IDs dành cho nhánh nội bộ, không được dùng làm clause ID. Metadata filters giữ schema Prompt05, unknown fields/category hoặc metadata expression vượt bounds bị422. Leaf thêm negated(defaultfalse) và weight(default1,>0≤10). Explicit AST là authoritative conditions, text giữ retrieval context.

```json
{"text":"a cup of coffee","constraints":{"op":"and","clauses":[{"id":"dimensions","kind":"metadata","filter":{"min_width":500},"required":true},{"id":"preference","kind":"semantic","text":"warm light","required":false,"weight":0.5}]},"rerank":true,"top_k":5}
```

Required metadata mismatches bị hard-gate theo AST AND/OR, missing fields UNKNOWN. Best effort giữ unknown và cảnh báo; require_verified=true loại required metadata unknown, required semantic leaf→409 VERIFIER_UNAVAILABLE. Không nới điều kiện khi fallback. [MULTI_INTENT_SEARCH](MULTI_INTENT_SEARCH.md) định nghĩa tri-state, optional projection và negation.

## Responses và telemetry

SearchResponse giữ query/request/model/index IDs, results, total_results, effective_settings, latency.processing_ms/latency_ms alias, server_response_ms=null trước final send. search_mode mở rộng text/image/multi_intent/multimodal; service_class fast|advanced. QueryAnalysis trả original_query, language heuristic, classification, AST/limitations/uncertain và strategy; không claim parser hiểu mọi ngữ pháp.

Result giữ canonical constraint_assessments(clause_id,status:satisfied|violated|unknown,evidence_ref), thêm evidence_kind/semantic_score(nullable)/required/negated. Compatibility constraint_evidence dùng uppercase statuses VERIFIED_MATCH/VERIFIED_MISMATCH/UNKNOWN. score_type cosine|rrf|weighted_score|reranker đi với ranking_version, contributing_branches và score_components. Không dùng cosine cao làm VERIFIED_MATCH semantic.

Effective settings gồm route, channels, vector_calls(query_points), vector_fetch_calls(stored candidate vector reads), candidate count/pool cap, normalized fusion_weights, method/k, rerank_applied, constraints mode, truncation. Full ASGI metrics vẫn ghi sau final send vào bounded ring theo request_id; thêm route/vector_calls/rerank_applied, không text/images/credentials. Query analysis chỉ trả requester, không ghi vào logs/metrics.

Health capabilities multimodal/multi_intent/rerank phản ánh loaded search runtime và server flags; explanations/agent vẫnfalse. `/health?check=search` kiểm required stores/active index/encoder như trước.

## Errors

401 auth;409 FEATURE_DISABLED/VERIFIER_UNAVAILABLE/UNSUPPORTED_RELATIONAL_QUERY/MODEL_INDEX_MISMATCH;413 body/file cap;415 format;422 INVALID_INPUT/CONSTRAINT_LIMIT/TEXT_TOKEN_LIMIT/CORRUPT_IMAGE;503 NOT_READY/DEPENDENCY_UNAVAILABLE/RERANK_FAILED/INFERENCE_BUSY;504 full request/vector deadline. Rerank budget timeout theo policy error→503 hoặc skip→200+warning, không được giấu. Empty eligible set là200/results=[], không thay thế dependency error.

Swagger tại `http://localhost:8000/docs` gồm schema recursive AST và JSON/multipart requestBody. CLI benchmark/evaluation và actual execution evidence tại [ADVANCED_SEARCH_TEST_REPORT](../archive/ADVANCED_SEARCH_TEST_REPORT.md).
