# Lỗi và bản sửa — Phase11

> Tài liệu lịch sử theo phase; lệnh trong nội dung giữ tên đường dẫn cũ. Hướng dẫn hiện hành tại [danh mục tài liệu](../README.md) và [scripts](../../scripts/README.md).

Các lỗi dưới đây đã được tái hiện trước bản sửa khi khả thi. Không tính lỗi sandbox, dependencies thiếu extra hoặc sai fixture request ID là lỗi của production API. Không xóa log chạy fail để làm báo cáo xanh.

## Defect register

| ID / mức độ | Tái hiện; expected / actual | Root cause và bản sửa | Regression / kết quả |
| --- | --- | --- | --- |
| P11-01 Medium — request validation | POST với Content-Length gồm5000 chữ số hoặc Unicode digit. Expected413; actual500 do int conversion | `core/middleware.py`: ASCII decimal + length/bound trước int; empty header cũng invalid | `security/test_request_security.py::test_invalid_content_length_never_becomes_internal_error`,5 variants pass |
| P11-02 Medium — metadata validation | Filters/ingestion metadata chứa NUL/control. Expected ValidationError; schema cũ chấp nhận | `schemas/filters.py`, `schemas/ingestion.py`: reject Cc/Cs, normalize filter; giữ multiline caption và fingerprint input | Security filter/upload/control/Unicode/multiline cases pass; real SQL punctuation là dữ liệu |
| P11-03 Medium — Agent deadline | Optional RAG chạm total deadline. Expected global deadline và giữ ảnh; actual tool timeout/warning sai, assertion race | `agent/tool_executor.py`, `agent_service.py`: xét global deadline, propagate code và giữ validated results | `unit/test_agent.py::test_overall_deadline_during_rag_preserves_validated_images` pass |
| P11-04 Medium — lifecycle | Generator constructor hoặc closer lỗi. Expected services đóng; actual close không được gọi | `main.py`: AsyncExitStack, đăng ký closer ngay sau khi tạo resource; không nuốt lỗi | Hai `reliability/test_lifecycle.py` từng fail, nay pass |
| P11-05 Medium — frontend cleanup | Refresh health rồi unmount. Expected abort request hiện tại; actual chỉ abort controller ban đầu | `hooks/useHealth.ts`: cleanup theo ref hiện tại và clear ref | `useHealth.test.tsx` tái hiện fail trước sửa, nay pass |
| P11-06 Medium — RAG SSE | Recoverable error trước generation_completed. Expected terminal fallback và ảnh; actual UI kết thúc sớm | `ExplanationPanel.tsx`: tiếp tục khi retrieval_preserved=true; decoder kiểm tra terminal payload | Component test và mock browser pass; serving browser timeout fallback giữ10 ảnh |
| P11-07 High — indexing integrity | Zero encoder trên Qdrant thật. Expected failed/no point; actual job succeeded | `indexing/collection_manager.py`: validate batch shape, finite, dimension, normalized norm trước RPC | `integration/test_qa_services.py::test_zero_encoder_cannot_publish_a_successful_receipt` từng fail; nay pass/0points |
| P11-08 Medium — benchmark leak | Health503 khi resource monitor đang chạy. Expected cleanup; actual pending monitor task | `evaluation/benchmark.py`: try/finally, set stop, cancel và await monitor trên mọi exit | `reliability/test_benchmark_cleanup.py` từng fail; nay pass; benchmarks thực hoàn tất |
| P11-09 Medium — worker cancellation | Block encoder thread, cancel worker rồi cho thread đọc PIL. Expected inputs còn sống; actual ValueError vì image đã đóng | `indexing/worker.py`: shield task, thread sở hữu/đóng inputs trong finally; collect exception, không upsert sau cancel | `integration/test_qa_services.py::test_worker_cancellation_keeps_images_alive_until_encoder_finishes` từng fail; nay pass |

Không có Critical defect được xác nhận còn mở trong phạm vi Phase11. P11-07 là lỗi toàn vẹn ingestion có thể chặn release; đã có real-service regression chứng minh sửa được.

## Hardening bổ sung

- Thêm ErrorBoundary cho lỗi render/lazy chunk, fallback có thể tải lại;2 component cases và1 mock browser pass. Đây là thiếu sót resilience phát hiện qua audit, không gán log reproduction trước sửa không tồn tại.
- Thêm DTO/OpenAPI cho `system/workspace` và `system/evaluation`, giữ JSON shape/client compatibility; finite/nonnegative metrics, malformed artifacts không đưa số giả ra UI. Unit/OpenAPI và real/browser regression pass.
- Guard integration/fixture import buộc QA flag/DB host/name và opt-in; không nới quyền fixture trên DB phục vụ. Unit security6 cases kiểm tra deny conditions.
- Worker metrics giới hạn10000 records, counters cộng dồn giữ throughput đúng khi history truncate. Unit/integration kiểm tra đường chạy worker; chưa có long-soak chứng minh ổn định nhiều ngày.
- Bổ sung mode/model/index/route vào safe logging allowlist; test loại private extra fields. Không log raw query để phục vụ telemetry.

## Các lần fail của môi trường/test harness

Host sandbox treo executor; browser IPC bị EPERM; WebKit thiếu shared libraries/Snap paths. Đã chuyển execution sang môi trường được phép và helper child env. Backend image ban đầu thiếu matplotlib evaluation extra; đã thêm build option dành QA/CI. Unit fixture từng kế thừa CORS/log env QA, nay tạo settings defaults độc lập.

AI fixture từng bị đúng guard từ chối, dùng request_id không phải UUID và đụng collection name cố định. Đã sửa test setup, namespace theo owned database hash và cleanup; không bỏ validation. Indexed mobile test từng đọc count cũ rồi abort request trước; đã đợi đúng response. Các log này nằm trong [runs](../verification/phase11/runs) và được giữ trạng thái failed ban đầu.

## Vấn đề còn mở

| ID | Mức độ | Trạng thái và ảnh hưởng |
| --- | --- | --- |
| LIM-01 | Medium | C4 có3/100 INFERENCE_BUSY; queue deadline/capacity cần capacity plan theo workload thật |
| LIM-02 | Medium | Gemini planner first-attempt timeout2/2; RAG generated2 mẫu vượt3s và browser2 lần timeout/fallback |
| LIM-03 | Medium, quality gate | Thiếu human relevance/faithfulness labels; không công bố AI accuracy |
| LIM-04 | Low, validation gap | GitHub Actions chưa chạy từ remote; local/actionlint không thay remote run |
| LIM-05 | Deployment scope | TLS/edge/RBAC/backup/restore/production-scale/physical-device/soak chưa xác minh |

Các giới hạn này không được ghi thành test pass. Nếu yêu cầu release bắt buộc generation≤3s hoặc production AI accuracy, các gate tương ứng vẫn chưa đạt. Milestone phần mềm độc lập dataset được đánh giá riêng ở [PHASE11_TEST_REPORT](PHASE11_TEST_REPORT.md).
