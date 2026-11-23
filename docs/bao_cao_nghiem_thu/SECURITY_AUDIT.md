# Kiểm tra bảo mật thực dụng — Phase11

> Tài liệu lịch sử theo phase; lệnh trong nội dung giữ tên đường dẫn cũ. Hướng dẫn hiện hành tại [danh mục tài liệu](../README.md) và [scripts](../../scripts/README.md).

Phạm vi: source audit, 28 security tests, unit Agent/RAG/API, real private storage integration và browser XSS/URL tests. Đây không phải penetration test hoặc chứng nhận không còn lỗ hổng.

| Vấn đề | Mức độ | Kết quả |
| --- | --- | --- |
| Content-Length cực dài/malformed | Medium | Đã tái hiện500; chặn ASCII decimal/length/bound trước int, trả413 |
| Control characters trong filter/metadata | Medium | Chặn trước PostgreSQL; giữ Unicode hợp lệ và caption multiline/hash |
| Zero embedding vẫn publish success | High, toàn vẹn dữ liệu | Chặn finite/shape/norm trước Qdrant; real regression pass |
| Fixture import vào nhầm DB | High nếu cấu hình nhầm | Guard QA host/db/flag và fixture opt-in; serving DB tiếp tục bị từ chối |
| SQL injection | Không tái hiện khai thác | Bind parameters/SQLAlchemy; punctuation là dữ liệu, không ghép raw SQL từ input |
| XSS/foreign media | Không tái hiện trong phạm vi test | React text rendering, không dangerous HTML; URL same-origin/private path validation |
| Upload | Kiểm chứng input limits | Decode thật, magic/format/pixel/byte bounds, corrupt/unsupported/type mismatch; query image không ingest |
| API/media auth | VERIFIED_WITH_REAL_SERVICES | Read/write token boundary; private API401, MinIO anonymous403, no-store |
| Agent tools | TESTED_WITH_MOCKS + REAL_SERVICES | Typed allowlist, validate arguments/dependencies/budgets; không shell/SQL tool tùy ý |
| Prompt injection | TESTED_WITH_MOCKS | Untrusted caption/context không thành system/tool authority; invalid citation/plan bị từ chối |

## Credentials và log

`.env` và `.env.qa` mode0600, được gitignore; QA sinh credentials khác hoàn toàn, không kế thừa provider keys. Không đưa credentials server vào `VITE_*`. Token truy cập được người dùng nhập vào phiên UI; đây là credential của client, không được lưu localStorage hoặc bundle. CI mặc định không cần production/provider secrets.

Structured logger dùng allowlist: request ID, mode, model/index, route, status, duration/error category. Raw queries, Authorization, prompts và untrusted extra fields không xuất hiện trong formatter regression. Playwright trace tắt. Screenshot/error-context có thể chứa token đã nhập; test-results được ignore, không đưa vào source archive và không dùng ảnh lỗi đó làm artifact công khai.

Scan cuối so sánh **giá trị** secrets local với docs, artifacts và frontend dist, chỉ xuất tên biến nếu phát hiện; xem `final_audit.json`. Không in keys trong báo cáo. Npm audit thực tế báo0 advisory ở thời điểm chạy; `uv pip check` báo69 packages tương thích. Pip check không phải CVE scan Python/container; các scan đó **NOT_VERIFIED**.

## Storage và deployment boundary

Signed/expired URLs: **N/A**, hệ thống dùng authenticated media proxy; không có presigned credential trong browser URL. Object orphan detector chỉ báo cáo, không tự xóa object phục vụ.

Local endpoints bind loopback; QA data network internal. Qdrant HTTP API-key warning vẫn có: chưa mã hóa nội bộ. TLS, reverse proxy, rate limiting ở edge, credential rotation/RBAC đa tenant, backup/restore và hardening exposure cần thiết kế/kiểm tra ở Phase12. Không mở public hosting trong Phase11.

Prompt injection tests chỉ bao phủ các payload đã liệt kê. Không tuyên bố toàn bộ model output luôn đúng hoặc chống mọi injection. Human faithfulness/relevance vẫn chờ xác nhận.
