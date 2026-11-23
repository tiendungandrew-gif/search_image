# Báo cáo nghiệm thu Prompt10 — A–P

> Tài liệu lịch sử theo phase; lệnh trong nội dung giữ tên đường dẫn cũ. Hướng dẫn hiện hành tại [danh mục tài liệu](../README.md) và [scripts](../../scripts/README.md).

Ngày: **07/11/2026**. Phạm vi: frontend tích hợp trong repository hiện có; dừng sau Phase10. **Đã hoàn thành triển khai và các kiểm tra chức năng trong phạm vi dưới đây.** Không tuyên bố production readiness hoặc nghiệm thu chất lượng AI từ test giao diện.

## A. Implementation Summary

Lens dùng React/TypeScript/Vite/Tailwind hiện có, tích hợp Semantic, Image, Multimodal, Multi-intent, RAG và Agent bằng contract thật. Bổ sung drag/drop, advanced metadata filters/fusion/rerank, gallery và private detail dialog, cancellation/stale guards, dataset/capability states, dashboard benchmark, theme và accessibility. Không thay encoder/ranking, không reindex corpus để hoàn thành UI, không tạo app demo hoặc publish.

## B. Files Created / Updated

Các nhóm source chính:

- `frontend/src/features/search`: `SearchForm`, `SearchWorkspace`, `useSearchSession`, `AdvancedControls`, `validation`, `ImageUpload`, `ResultGallery`, `ResultImage`, `ImageDetailDialog`, `QueryAnalysis`, `SearchSkeleton` và unit tests tương ứng.
- `frontend/src/features/system/DatasetStatus.tsx`, `hooks/useWorkspaceStatus.ts`; `features/evaluation/EvaluationPage.tsx`.
- `features/rag/ExplanationPanel.tsx`, `features/agent/api.ts`, `features/agent/AgentResults.tsx`: nối SSE chung, giữ partial/validated citations và gallery dùng chung. Giữ các thay đổi Prompt08/09 đã có, không revert working tree của người dùng.
- `services/api/client.ts`, `decoders.ts`, `stream.ts`, `media.ts`, `types/api.ts`, App và CSS design tokens.
- E2E `phase10.spec.ts`, `phase10-empty.spec.ts`, `phase10-performance.spec.ts`; cập nhật regression foundation/RAG và Playwright projects. Chỉ thêm axe-core ở dev dependency/lockfile.
- Backend bổ sung `services/workspace.py`, hai read-only routes trong `api/v1/system.py`, config evaluation root, nullable metadata detail fix, 11 unit tests; Compose thêm evaluation mount read-only. Không migration.
- Scripts: `check_frontend.py`, `phase10_empty_server.py`, `capture_phase10_evidence.py`.
- Bảy tài liệu frontend theo yêu cầu; cập nhật README, MASTER_SPEC, ROADMAP, SAD, SYSTEM_ARCHITECTURE, SETUP, API_SPECIFICATION và `.env.example`.

Manifest thay đổi so với snapshot đầu Phase10 và fingerprint source cuối được lưu tại `docs/verification/phase10/source_changes.json` và `final_audit.json`. Không stage/commit/push trong nhiệm vụ này.

## C. Frontend Architecture

App quản lý shell/navigation/theme/token memory; form giữ draft; `useSearchSession` giữ server state và request identity; API layer kiểm tra JSON/SSE runtime; gallery/media/detail có vòng đời tài nguyên riêng. Dialog/evaluation/RAG/Agent code split. History API xử lý back/forward cho hai route; không thêm store/router/query library khi chưa cần. [Sơ đồ và quyết định](../features/FRONTEND_ARCHITECTURE.md).

## D. Search Interface

Auto/Text/Image/Multimodal/Multi-intent/Agent được bật theo capability. Text VI/EN, max 2000, Enter/Shift+Enter/IME, clear, Top-K runtime max 50, filters dataset/city/tags-any/MIME/dimensions, fusion RRF/weighted RRF/weighted score và rerank. Không gửi inference mỗi keystroke. State phân biệt validating/searching/success/no-match/index-not-ready/error/cancelled. Không tự biến core relational query chưa hỗ trợ thành Agent call.

**Trạng thái:** `IMPLEMENTED`, `TESTED_WITH_MOCKS`, `VERIFIED_WITH_REAL_BACKEND`, `VERIFIED_WITH_REAL_DATA`.

## E. Image Upload & Gallery

Select/drop một JPEG/PNG/WebP; kiểm tra empty/MIME/size, preview/name/size/remove và revoke URL. Query image không gọi ingestion. Gallery bảo toàn rank, score type không phải xác suất, metadata/tags/evidence, placeholder/error retry; lazy authenticated fetch thực sự. Detail dùng API metadata/ảnh gốc, có prev/next/arrow/Escape/focus trap/return focus; không tạo public download/share.

**Trạng thái:** `VERIFIED_WITH_REAL_DATA`; drop/error/cleanup/race branches bổ sung `TESTED_WITH_MOCKS`. Thumbnail backend còn cho phép trả original bytes.

## F. Multi-intent & Multimodal

AND/OR, tiếng Việt, uncertainty/limitations và cây constraints lấy từ backend, không chạy parser giả phía UI. Per-result evidence giữ ba trạng thái satisfied/violated/unknown; semantic score không trở thành xác nhận thị giác. Multimodal gửi đúng multipart/options và giữ cả hai modality; RRF/weighted score được kiểm chứng browser trên ba engine. Weighted RRF có control và dùng contract đã có, không tuyên bố benchmark riêng cho chiến lược này ở Phase10.

## G. RAG Interface

Explicit explain-existing truyền image_ids và expected_index_id; không yêu cầu UI chạy lại search. Streaming theo capability; JSON khi streaming tắt. Chỉ render terminal answer/citations đã kiểm tra, không raw unverified token. Có cancel/retry, error/insufficient/quota, giữ ảnh.

Real browser desktop và mobile đều nhận **generated=true, grounding_status=supported, 6 citations, error_code=null** từ provider thật; [raw outcomes](../verification/phase10/rag_outcomes.json). Đây là kiểm chứng luồng metadata grounding, không phải chấm faithfulness bởi con người. Mock tests bao gồm incomplete SSE, foreign citations, late cancelled response và timeout retry có chủ đích.

## H. Agent Interface

Public progress và final steps/tool timing lấy từ SSE/response, entities/quan hệ/source links từ dữ liệu thật, optional validated RAG. Không hiển thị chain-of-thought. Phân biệt insufficient relation, empty dataset, partial, timeout, fatal error và quota; `retrieval_preserved=true` giữ ảnh chờ terminal partial.

Workflow địa danh NPS thực hiển thị **3 ảnh, 4 tool steps**, quan hệ tại Washington, D.C. và link nguồn; missing relation không tạo ảnh địa danh giả. LLM planner và optional Gemini citations được kiểm chứng bằng các ca opt-in. Chất lượng multi-hop trên bộ nhãn human chưa được nghiệm thu.

## I. Empty Dataset Mode

Đã chạy backend thực trên database/bucket/collection tạm riêng, không xóa live volumes. Fixture xác nhận **0 Qdrant points, 0 MinIO objects**; API xác nhận **0 DB images, 0 indexed receipts**, dependencies healthy; features tắt được phản ánh đúng UI. Desktop/mobile không có fake cards/traces, không POST search, vẫn nhập draft/chọn ảnh/navigation được. Evaluation empty có trạng thái riêng, không bảng số liệu giả. [Nguồn bằng chứng](../verification/phase10/empty_resources.json), [API snapshot](../verification/phase10/api_evidence.json).

Empty→ready bằng refresh không sửa source được kiểm tra thêm với controlled mock. Dataset live nghiệm thu có **513 ảnh/513 indexed receipts/513 vectors**, active index `b4597021-4b91-491d-99ae-0617a6ca389c`, generation **3**. [Thiết kế và lệnh tái hiện](../features/FRONTEND_EMPTY_DATASET_MODE.md).

## J. API Integration & Verification State

| Nhóm | Trạng thái và bằng chứng |
|---|---|
| Health/live/readiness/workspace | `VERIFIED_WITH_REAL_BACKEND`; live dataset và empty backend, private auth |
| Text/image/multimodal/multi-intent | `VERIFIED_WITH_REAL_DATA`; real CLIP/Qdrant/PG/MinIO |
| Image detail/content | `VERIFIED_WITH_REAL_DATA`; API roundtrip và browser decode/focus |
| RAG/Agent | `VERIFIED_WITH_REAL_DATA` cho workflow mô tả ở G/H; controlled failures là `TESTED_WITH_MOCKS` |
| Evaluation | `VERIFIED_WITH_REAL_BACKEND` với artifact benchmark đã lưu; empty thật cũng đã kiểm tra |
| HTTP 400/401/403/404/408/422/429/500/503, malformed proxy HTML | `TESTED_WITH_MOCKS`; bảo toàn HTTP status, không tự retry |
| Endpoint/media không token | `VERIFIED_WITH_REAL_BACKEND`, HTTP 401 |
| Human relevance/faithfulness, Recall@10 công bố | `NOT_VERIFIED`, chờ nhãn được xác nhận |

Không có provider secret trong frontend env/bundle hoặc URL media. Provider configuration không đồng nghĩa quota/provider luôn online; lỗi generation vẫn được xử lý ở request thực. [Contract](../features/FRONTEND_API_INTEGRATION.md).

## K. Responsive & Browser Compatibility

**72 functional E2E pass**, 0 fail/flaky; 2 performance test skip có chủ đích trong ma trận rồi chạy riêng đều pass. Chromium desktop/mobile, tablet, Firefox desktop và WebKit mobile emulation đã kiểm tra; 4 ca empty backend thật trên desktop/mobile. Gallery/layout không tràn ngang; table overflow có region riêng, upload và native dialog hoạt động.

Không tuyên bố đã chạy Chrome/Edge branded binary, Safari Apple hoặc thiết bị Android/iOS vật lý. WebKit ban đầu lỗi thư viện host/Snap; đã xử lý ở child test environment và pass toàn ma trận cuối, không ẩn failure bằng skip project.

## L. Accessibility

Axe tags WCAG 2 A/AA, 2.1 AA, 2.2 AA ở search sáng, dialog, search tối, evaluation tối trên **5 project**: **20 screen audits không violation**; thêm **2 empty screen audits thật**. Native keyboard focus/arrow/Escape/Tab/return-focus, labels/status/alert/skip link, contrast theme và reduced-motion styles được triển khai. [Axe evidence](../verification/phase10/accessibility.json).

Chưa có kiểm tra người dùng với NVDA/VoiceOver/thiết bị thật hoặc audit WCAG toàn diện. Không gọi kết quả axe là chứng nhận WCAG.

## M. Frontend Performance

20 mẫu/viewport sau 2 warmup, local CPU, Chromium/Vite dev, C1, không throttle, không gọi LLM:

| Metric (ms) | Desktop P90 / P95 | Mobile P90 / P95 |
|---|---:|---:|
| API client | 141.78 / 153.48 | 134.68 / 136.50 |
| Thẻ kết quả sau commit/frame proxy | 216.59 / 230.26 | 216.68 / 217.87 |
| React gallery render | 13.03 / 13.41 | 13.42 / 13.64 |
| Fetch + load/decode ảnh đầu từ intersection | 92.70 / 94.76 | 58.32 / 64.98 |

Top-K 50 ban đầu chỉ tải 8 media desktop / 1 mobile. Entry JS production 272.42 kB, gzip 85.32 kB; có 4 lazy chunks. API time, frame proxy, React CPU và image time có định nghĩa riêng; các percentile không cộng/trừ thay thế nhau. Không lấy số đo frontend 20 mẫu để xác nhận SLA backend P90/P95 hoặc TTLast 3s. [Phương pháp, raw samples và giới hạn](../research/FRONTEND_PERFORMANCE.md).

## N. Test Results

- Frontend: **40/40 unit**, 9 files, typecheck/lint/build pass.
- Backend: **211/211**, gồm **199 unit + 12 integration**; [log](../verification/phase10/backend_tests.txt).
- Ma trận browser: **72 pass / 2 performance skip / 0 fail / 0 flaky**, 3.5 phút; [JSON](../verification/phase10/browser_final.json), [log](../verification/phase10/browser_final.txt).
- Performance riêng: **2/2 pass**, 40 measured requests + 4 warmups và 2 Top-K50 requests; [log](../verification/phase10/performance_run.txt).
- Trong 72 functional ca có **14 mock/hybrid** được phân loại rõ; các ca còn lại gồm API/data thực và 2 artifact annotation thực. Không trình bày ca quota SSE giả làm provider-rate-limit thật.
- API liveness/readiness/metadata/media/auth và dataset count cuối: [api_evidence.json](../verification/phase10/api_evidence.json). Human labels tiếp tục chờ theo quyết định trước của người dùng.

Các lỗi tìm được đã sửa: aria-label trên generic placeholder, Agent không đưa kết quả vào vùng nhìn thấy, regression test cuộn hidden image thay vì card sau lazy network, runtime WebKit phụ thuộc thư viện host/Snap. Failure matrix ban đầu giữ trong artifact; không xóa lịch sử để tạo báo cáo pass.

## O. Known Issues / Unresolved Checklist

- [x] Không còn failure chức năng/lint/type chưa xử lý trong các kiểm tra đã nêu.
- [ ] Human relevance/faithfulness và semantic benchmark chất lượng: người dùng đã cho phép giữ chờ, không tự điền nhãn.
- [ ] QA trên Safari/Edge/Chrome branded, thiết bị iOS/Android và screen reader thật.
- [ ] Đo LCP/INP, skeleton first-paint riêng, mạng di động/CPU throttle và production load frontend.
- [ ] Thumbnail derivative riêng: backend hiện cho phép original fallback.
- [ ] Dashboard chưa công bố Recall@10, quality charts hoặc per-group Agent/RAG aggregate; null hiển thị chưa đo, không giả lập số liệu.
- [ ] UI chưa cung cấp trình dựng AST tùy ý, captured-date filters hoặc công cụ quản trị ingestion. Các luồng dữ liệu tiếp tục dùng CLI/worker hiện có.

Không bổ sung hạng mục ngoài scope để gọi hệ thống production ready. Secrets/browser storage và raw artifacts được kiểm tra trong final audit; trace vẫn tắt.

## P. Prompt11 Readiness

**Sẵn sàng bàn giao sang Phase11 khi người dùng yêu cầu**, với source UI/API, contracts, typed decoders, fixtures real-empty, regression matrix, source manifest và số đo thực làm baseline cho integration/reliability/security/performance/debugging sâu. Infrastructure và dữ liệu thực đủ cho các luồng chức năng đã kiểm tra; không bị chặn bởi thiếu corpus cho functional QA. Nghiệm thu chất lượng AI vẫn thiếu nhãn human, QA thiết bị thật cần môi trường tương ứng.

**Dừng sau Phase10. Không triển khai Phase11, không deploy hoặc push code tự động.**
