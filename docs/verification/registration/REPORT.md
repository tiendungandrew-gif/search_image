# Đăng ký tài khoản — 19/11/2026

Đã thêm nút **Đăng ký** tại form Lens, giữ nền collage và hỗ trợ desktop/mobile. Form nhận tên hiển thị, tên đăng nhập, mật khẩu 12–128 ký tự và xác nhận. Có hiện/ẩn mật khẩu, kiểm tra xác nhận, lỗi tên trùng, loading/khóa thao tác và quay lại đăng nhập. Đăng ký xong điền sẵn username, xóa mật khẩu và thông báo thành công; người dùng tự đăng nhập.

`POST /api/v1/auth/register` trả 201 `{status:"registered"}`, không tạo session. Input không nhận role/grants/is_demo. Tài khoản luôn User, active, không demo và không có thư viện. Tên chuẩn hóa chữ thường, tên demo dành riêng bị từ chối; unique insert ngăn tạo trùng khi hai yêu cầu đồng thời. Mật khẩu dùng salted scrypt và password semaphore hiện có. Dùng kiểm tra Origin/throttle hiện có, audit `auth.registered`, không trả hash/password. Không cần migration.

## Kiểm chứng

| Kiểm tra | Kết quả | Bằng chứng |
| --- | --- | --- |
| Frontend unit/component | 70 pass / 17 files | [frontend-test.txt](frontend-test.txt) |
| ESLint | Pass | [lint.txt](lint.txt) |
| TypeScript + Vite build | Pass | [build.txt](build.txt) |
| Backend unit/security/reliability | 257 pass | [backend-fast.log](backend-fast.log) |
| PostgreSQL/Qdrant/MinIO integration | 22 pass, gồm 3 test đăng ký mới | [backend-services.log](backend-services.log) |
| Chromium desktop/mobile/320px và Firefox | 4 pass | [browser.json](browser.json), [browser.txt](browser.txt) |
| Ruff check/format các file Python đổi | Pass | Kiểm tra trực tiếp sau chỉnh sửa |

Integration chạy database/bucket/collection QA disposable, kiểm tra hash mật khẩu thật, audit, signup/login/logout/cookie, 403 Admin, không tự cấp grant, duplicate race, role/grant injection, input, Origin, tên demo và throttle. Frontend kiểm tra mismatch không gửi API, username chuẩn hóa, success và xóa password, pending/error/retry. Browser dùng API QA thật, kiểm tra 201/409, đăng nhập User không grant, 403 Admin, logout, axe và không tràn ngang; Firefox dùng dark theme.

Đã xem [form mobile](signup-mobile.png). Lưu thêm [desktop](signup-desktop.png), [320px](signup-narrow.png), [Firefox dark](signup-firefox.png). [Script kiểm chứng](check.mjs). Lượt browser đầu thiếu baseURL cho request kiểm tra Admin; đã sửa script và chạy lại, bằng chứng đầu giữ tại [initial-browser.txt](initial-browser.txt). Lượt TypeScript đầu phát hiện option `exact` không hợp lệ trong test Testing Library; đã sửa query và build cuối pass. Không gọi những lượt này là pass.

Backend development đã restart và xác nhận OpenAPI có endpoint mới, liveness 200. Mở http://localhost:5173 → **Đăng ký** để dùng. Các lượt tạo tài khoản thử dùng QA riêng, không thêm tài khoản test vào dữ liệu chính. QA được dọn sau kiểm chứng. Bản production-like 8088 chưa cập nhật; mã nguồn chưa commit.

Đăng ký dùng username, không thu thập email hoặc gửi email xác minh/khôi phục. Thư viện do Admin cấp theo chính sách quyền hiện có; người dùng mới có thể đăng nhập ngay và thấy thư viện trống.
