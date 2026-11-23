# Thiết kế công cụ Agent

Registry có đúng 9 tên allowlist, mỗi definition cung cấp JSON Schema input/output, capability, permission `search:read`, timeout và max_results. `GET /api/v1/search/agent/status` công bố contract thực tế; output là `ToolOutput` Pydantic, không phải text instruction.

| Tool | Input chính | Adapter/evidence | Hop cost |
| --- | --- | --- | --- |
| semantic_image_search | query, filters, entity_ids?, image_ids?, top_k | SearchService text/multi_intent, hard image-ID gate khi có entities | 1 |
| multimodal_image_search | query, image_id, filters, top_k | Engine multimodal Phase 06, dùng ảnh corpus được phép đọc | 1 |
| metadata_search | filters, top_k | PG predicate allowlist, EvidenceRetriever | 1 |
| entity_lookup | name, entity_type? | Canonical name/alias chính xác đã normalize | 0 |
| relationship_lookup | entity_ids, predicate, direction, type?, limit | Cạnh PG có nguồn và verified_at | 1 |
| get_related_entities | Như relationship_lookup | Traversal có hướng, trả entities và cạnh nguồn | 1 |
| retrieve_image_details | image_ids | Kiểm tra metadata/vector/object hiện có | 0 |
| rerank_images | query, image_ids, filters, top_k | Existing SearchService/reranker với ID restriction | 0 |
| rag_explain | image_ids | RagService/context/provider/citation validator Phase 08 | 0 |

Result ảnh tối đa 50; lookup/traversal tối đa 50 entities mỗi call; input IDs tối đa 1.000; output tối đa 256 KiB, giới hạn Pydantic bổ sung cho relations/associations. Thiếu danh sách IDs hợp lệ dừng dependency, không tự thay bằng entity khác. Điểm metadata có thể null; không tạo cosine score giả.

## Thực thi và bảo vệ

`StateReference` chỉ nhận `{step_id, field: entity_ids|image_ids}`. Validator kiểm tra producer, dependency khai báo và kiểu dữ liệu trước khi chạy bất kỳ bước nào. Executor resolve từ output đã hoàn tất, không string interpolation. Arguments unknown bị reject. Fingerprint tool + normalized arguments phát hiện call lặp, danh sách UUID dùng set đã sắp xếp cho fingerprint. Call count được trừ trước khi invoke, kể cả call thất bại.

Timeout thông thường 2 giây/call; `rag_explain` dùng RAG request timeout nhưng luôn bị cắt bởi deadline Agent còn lại. Timeout tạo structured code, cancellation nhả admission và dừng child task SSE. Output malformed/quá lớn bị loại; kết quả tool không được đọc như chỉ thị cho planner. Không có import, mutation, raw SQL, file path hoặc URL tool trong registry.

`TOOL_TIMEOUT`, `DEPENDENCY_UNAVAILABLE`, `INSUFFICIENT_EVIDENCE` là các nhóm public errors. Trace thực tế còn phân biệt `LOOP_DETECTED`, `TOOL_OUTPUT_LIMIT`, `TOOL_EXECUTION_FAILED`, `CONFLICTING_RELATIONSHIPS` và lỗi có kiểu của SearchService. Trace chỉ chứa tên bước/tool, status, duration, counts và evidence IDs, không raw arguments hoặc suy luận nội bộ.

## RAG và giới hạn thực tế

RAG là adapter tùy chọn; disabled/provider error giữ ảnh đã revalidate, status partial và warning. RAG giải thích từ caption/metadata ảnh, không được dùng model memory làm nguồn quan hệ. `relationship_summary` được ghép từ cạnh đã xác minh, tách khỏi answer do model sinh. Citation IDs phải thuộc final image set. Việc citation có ID đúng chỉ kiểm tra cấu trúc; faithfulness vẫn cần người đánh giá.

Không có engine embedding/retrieval thứ hai. Thay đổi core duy nhất phục vụ tools là `filters.image_ids`, áp dụng Qdrant HasIdCondition và PG recheck; CLIP/preprocessing hiện hành được giữ nguyên.

Ở lần hoàn thiện, image_id của SearchArgs dùng UUID thay vì string; tham chiếu sai bị reject trước invoke. Agent-to-RAG dùng `context_format=compact`: provider chỉ chọn fact IDs, còn full source provenance/UUID được giữ trong context server và citations. Không rút gọn schema validator hoặc bỏ hard image-association gate. Giao diện công bố nguồn quan hệ cho bộ NPS thật.
