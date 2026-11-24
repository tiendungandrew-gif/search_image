# Browser E2E — Phase11

> Tài liệu lịch sử theo phase; lệnh trong nội dung giữ tên đường dẫn cũ. Hướng dẫn hiện hành tại [danh mục tài liệu](../README.md) và [scripts](../../scripts/README.md).

Playwright đã kiểm tra Chromium desktop1440px, mobile390px, Firefox1366px và WebKit390px. Đây là emulation/headless trên Linux, không phải iPhone/Android vật lý hoặc Safari binary của Apple.

## Kết quả tách theo backend

| Profile | Pass | Skip | Nguồn dữ liệu |
| --- | ---: | ---: | --- |
| QA mock riêng | 4 | 0 | `qa-e2e/mock.spec.ts`, fixtures ghi rõ MOCK |
| QA empty | 4 | 8 | Ba dịch vụ thật, không active index/knowledge, optional features off |
| QA indexed | 8 | 4 | CLIP thật,6 ảnh tổng hợp, fictional KB chỉ QA |
| Serving regression | 50 | 0 | Corpus513;42 ca thực và8 ca route mock có nhãn |

Không tính mỗi lần rerun thành test mới. Skip là profile không áp dụng, không phải pass. Các legacy Agent browser specs không chọn ở lượt hồi quy50 ca; Agent được kiểm tra bằng QA browser8 ca, unit, real integration và live benchmark riêng.

## Ma trận Phase 11

| ID | Hành vi | Bằng chứng |
| --- | --- | --- |
| E2E-01/02 | Startup và frontend gọi backend | QA empty/indexed và foundation |
| E2E-03 | Empty dataset, không ảnh/benchmark giả | QA empty với DB thật |
| E2E-04/05 | Text/image, preview/query ảnh không ingest | QA indexed + serving foundation |
| E2E-06/07 | Text+image/fusion và AND/OR/UNKNOWN | QA indexed + foundation |
| E2E-08 | RAG SSE/generated hoặc unavailable state | QA disabled;2 serving live;mock recoverable SSE |
| E2E-09 | Agent4 bước, unknown entity abstention | QA fictional KB thật + live framework |
| E2E-10 | Details/metadata/navigation/focus | QA indexed và serving phase10 |
| E2E-11/12 | Errors/backend unavailable | Mock profile; API container SIGKILL ở fault profile |
| E2E-13 | Cancel/retry/late response | Mock profile và hook unit |
| E2E-14 | Mobile không tràn ngang | Chromium/WebKit viewport390px |
| E2E-15 | Keyboard/axe | Details arrow/escape/focus; các trang search/dialog/evaluation/theme |

Hai ca serving RAG thực tế đều `generated=false`, `generation_unavailable`, `LLM_TIMEOUT`, không citations; UI giữ10 ảnh và hiển thị fallback đúng. [browser_rag_outcomes.json](../verification/phase11/browser_rag_outcomes.json) lưu kết quả. Generation thành công được kiểm chứng riêng trong Agent benchmark, không gán cho hai ca browser này.

## Lỗi phát hiện và xử lý

RAG SSE `error` có retrieval_preserved=true trước terminal event trước đây làm UI kết thúc sớm; component nay đợi response cuối và giữ ảnh. Health refresh sau unmount nay abort đúng request hiện tại. Lazy module failure nay được ErrorBoundary bao và có nút tải lại; payload exception không đưa ra UI.

Một lần indexed mobile bị INFERENCE_BUSY vì test kiểm tra count3 của kết quả trước rồi chuyển mode/hủy request đang chạy. Test nay đợi đúng POST response và assert200 trước khi chuyển mode; cả8 ca indexed đã pass. Không tăng queue timeout hoặc retry mù để che lỗi test.

Lần chạy trong sandbox không launch được browser do IPC EPERM; đã chạy lại ngoài sandbox. WebKit cần libevent/libavif dependencies và loại đường dẫn GIO/GTK/LD do Snap chèn trong child environment; helper `scripts/browser_environment.py` dùng chung với runner. Những lỗi môi trường ban đầu không được ghi thành product pass.

## Artifacts

[indexed_browser.json](../verification/phase11/indexed_browser.json), [main_browser.json](../verification/phase11/main_browser.json), [main log](../verification/phase11/main_browser.log) và [runs](../verification/phase11/runs) chứa kết quả thật. JSON empty/mock mới nhất được dẫn từ `final_audit.json`. Trace tắt; không lưu screenshot có token vào docs. Axe không có violations trong các states đã chọn, không thay thế đánh giá accessibility thủ công.
