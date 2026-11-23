# Báo cáo nghiệm thu Prompt 09 — lần hoàn thiện

> Tài liệu lịch sử theo phase; lệnh trong nội dung giữ tên đường dẫn cũ. Hướng dẫn hiện hành tại [danh mục tài liệu](../README.md) và [scripts](../../scripts/README.md).

Chốt báo cáo ngày 07/11/2026; các số đo ngày 06/11/2026. Đã hoàn thiện phần mềm, dữ liệu công khai nhỏ có nguồn và kiểm chứng workflow thật của Phase 09. **Human relevance/faithfulness vẫn chờ theo lựa chọn của người dùng; không tự gán nhãn.** Phạm vi dừng ở Prompt 09. [Snapshot báo cáo ban đầu](../verification/phase09/PHASE09_TEST_REPORT_initial.txt) và toàn bộ raw lỗi cũ giữ nguyên.

## A. Tổng hợp hiện thực

Agent optional có router, structured planner,9 tools, validated DAG, bounded executor, isolated state, knowledge repository/import, evidence aggregation, optional RAG, JSON/SSE và React. Fast Search độc lập với LLM. Lần hoàn thiện bổ sung real NPS corpus/facts, per-attempt planner tracing, prompt compaction, benchmark pacing, xử lý quota và giữ images qua SSE RAG failure.

| Năng lực | Trạng thái và bằng chứng |
| --- | --- |
| Framework, APIs, UI, CLI import/download | IMPLEMENTED và kiểm thử |
| Invalid plan/tool/ref, loops, timeout, cancel, admission, provider errors | TESTED_WITH_MOCKS; doubles không là actual-provider accuracy |
| PG/Qdrant/MinIO/CLIP và corpus 513 ảnh | VERIFIED_WITH_REAL_DATA về hạ tầng/execution |
| NPS real facts/photos, EN/VI/alias/missing/filter workflows | VERIFIED_WITH_REAL_DATA theo source/receipt, không là human relevance |
| Gemini planner và optional RAG có citations | VERIFIED_WITH_REAL_DATA về tích hợp/thời gian quan sát |
| Recall@10/nDCG/faithfulness/unsupported-claim rate | NOT_VERIFIED, chờ người đánh giá |

## B. Files tạo mới hoặc sửa

Source bắt đầu lần hoàn thiện:247 files. Bản hiện tại có253 files; 28 files cũ thay đổi, 6 files mới, không xóa baseline. [Danh sách đầy đủ và source archive](../verification/phase09_completion_20261106/source_changes.json). Những sửa Prompt08 đã có sẵn được giữ nguyên.

Các thay đổi chính: agent schemas/state/planner/service/response/API metrics; RAG context_format và provider429 policy; evaluation/agent và CLI pacing; typed UUID tool arguments; knowledge import/revalidation guards; CLI download_landmarks/prepare_landmark_knowledge; scripts/verify_public_agent; frontend Agent source links/quota/partial SSE; tests; NPS catalog/import receipts; tài liệu và ignore raw dataset. Không đổi ClipEncoder, ingestion/query decoders hoặc hai package lockfiles; [audit](../verification/phase09_completion_20261106/final_audit.json). Không commit/push tự động.

## C. Kiến trúc Agent

Explicit Agent → finite VI/EN router → deterministic hoặc JSON LLM planner → validate toàn DAG/tools/refs/budgets → execute → revalidate evidence → optional RagService → response. Chọn custom asyncio/Pydantic state machine; không thêm dependency hoặc service. LLM hiện là constrained template planner, không hiểu tùy ý mọi natural-language relation. [AGENT_ARCHITECTURE](../features/AGENT_ARCHITECTURE.md).

## D. Tool Registry

9 read-only tools: semantic_image_search, multimodal_image_search, metadata_search, entity_lookup, relationship_lookup, get_related_entities, retrieve_image_details, rerank_images, rag_explain. Input/output schemas, capability, permission và caps được công bố ở status. Không shell, SQL tùy ý, URL fetch hoặc mutation trong Agent. Downloader/import là CLI quản trị sau lựa chọn nguồn công khai của người dùng. [AGENT_TOOL_DESIGN](../features/AGENT_TOOL_DESIGN.md).

## E. Multi-hop đã kiểm chứng

Washington Monument → located_in Washington, D.C. → inverse located_in lấy ba landmarks → semantic search với verified image-ID gate.4 calls,3 logical hops,3 ảnh thật. Query tiếng Việt và alias Jefferson Memorial đã qua. [Raw public workflow](../verification/phase09_completion_20261106/public_final/result.json), [labels nguồn chuẩn bị trước query](../verification/phase09_completion_20261106/public_final/expected_labels.json).

Ba case có exact-ID workflow metrics3/3, classification source_verified_workflow và real_world_retrieval_accuracy=null. Đây là kiểm tra query/dataflow/storage identities trên tập nhỏ có nguồn, không là semantic accuracy tổng quát. Fixture hư cấu vẫn chỉ ở DB/bucket/collection test riêng và không được nhập vào serving DB. [MULTI_HOP_SEARCH](../features/MULTI_HOP_SEARCH.md).

## F. Knowledge Base và dữ liệu

Hiện513 ảnh,503 captions,4 entities,3 relationships,3 verified image links. Ba JPEG NPS có credit/rights/source URL và SHA-256; city facts từ trang NPS. [PUBLIC_LANDMARK_DATASET](../research/PUBLIC_LANDMARK_DATASET.md) ghi nguồn/giấy phép và giới hạn, [manifest](../verification/phase09_completion_20261106/public_download_manifest.json) ghi ảnh/source-page checksums. Không lấy facts từ LLM memory.

Index `b4597021-4b91-491d-99ae-0617a6ca389c` active generation 3,513 ready/vector receipts. Index510 ảnh generation 2 và baseline10 ảnh còn nguyên. Model `02593ce4-5531-49eb-8b46-89e6ecaef50c`/CLIP512/pinned manifest giữ nguyên. Schema16 bảng, migration20261106_agent_knowledge không thêm dữ liệu giả. [KNOWLEDGE_BASE_DESIGN](../features/KNOWLEDGE_BASE_DESIGN.md).

Wikimedia trả403/429 nên không bypass; bộ thật đầu tiên dùng NPS. Hồ Hoàn Kiếm chưa có trong kho và tiếp tục trả thiếu evidence. Không suy coverage địa lý rộng từ ba landmarks Washington, D.C.

## G. State và lỗi

State riêng request: planned → running → completed/partial/insufficient_evidence/timeout/failed/cancelled.3 hops/6 calls/1 replan,15s overall,2s tool,4s planning attempt, concurrency2. Không long-term memory/checkpoint. Provider auth/config/quota không retry/replan ngay. planner_trace ghi duration/status/error/input bytes cho từng attempt, gồm attempt timeout đã phục hồi; không raw prompt/private reasoning. [AGENT_STATE_MANAGEMENT](../features/AGENT_STATE_MANAGEMENT.md).

## H. Evidence và provenance

Dedup stable IDs, giữ thứ tự ranking, revalidate PG facts/provenance/timestamp/image links và current images/vectors/objects. Relational results bắt buộc verified association tới target entities. Similarity không chứng minh located_in. Fixture source flags/prefix bị loại trong import và normal reads; stale/fabricated IDs bị reject. relationship_summary chỉ render cạnh thật có nguồn. [Raw response cuối](../verification/phase09_completion_20261106/public_final_response.json).

## I. RAG và tối ưu

Reuse Phase08 provider/context/citation validator. Compact format chỉ gửi fact_id/field/quote, giữ full UUID/provenance trên server; exact citations vẫn map về ảnh hiện có. Planner v2 bỏ lặp full JSON schemas trong prompt, giữ full validation server. Lượt paced A4 generated10/10, có citations10/10. Chưa có human semantic-quality score.

429 được giữ thành structured failure/partial, không tự retry tức thì. SSE RAG error có retrieval_preserved được đọc tiếp tới terminal partial, thay vì ném mất ảnh. Fatal Agent error và truncated stream vẫn reject. Unit và browser có ca riêng cho cảnh báo quota với real public images.

## J. API và frontend

POST /api/v1/search/agent JSON, /stream SSE, GET /status,/samples; read auth, strict request aliases/budgets, separate query_success và status. Public technical traces không có credentials hoặc private reasoning. React có Agent/planner/explanation/cancel/progress, images, source links và empty/partial/timeout/quota states. Quota được phân biệt với missing knowledge; chọn “Theo mẫu đã hỗ trợ” để chạy relation workflow không cần LLM. [AGENT_API](../features/AGENT_API.md).

## K. Empty Dataset Mode

Full integration suite tạo PG DB sau migration, Qdrant512-cosine collection trống và MinIO bucket trống; app/registry9 tools khởi tạo, plan validate, results rỗng/insufficient_evidence và không tạo facts. Sau đó dùng CLIP/ảnh thật cùng fixture hư cấu để kiểm tra dependent IDs. Không xóa serving dataset để test empty mode. Temporary namespaces được dọn; audit không còn agent_test DB/collection. Empty UI dùng SSE mock, được ghi rõ là mock.

## L. Hiệu năng thực đo

Fast Search500/500 không lỗi: complete-server P90 **132.01ms**, P95 **137.41ms**. Target 300ms quan sát đạt trên513 ảnh local.

| Nhóm paced | N | Planning P90 ms | Tools P90 ms | Mean hops/calls | Client P90 ms | Failed/partial/HTTP lỗi |
| --- | --- | --- | --- | --- | --- | --- |
| A1 | 10 | — | — | 0.0/0.0 | 91.46 | 0/0/0 |
| A2 | 10 | 0.53 | 122.03 | 3.0/4.0 | 256.56 | 0/0/0 |
| A3 | 10 | 2225.08 | 131.51 | 3.0/4.0 | 2480.18 | 0/0/0 |
| A4 | 10 | 0.18 | 1684.65 | 1.0/2.0 | 1858.18 | 0/0/0 |

A4 Agent-request TTLast P90 **1730.99ms**, provider TTFT P90 1446.17ms; 10/10 generated samples đạt3s, không missing timing. Paced40 requests có0 execution/partial/HTTP failures. Không suy SLA mọi workload từ N=10 mỗi nhóm.

Burst40 trước đó có2 planning failures và2 RAG partial do quota; giữ nguyên raw. Pacing5s là offered-rate control riêng, không tính vào request latency và có elapsed total trong metadata. Không dùng timeout hoặc xóa failures để đạt target. [AGENT_PERFORMANCE](../research/AGENT_PERFORMANCE.md), [CSV/PNG/SVG](../../evaluation/reports/phase09_completion_20261106_final/REPORT.md).

## M. Kiểm thử và bảo toàn

| Nhóm | Kết quả / bằng chứng |
| --- | --- |
| Backend |200 passed:188 unit và12 integration; [log](../verification/phase09_completion_20261106/final/backend_tests.txt) |
| Frontend hiện tại |21 unit, typecheck/lint/Vite build qua; [log](../verification/phase09_completion_20261106/frontend_checks_current.txt) |
| Browser full |24 passed trước bổ sung nhánh quota; [log](../verification/phase09_completion_20261106/full/browser.txt) |
| Browser nhánh cuối |6 desktop/mobile cases public/empty/quota, gồm2 quota mocks với ảnh thật; [log](../verification/phase09_completion_20261106/browser_sse_final.txt) |
| Public source verification |3 labelled workflow cases và missing/filter/LLM/RAG cases; source-verified, không human relevance |
| Mock errors |Plan invalid/ref/cycle/loop, timeouts/cancel, concurrency, auth/quota no retry, partial/fatal/truncated SSE |
| Data/source/security |513/510/10 receipts,4/3/3 knowledge, no fixture leaks; protected encoders/locks unchanged; no actual-secret matches |

Các logs failed run cũ ở verification/phase09 và raw burst quota vẫn giữ nguyên; không gộp counts của repeat runs thành unique tests. Static checks không còn lỗi chưa xử lý. Warnings private-network Qdrant HTTP và Node color flags nằm log, không là test failures. [Audit và source snapshot](../verification/phase09_completion_20261106/final_audit.json).

Benchmark paced source `c23876c8b1bf9cf54ee299e268ff412eddae0af0c8e21c8008a7067acce4f32d`; SSE client được sửa sau measurement, không đổi backend/engine đo latency. Source cuối `66ffd026326c79dc9c2c82018df37bb5aca9d671a0797d582761e05f0ddf187e`; audit đối chiếu backend source của measurement với code hiện tại.

## N. Checklist và giới hạn

- [x] Agent optional, core Search/RAG/advanced services được reuse.
- [x] Typed plans/tools/refs, limits, loops, timeout/cancel/admission và tracing.
- [x] Empty services, missing/conflicting knowledge và provider disabled/unavailable/quota.
- [x] Knowledge thật có nguồn và images thật; source/import validation và data versioning.
- [x] Multi-hop Anh/Việt/alias, public sources trong UI, optional real Gemini/RAG.
- [x] Test/static/build, source/data preservation, raw experiments và reports.
- [x] Fast P90≤300ms và RAG TTLast≤3s quan sát đạt trên workload paced đã đo.
- [ ] Human relevance/faithfulness/unsupported-claim labels; vẫn chờ theo lựa chọn người dùng.
- [ ] Quality trên nhiều city/domain, workload lớn/concurrency cao và SLA dài hạn chưa xác minh.

Finite grammar và LLM template guard là giới hạn có chủ đích. External connector chỉ là bounded NPS administrative CLI; không crawling tùy ý trong Agent. Import CLI chưa có CRUD/revision workflow; durable memory/tenant/public hardening không thuộc phần hiện thực này. Không tuyên bố fully verified real-world quality từ ba ảnh hoặc các fixtures.

## O. Sẵn sàng Prompt 10

Phần mềm và real workflow của Prompt 09 đã sẵn để phát triển end-to-end UX khi người dùng yêu cầu Prompt 10. Thử tại http://localhost:5173 → Agent → Washington Monument relational query. Nếu LLM quota, dùng planner theo mẫu hoặc tắt explanation; vẫn giữ retrieval/facts có nguồn. Muốn nghiệm thu chất lượng cần người đánh giá hoàn tất labels đã hoãn, không cần thêm kiến trúc để nạp dữ liệu thật.

**Dừng ở Prompt 09; không tự triển khai Prompt 10.**
