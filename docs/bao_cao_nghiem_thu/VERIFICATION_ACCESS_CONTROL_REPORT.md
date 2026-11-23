# Nghiệm thu phân quyền và cải thiện giao diện

Ngày 08/11/2026. Triển khai tài khoản Admin/User và quyền thư viện trên ứng dụng hiện có. Báo cáo này bổ sung cho snapshot Phase12, không thay các số đo chất lượng lịch sử.

## Đã triển khai

- Đăng nhập bằng username/password, session HttpOnly, CSRF, giới hạn login và hạn mức User; thay/reset mật khẩu, khóa tài khoản và thu hồi phiên. Không có đăng ký công khai.
- Admin quản lý tài khoản, vai trò, thư viện/grants; nhập/sửa/ẩn/khôi phục ảnh; tạo/reindex/verify/activate chỉ mục; nhập tri thức theo thư viện; xem benchmark và nhật ký.
- User chỉ tìm và đọc dữ liệu đã được cấp; quyền được kiểm tra tại API, Qdrant, PostgreSQL, ảnh trực tiếp, evidence RAG và repository tri thức Agent. Không chỉ ẩn nút trên giao diện.
- Login mới, khu khám phá tập trung vào ảnh, sidebar thư viện được chia sẻ; khu Admin riêng có tabs; trang đổi mật khẩu; responsive, theme sáng/tối, nhãn hỗ trợ screen reader. User không phải nhập token, không thấy chẩn đoán/benchmark hoặc thông số inference trên màn tìm kiếm.
- Worker cập nhật receipt metadata_revision đúng sau chỉnh sửa. Scheduler chỉ nhận model manifest tương thích, không để retry/lease chưa đến hạn chặn việc mới; cooldown khi một index lỗi. Development worker có tmpfs heartbeat và healthcheck.
- Migration bổ sung `20261108_access_control`, backfill catalog/knowledge scope từ dữ liệu hiện có. Không đổi encoder/decoder hay manifest/index active.

## Kiểm chứng thực chạy

| Kiểm tra | Kết quả |
| --- | --- |
| Backend unit/security/reliability | 254 pass |
| PostgreSQL/Qdrant/MinIO integration | 16 pass, gồm 5 ca tổng hợp cho tài khoản, scope, metadata, index, tri thức và scheduler |
| CLIP thật với ảnh tổng hợp QA | 1 pass; không coi là nhãn relevance |
| Frontend unit | 48 pass |
| ESLint, TypeScript, frontend build | Pass |
| Ruff check/format, Python compile | Pass |
| Browser QA Admin/User, desktop/mobile | 2 pass, thêm kiểm tra tương phản theme tối và login sau logout; thực tạo tài khoản/cấp quyền/tìm ảnh/ảnh private/403 Admin/logout |
| Browser giả lập lỗi tìm kiếm/RAG/module/XSS | 4 pass; đây là mock, không coi là integration |
| Kiểm tra HTTP corpus chính | Pass đăng nhập Admin, 513 ảnh/indexed/vectors, tìm kiếm và ảnh private, logout |
| Kiểm tra browser corpus chính | 2 pass desktop/mobile, xem main-browser.json |
| Deployment Nginx và browser | HTTP đầy đủ pass; 4 browser pass (desktop/mobile/Firefox/WebKit), xem deployment-browser.json |
| Quét secrets và tài liệu | Không có secret match; 106 tài liệu không có link local hỏng |

Các ca security bao gồm chống CSRF/Origin sai, token vận hành bị tắt, last Admin, reset/expiry/khóa tài khoản, User gọi API Admin, đoán ID ảnh, thư viện rỗng, grant/thu hồi, Qdrant pushdown, evidence RAG, tri thức Agent, ẩn/khôi phục, metadata job và quota. API/worker dùng services thật trong namespace QA tạm; vector synthetic dùng để kiểm tra cơ chế. Test CLIP riêng dùng model đã cache và ảnh tổng hợp. Không gọi Gemini để tự chấm chất lượng.

Warnings còn lại là qdrant-client thông báo API key trên kết nối HTTP của mạng Docker private, và Playwright báo NO_COLOR/FORCE_COLOR; không có lỗi lint/type bị bỏ qua. CI workflow đã cập nhật bootstrap/tài khoản nhưng chưa chạy GitHub Actions từ phiên làm việc này.

## Dữ liệu và thông tin đăng nhập

Development: http://localhost:5173, backend http://localhost:8000. Admin local: `.cache/auth/admin-login.json` (0600). Deployment riêng: http://127.0.0.1:8088, Admin `.cache/auth/deployment-admin-login.json` (0600). Các file này không nằm trong Git, frontend bundle hoặc Docker context.

Corpus chính giữ 513 ảnh/original receipts, active index `b4597021-4b91-491d-99ae-0617a6ca389c`, generation 3 và 513 active vectors. Worker daemon đã khôi phục một job `processing` lịch sử hết lease ở collection thử nghiệm không active: ready embeddings tổng 1053 → 1054, succeeded items 1073 → 1074, collection thử nghiệm 0 → 1 point. Đây là hoàn tất công việc cũ, không thêm ảnh vào corpus hoặc đổi active index. Các collections khác và 516 object MinIO giữ nguyên. So sánh ở main-before.json/main-after.json; không đánh dấu assertion inventory tổng ban đầu là pass.

Deployment giữ 7 ảnh tổng hợp, 7 originals, 13 ready embeddings, 9 objects, active generation 2. Image Phase12 cũ giữ tag nguyên vẹn; bản cuối dùng tag `access-control-v3` (các tag trung gian giữ riêng), xem release.json. Trước migration chính có pg_dump private tại `.cache/auth/backups/before-access-control-main.dump`; trước mỗi cập nhật deployment có backup đầy đủ checksum trong `backups/` (0700/0600, ignored).

`.env` development và secrets deployment được giữ nguyên. Deployment bổ sung cờ auth, localhost CORS và đổi release tag. Kiểm tra checksum encoder/decoder, env chính và secrets: secret-check.json.

## Các lỗi phát hiện và đã xử lý

Trong quá trình thực hiện, các lượt kiểm thử trung gian thất bại rồi được sửa: schema expectation chưa có bảng mới; truy vấn GROUP BY thống kê thư viện; sai đường dẫn status trong test; receipt phiên bản metadata sau edit; flush khóa ngoại khi nhập knowledge scope; nhãn account mobile và editor remount làm mất phản hồi; operator route trong bộ test cũ. Các lần chạy cuối trong bảng mới dùng làm bằng chứng pass. Lệnh `operations migrate` không tồn tại đã dừng trước thao tác; migration chạy bằng Alembic. Lần pg_dump ghi trực tiếp file gặp hạn chế Docker Snap đã được chạy lại qua pipe thành công.

## Giới hạn giữ rõ

- Chỉ triển khai local; public hosting/TLS và ngoại lệ Docker Snap no-new-privileges vẫn theo tài liệu vận hành. Public origin cần HTTPS và AUTH_COOKIE_SECURE=true.
- Recall/relevance và chất lượng RAG vẫn chờ nhãn người đánh giá; không tự nâng trạng thái nghiệm thu chất lượng.
- Chưa có MFA/SSO/email khôi phục. Operator reset qua terminal; không có public bootstrap endpoint.
- Quyền thư viện là phạm vi dùng chung, chưa có ownership của từng ảnh trong cùng thư viện. Admin có toàn quyền nội dung theo vai trò.
- Thu hồi áp dụng yêu cầu kế tiếp; không thể thu hồi byte đã tải trước đó. Request đang chạy dùng snapshot quyền đã xác thực.
- Index activation hiện hỗ trợ một API process như Compose; nhiều replica cần reload generation phối hợp. Model mới cần operator chuẩn bị artifact; không có tải model tùy ý qua web.
- Usage/throttle cần scheduled retention khi vận hành dài hạn; audit cần chính sách lưu/archival của tổ chức.

QA đã được dọn sau kiểm thử; hai stack development/deployment vẫn hoạt động. Tổng hợp máy đọc được: summary.json; runtime/source/release và bằng chứng kiểm thử nằm cùng thư mục.

Hướng dẫn: [ACCOUNTS](../../operations/ACCOUNTS.md). Thiết kế/API: [ACCESS_CONTROL](../../architecture/ACCESS_CONTROL.md).
