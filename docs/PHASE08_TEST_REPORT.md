# Báo cáo triển khai và nghiệm thu Prompt08

Ngày thực hiện05/11/2026. RAG mở rộng retrieval hiện có, dùng Gemini API do người dùng chọn. Chưa triển khai Prompt09.

## A. Tóm tắt triển khai

Đã thêm optional RAG orchestration/evidence/context/LLM adapter/prompts/citation validation/API/SSE/React explanation panel/evaluation CLI. Giữ Fast Search và active CLIP, không tạo caption giả hoặc thay ranking để làm số đẹp.

## B. Tệp tạo và sửa

Các source chính: schemas/rag.py; services/rag/{evidence_retriever,context_builder,llm_provider,generator,citation_validator,rag_service}.py và4 prompt templates; api/v1/rag.py; evaluation/rag.py; cli/rag.py; unit/integration/browser RAG tests; frontend/src/features/rag/ExplanationPanel.tsx. Sửa config/main/router/middleware/health, SearchWorkspace/CSS, env.example và verifier; thêm7 tài liệu RAG. Danh sách source/hash và final checks được giữ trong verification/phase08 khi chốt.

## C. Kiến trúc

[RAG_ARCHITECTURE](RAG_ARCHITECTURE.md): actual SearchService → batch current evidence → context facts/provenance → Gemini selection → closed-ID validation → exact metadata quotes/citations. Existing IDs được revalidate, không tin metadata của browser. Không gửi ảnh nhị phân sang model.

## D. Evidence

Corpus10 ảnh thật vẫn có0 captions/0 tags. RAG giải thích format/dimensions/source có thật; câu hỏi về màu/đối tượng/cảnh phải báo chưa đủ evidence. Source provenance và validation được mô tả ở [triển khai](RAG_IMPLEMENTATION.md). Citation ID đúng không thành bằng chứng thị giác.

## E. Model/config

Gemini API native GenerateContent/streamGenerateContent (adapter compatible vẫn có), model gemini-3.5-flash-lite/reasoning minimal, temperature0,1, output128 tokens; context upper-bound2048/input4096, max5 images. Revision provider_managed/returned_model được ghi thật, không giả biết weights revision. Key giữ trong .env, hỗ trợ GEMINI_API_KEY, không frontend/Git/log. OpenAI/self-hosted adapter có contract/tests nhưng chưa gọi OpenAI thật khi chỉ có Gemini key.

Probe: model3.8 timeout,2.5 Flash-Lite404,3.5 Flash-Lite thực thành công; không silent model fallback trong request. Các model thử trước và lý do chọn được giữ trong verification. [Model khả dụng](verification/phase08/provider_discovery.json), [probes](verification/phase08/provider_model_probes.json).

## F. Prompt/grounding

[Prompt design](RAG_PROMPT_DESIGN.md): version/hash4 templates, question/evidence untrusted, no tools, model chỉ chọn facts. Server dựng câu theo quote; phần diễn giải tự do chưa hỗ trợ vì chưa có entailment verifier. Technical supported khác descriptive partially_supported; không dựa status tự khai của model.

## G. API và frontend

[RAG_API](RAG_API.md): JSON/SSE, search-and-explain và explain-existing; preservation khi provider lỗi; input/auth/limits/cancellation. React gọi API thật, optional button, loading/error/cancel, citations tới result-card; không tự gọi LLM mỗi search và không hiển thị token chưa validate như answer.

## H. Grounding evaluation

Citation ID/field/exact quote audits và injection/invalid-citation tests đã có. Answer relevance, visual faithfulness và unsupported semantic claim rate cần người đánh giá; không tự tạo labels hoặc dùng metadata-only mechanical checks thay human scores. Raw matrices đã có63/63 IDs và63/63 quotes đúng; không dùng số này làm faithfulness thị giác. [Raw results](../evaluation/reports/phase08_20261105/REPORT.md).

## I. Hiệu năng

| Protocol / cấu hình | Attempts / generated / unavailable | Client P90 ms | Provider TTFT P90 ms | TTLast P90 từ service ms |
| --- | --- | --- | --- | --- |
| [openai_compatible/R1](../evaluation/results/phase08/20261105T042632_rag_37780e9449/result.json) | 5 / 0 / 0 | 103.42 | — | — |
| [openai_compatible/R2](../evaluation/results/phase08/20261105T042632_rag_37780e9449/result.json) | 5 / 0 / 0 | 135.88 | — | — |
| [openai_compatible/R3](../evaluation/results/phase08/20261105T042632_rag_37780e9449/result.json) | 5 / 3 / 2 | 5261.02 | 4353.80 | 4699.60 |
| [openai_compatible/R4](../evaluation/results/phase08/20261105T042632_rag_37780e9449/result.json) | 5 / 0 / 5 | 5207.81 | — | — |
| [native/R1](../evaluation/results/phase08/20261105T050046_rag_4b6c513c95/result.json) | 5 / 0 / 0 | 87.14 | — | — |
| [native/R2](../evaluation/results/phase08/20261105T050046_rag_4b6c513c95/result.json) | 5 / 0 / 0 | 142.83 | — | — |
| [native/R3](../evaluation/results/phase08/20261105T050046_rag_4b6c513c95/result.json) | 5 / 5 / 0 | 2151.82 | 1845.20 | 2122.30 |
| [native/R4](../evaluation/results/phase08/20261105T050046_rag_4b6c513c95/result.json) | 5 / 5 / 0 | 3673.09 | 3448.03 | 3643.47 |

Hai lượt R1–R4 có40 API attempts:20 search/metadata-only,20 lượt yêu cầu generation. Compatible có7/10 generation unavailable do timeout; native có10/10 generation thành công/0 generation errors trong lượt benchmark sau. Không gộp hai điều kiện thành một SLA hoặc bỏ lượt thất bại.

Native R3 cap3: provider TTFT P90 **1.845,20ms**, TTLast từ service P90 **2.122,30ms**,5/5 completed. Native R4 cap1: TTFT P90 **3.448,03ms**, TTLast P90 **3.643,47ms**,5/5 completed. Có một R4 vượt3s; **không nghiệm thu mục tiêu3s cho toàn RAG workload**. VớiN5/cấu hình, nearest-rank P90/P95 là maximum; không là production confidence hoặc robust context-selection improvement. Context lớn không tự động chậm hơn/context nhỏ không tự động tốt hơn. Model/protocol/retry/time window khác nhau; không kết luận native gây ra toàn bộ cải thiện latency.

Các mốc retrieval/evidence/context/generation/total đo từ RagService sau request validation tới trước serialize; client_total_ms bao phủ HTTP response hoàn chỉnh. provider TTFT/TTLast chỉ đo khi stream thực; nonstream/không gọi model đểnull. TTLast từ service tổng hợp các elapsed spans của cùng request, không cộng component percentiles. Cache/provider network không kiểm soát, model remote hardware không biết.

Fast Search sau tích hợp RAG: [20261105T043305_benchmark_38092a56a4](../evaluation/results/phase08/20261105T043305_benchmark_38092a56a4/result.json), **500/500 success,0 lỗi**, full-server P50106.02ms/P90144.59ms/P95153.17ms;8.64success/s, C1/K10/candidate50/CLIP512 CPU4threads/10 ảnh. Mục tiêu Fast P90≤300/P95≤500 đạt trong điều kiện đã đo, không là capacity/production claim. Không gọi Gemini ở các search requests này.

Trên13 responses generation hợp lệ từ hai matrices: **63/63 citation IDs hợp lệ, 63/63 exact quotes khớp evidence**. Đây là mechanical citation/extraction audit, không visual faithfulness/answer relevance. Semantic unsupported-claim rate chưa có human judgments. Denominator0 ở các case unavailable được đểnull, không nhận100% giả.

Các fallback thực native: RAG_DISABLED, LLM_CONNECTION_FAILED và LLM_TIMEOUT đều giữ ảnh, không citations/answer bịa, original config được khôi phục. [Artifacts](verification/phase08/fallback_cases.json). Captions/tags vẫn0/10; câu hỏi visual không gọi model khi thiếu facts.

[Report JSON/CSV/Markdown](../evaluation/reports/phase08_20261105/REPORT.md), [per-case CSV](../evaluation/reports/phase08_20261105/rag_cases.csv), [RAG latency PNG](../evaluation/reports/phase08_20261105/rag_latency.png), [Fast latency PNG](../evaluation/reports/phase08_20261105/latency.png). BảnSVG cùng thư mục, tất cả từ actual measurements. Hai report renders cũ được giữ, bản bàn giao dùng thư mục có ngày.


## J. Tests

- Backend **144 passed** trong lượt full backend cuối:135 unit +9 integration thật; [log](verification/phase08/backend_tests.txt), [summary](verification/phase08/backend_tests.json). Hai native RAG tests chạy riêng cũng **2 passed**; [log](verification/phase08/isolated_native_tests.txt).
- Source unit chốt **135 passed** sau cập nhật templates/schema/report. Python Ruff/format và shell syntax qua. Không dùng provider doubles làm bằng chứng LLM generation thật.
- Frontend **10 unit passed**, TypeScript/ESLint/Vite build qua. [Log](verification/phase08/frontend_checks.txt).
- Full browser cuối **15 passed,1 failed**;14 base/advanced/annotation cases và một RAG viewport pass, một RAG viewport gặp LLM_TIMEOUT. [Log](verification/phase08/browser.txt). Targeted RAG rerun **1 passed,1 failed** do timeout provider; [log](verification/phase08/browser_rag_final.txt). Cả desktop/mobile đã hiển thị answer thật ở các lượt khác nhau nhưng không có tuyên bố latest full-run16/16.
- Fault injection thực3/3 qua: module off, refused local endpoint và deadline0,1s với real Gemini endpoint; [JSON](verification/phase08/fallback_cases.json). API images được giữ, no fabricated answer. Native stream/JSON và citation references có success thật trong integration/benchmarks; request cancellation có unit test đóng upstream và trả admission slot.
- Metric/context/labels/schema/injection/empty/missing/duplicate/provider-error/retry/timeout/closed-citation tests dùng isolated fixtures được ghi rõ. Human-review fixtures không trở thành nhãn cho actual corpus. Có raw LLM/model probes/failure histories; không sửa assertion hoặc bật test retries để che outage.

**Trạng thái nghiệm thu còn mở:** một browser happy-path assertion phụ thuộc provider còn thất bại ở lượt cuối; RAG3s không đạt mọi case và semantic quality cần human review. Không ghi toàn Phase08 pass khi các gates này chưa đóng.

## K. Giới hạn và vấn đề còn mở

Không có caption/tag hoặc human qrels, chưa kiểm visual faithfulness/answer relevance trên corpus đại diện. Model-managed weights revision/remote hardware không được công bố cho lượt này; Gemini/network latency biến động, output có thể bị reject hoặc timeout. RAG chỉ trích facts, chưa free-form synthesis/vision verification. Streaming raw fact-selection deltas phải được coi chưa verified. Không có căn cứ claim OpenAI đã tích hợp thật từ Gemini tests. Những gates chưa xác minh phải giữ mở.

## L. Sẵn sàng Prompt09

Đã có typed RAG service/evidence/citations/status/deadlines cho integration tương lai. Planner/tool calling/multi-hop/state/evidence aggregation chưa triển khai. Cần bổ sung chất lượng evidence/nhãn, policies và sustained provider reliability trước Agentic workflows. Dừng ở Prompt08.

Lịch sử kiểm thử được giữ: lượt đầu3 failures (một unit fixture chịu ảnh hưởng RAG_ENABLED môi trường và hai Gemini timeout), lượt sau141 pass/16 browser pass, lượt compatible chốt sau đó có2 timeout/141 pass. Unit fixture đã cô lập rag_enabled=false, không đổi assertions để che provider failure. Native adapter được bổ sung và nghiệm thu riêng; không lấy JSON pass cũ cho lần chạy fail.

Nghiệm thu native đã có144 backend tests pass; browser từng có16/16 pass ở lượt compatible, nhưng lượt native cuối hiện15/16 do một LLM_TIMEOUT. Không đổi assertion để giấu outage; logs các lượt được giữ. Không có căn cứ kết luận đổi protocol khắc phục hoàn toàn provider latency.

## Checklist bàn giao

- [x] RAG optional, SearchService/index baseline/ranking được giữ.
- [x] Evidence hiện hành và provenance, context bounded/dedup/field selection.
- [x] Gemini native thật + adapter Chat Completions cấu hình được; không trộn key/endpoints.
- [x] JSON/SSE thực, citation validation và giao diện explanation/citation links.
- [x] Disabled/provider failure/timeout/cancellation không làm mất ảnh đã tìm.
- [x] Unit/integration/static/build và Fast Search500-request regression đã chạy.
- [x] R1–R4, raw failures, JSON/CSV/Markdown/PNG/SVG và CLI human review.
- [ ] Browser RAG pass ổn định cho cả hai viewports trong cùng lượt với provider.
- [ ] Mục tiêu3s trên workload đại diện, thay vì chỉ một subset/single successful call.
- [ ] Human answer-relevance/faithfulness/unsupported-claim review và corpus mô tả đủ tốt.

Đã bàn giao triển khai Prompt08; **chưa đánh dấu nghiệm thu toàn bộ**. Không bắt đầu Prompt09. Provider jitter và data/label gaps được giữ như vấn đề mở, không được thay bằng success giả.

[Kiểm tra bàn giao cuối](verification/phase08/final_checks.json), [source thay đổi](verification/phase08/source_changes.json), [source snapshot/archive](verification/phase08/source_snapshot.json). Có22 source/config files thêm,14 files sửa,không xóa;216 source/config files được fingerprint. CLIP encoder/ingestion decoder giữ nguyên,32 experiments Phase07 và7.360 old benchmark attempts được giữ. Secrets scan không có private matches, .env0600 và private env không nằm trong source archives. Seven required docs/relative links/JSON/examples/traceability/structural diagrams đã qua. Không tạo Git commit; source hashes/archives là provenance fallback.
