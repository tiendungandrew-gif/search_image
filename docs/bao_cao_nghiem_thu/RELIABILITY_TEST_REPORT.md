# Reliability — Phase11

> Tài liệu lịch sử theo phase; lệnh trong nội dung giữ tên đường dẫn cũ. Hướng dẫn hiện hành tại [danh mục tài liệu](../README.md) và [scripts](../../scripts/README.md).

## Phép thử ngắt dịch vụ thật

[faults.json](../verification/phase11/faults.json) ghi bốn kịch bản SIGKILL chỉ trong project QA. Dataset trước/sau giữ nguyên6 images,6 vectors, index generation1. API liveness vẫn200 khi dependency chết; readiness503, search503 có error code thay vì kết quả rỗng giả.

| Container QA bị ngắt | Readiness ms | Search lỗi ms | Phục hồi đến search dùng được ms |
| --- | ---: | ---: | ---: |
| PostgreSQL | 6,73 | 4,44 | 883,50 |
| Qdrant | 10,91 | 10,20 | 878,64 |
| MinIO | 6,19 | 127,04 | 840,33 |
| API | N/A | Proxy5xx | Frontend shell vẫn200; restart và poll search thành công |

Số đo là quan sát một lần trên máy local; không phải MTTR/SLA production. Script có `finally` khởi động lại service và poll hữu hạn45s. Process worker riêng cũng bị SIGKILL sau durable claim; lease expiry/recovery hoàn thành job, không chấp nhận stale claim.

Đã chạy lại cả4 kịch bản trên stack hoàn toàn rỗng, đúng nhánh CI: cả4 pass; readiness503 trong12,50–21,97ms, phục hồi dependencies trong987,01–1255,79ms, dataset vẫn0 ảnh/không index. Tổng là8 lượt fault checks trên4 loại kịch bản và2 trạng thái dữ liệu. Artifacts lần sau có timestamp, không ghi đè raw evidence trước.

## Timeout, retry và cancellation

| Cơ chế | Hành vi/kiểm chứng |
| --- | --- |
| Request middleware | Deadline trả envelope lỗi; malformed Content-Length không còn500 |
| PostgreSQL | connect/pool/statement timeouts, pre-ping; fault integration kiểm tra phục hồi |
| Qdrant/MinIO | RPC/probe timeout; phân biệt unavailable với object missing |
| Inference | Một thread, queue có capacity và thời gian chờ; cancel không giải phóng slot trước completion |
| Worker | Lease token fencing, bounded attempts và exponential backoff+jitter; không retry permanent vector errors |
| RAG | Provider deadline/structured validation; failure giữ retrieval; SSE recoverable error chờ terminal response |
| Agent | Total deadline, tool deadline, hop/tool limits, loop/unknown-tool guards, partial validated images |
| Browser | Abort khi unmount/token change/cancel; stale response không ghi đè state mới |

Lỗi race giữa tool timeout và total Agent deadline đã sửa; budget toàn request luôn được phân loại `AGENT_DEADLINE_EXCEEDED`, kể cả optional RAG. Không xóa validated images đã lấy được.

CPU inference không thể bị hard-kill qua asyncio cancellation. Search giữ capacity đến khi thread hoàn tất. Worker giữ ảnh PIL đang được encoder dùng, rồi đóng khi encoding hoàn tất; lease recovery xử lý job chưa có receipt. Model bị treo ở native code vẫn cần process supervisor; không tuyên bố hard deadline cho việc dừng native compute.

## Resource lifecycle

`AsyncExitStack` đăng ký cleanup ngay khi tạo services/generator/runtime/agent; lỗi startup hoặc lỗi một closer không bỏ qua các closer còn lại. Hai regression tests tái hiện leak đã pass. Benchmark monitor luôn được cancel/await trong finally, kể cả health503; regression từng fail do pending task và nay pass.

Worker batch metrics dùng deque10000, cumulative counters giữ throughput không phụ thuộc việc truncate history. API metrics cũng có giới hạn. Health hook trước đây chỉ abort request ban đầu khi unmount; nay abort request hiện tại. ErrorBoundary giúp lỗi lazy chunk có giao diện tải lại.

## Giới hạn

Chưa thực hiện soak dài giờ/ngày, disk full, partition kéo dài, host reboot, physical device hoặc chaos đa host. Gemini thực tế có first-attempt timeout và retry; hai câu RAG vẫn vượt3s. [Performance](PERFORMANCE_REGRESSION.md) ghi nguyên kết quả, không coi HTTP200 là không có timeout nội bộ.
