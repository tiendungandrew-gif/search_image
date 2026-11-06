# API RAG — Prompt08

Base /api/v1, Bearer read token. LLM key chỉ backend. POST /search và /search/multimodal giữ nguyên contracts; explain.enabled cũ không âm thầm gọi LLM.

## POST /rag/explain

```json
{"query":"a cup of coffee","question":"Metadata ghi định dạng và kích thước như thế nào?","top_k":3,"search_mode":"semantic","language":"vi"}
```

Đây là input thật có thể chạy, không chứa kết quả/latency minh họa. Chọn đúng một operation: query, search (SearchRequest typed, gồm image_id/multimodal/filters/AST), hoặc image_ids. question tùy chọn, language auto/vi/en. top_k1–50; input text≤2000 ký tự, body≤64KiB. Existing IDs≤50/không trùng; expected_index_id chặn index drift. Metadata/score client cung cấp bị reject. max_evidence_items/max_context_tokens chỉ giảm tới server cap; context_policy rank hoặc descriptive_first.

Explain Existing dùng image_ids thật từ search response, expected_index_id hiện hành và question; score trả null vì operation này không tính lại retrieval score. Không giả score0 hoặc nhận score cũ từ browser như nguồn tin cậy.

RagResponse gồm query_id/request_id/operation/index_id/model_id/results, rag và latency. rag có answer/status/citations/evidence/language/generated/provider/model_id/revision/returned_model/prompt hash/context/usage/error_code/limitations. Citation có fact_id/image_id/evidence_field/quote/provenance/support_check. latency tách retrieval/evidence/context/generation/validation/provider TTFT/provider TTLast/TTLast từ request/total. Null là chưa đo hoặc không gọi model, không là0ms.

JSON200 có thể là insufficient_evidence hoặc generation_unavailable; ảnh vẫn được giữ khi generation lỗi. Input/auth/search errors dùng ErrorEnvelope401/409/422/503/504. Empty retrieval có results=[] và insufficient khi module sẵn sàng. Không tự fallback sang model khác khi model cấu hình lỗi.

## POST /rag/explain/stream

Cùng input, response text/event-stream. Events retrieval_started, retrieval_completed(results), generation_started, token(text/verified=false/kind=evidence_selection), generation_completed(full RagResponse), error(code). Không có token/generation_started nếu không gọi model. Generation failure có error và final response với status unavailable, không giả generation thành công. Failure trước/sau headers được phân biệt; lỗi sau headers là event error, không thể đổi HTTP status. Request disconnect đóng task và upstream stream. Streaming có thể tắt bằng operator config.

## Diagnostics

GET /rag/status trả enabled/configured/error_code/provider/model/streaming/grounding_policy. configured không bảo đảm provider hiện không bị outage/quota. GET /rag/samples là private bounded technical telemetry, không prompt/response/key. Không có endpoint Agent/Planner/Multi-hop ở Phase08.
