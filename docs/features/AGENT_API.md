# Agent API và frontend — hợp đồng runtime Phase 09

Base `/api/v1`; Bearer read token với `search:read`. OpenAPI `/openapi.json` và `schemas/agent.py` là schema thực thi đầy đủ. Document này thay phần Agent reserved của thiết kế Phase 02: có JSON endpoint và SSE endpoint riêng, hỗ trợ alias tương thích và response Agent riêng ở root, không bọc trong SearchResponse.agent.

## Endpoints

| Method/path | Ý nghĩa |
| --- | --- |
| POST /search/agent | AgentRequest → AgentResponse JSON |
| POST /search/agent/stream | Cùng request, `text/event-stream` |
| GET /search/agent/status | Enabled/initialized, caps, dataset state, 9 tool schemas |
| GET /search/agent/samples | Bounded execution/complete HTTP metrics, không query text |

Feature disabled trả409; JSON input lỗi422, auth401/403, body quá lớn413, admission đầy429 ở JSON endpoint. Sau khi SSE headers đã gửi, lỗi trả `error` event và không đổi HTTP status. Request hợp lệ nhưng thiếu evidence hoặc execution failed/timeout trả200 với structured status; client phải đọc status, không dùng HTTP200 làm query success.

## AgentRequest

| Field | Kiểu, default, ràng buộc |
| --- | --- |
| query / text | Đúng một field; normalize trim/NFC, 1…2.000 chars |
| mode | agent(default), auto, text, multi_intent, multimodal, metadata, explain |
| search_mode | Alias legacy chỉ `agent`, không kết hợp mode khác agent |
| top_k | Integer 1…50, default10 |
| image_id | Stored UUID cho multimodal; không URL/path/file upload ở route này |
| image_ids | 1…50 stored UUIDs, bắt buộc khi mode explain |
| filters | FilterSpec hiện có và image_ids UUID restriction tối đa1.000 |
| max_hops | Alias 1…3, clamp budgets.max_hops |
| budgets | max_hops=3, max_tool_calls=6, max_output_tokens=512, deadline_ms=15000 |
| include_explanation | Boolean defaultfalse |
| explain | Alias `{enabled,on_failure}` hiện có; enabled map sang include_explanation |
| allow_fallback | Boolean defaultfalse; chỉ fallback planning deterministic khi có ý nghĩa |
| language | auto(default), vi, en |
| planning_mode | deterministic hoặc llm; null lấy server default |
| rerank | Boolean defaultfalse |

Unknown fields bị reject. Limits là min(request,server), không cho client tăng call/hop/deadline server. `explain.on_failure` được chấp nhận để tương thích schema cũ; Agent luôn giữ ảnh và warning khi generation thất bại. Mode explain tự bật include_explanation. Không có LLM/key/model tùy ý từ request. Query multimodal chỉ dùng image_id đã có; UI Agent hiện chỉ nhập text, API hỗ trợ stored-image multimodal.

```json
{
  "query": "Find landmarks in the city where Hoan Kiem Lake is located",
  "top_k": 5,
  "search_mode": "agent",
  "max_hops": 3,
  "include_explanation": false
}
```

Với serving KB trống, ví dụ này trả `insufficient_evidence`, không có ảnh, không tự tạo facts về Hà Nội. Query “a dog outdoors” trả ảnh hiện có bằng semantic tool, không dùng planner LLM.

## AgentResponse

| Nhóm fields | Nội dung |
| --- | --- |
| Identity | query_id, request_id, execution_id, plan_id; index_id/model_id/manifest_sha256 nullable khi chưa runtime |
| Routing | requested_mode, search_mode, service_class fast/augmented |
| Outcome | status, query_success, dataset_status, verification_state, error_code, warnings |
| Images | results: RagImage[] (UUID, rank, nullable score/type, metadata, relative authenticated URLs) |
| Knowledge | resolved_entities, evidence, image_associations, image_sources, relationship_summary |
| Execution | steps: step_id/tool/status/duration_ms/logical_hop/result_count/error_code/evidence_ids; logical_hops, tool_calls |
| Planner | planner_mode, planner_attempts, plan_validated, planner_version, planner_usage, planner_model_id, planner_prompt_sha256, planner_trace |
| Explanation | answer nullable; rag nullable với generated/citations/error_code theo Phase 08 |
| Timing | latency_ms và latency: routing/planning/tools/aggregation/total_ms, provider_ttft/provider_ttlast/request_ttlast_ms nullable |

`dataset_status`: available, empty_dataset, search_unavailable, unknown. `verification_state=VERIFIED_WITH_REAL_DATA` chỉ xác nhận kết quả ảnh đến từ stores thật; không là chứng nhận relevance hoặc độ đúng câu trả lời. Fixture response có TESTED_WITH_MOCKS để tránh nhận nhầm knowledge hư cấu thành dữ liệu thật. `query_success` là success cấu trúc; muốn đo chất lượng cần labels riêng.

## SSE và UI

Public events: planning_started, planning_completed, tool_started, tool_completed, retrieval_completed, generation_started; token được adapter RAG forward khi có, terminal `agent_completed` hoặc `agent_partial`, và `error`. Event name không đảm bảo query success: kiểm tra terminal payload. Không gửi plan arguments, prompt hoặc private reasoning.

React có mode Agent, chọn deterministic/LLM, optional explanation, cancel và tiến độ thực tế; không vẽ các bước chưa chạy. Parser xử lý UTF-8/CRLF chia chunk, giới hạn2MiB, từ chối stream bị cắt khi chưa có terminal payload. Tokens chưa kiểm tra citation không được render; chỉ answer final được hiển thị. Ảnh tải qua content proxy có auth, không nhúng token vào URL. Empty/partial/timeout có thông báo riêng, các mode tìm kiếm khác vẫn hoạt động.

## Bổ sung dữ liệu và trace

Planner version `agent-template-plan-v2`; planner_trace chứa tối đa2 attempt có status/error_code/duration_ms/input_bytes. Public operational samples ghi plan_id và trace này khi AGENT_LOG_TRACE bật. Error codes chỉ là nhóm lỗi đã sanitize. UI có “Nguồn quan hệ” với source URLs đã verified; chỉ HTTPS không userinfo được mở bằng link, schemes khác hiển thị text. Dữ liệu NPS được kiểm chứng bằng query Washington Monument theo [PUBLIC_LANDMARK_DATASET](../research/PUBLIC_LANDMARK_DATASET.md). Fixture source/flags không được nhập vào serving DB.
