# Đăng nhập nhanh Admin / User

Trang đầu development hiện mở tìm kiếm khách. Mở http://localhost:5173/login hoặc bấm **Đăng nhập** để dùng các nút vào nhanh.

Mở http://localhost:5173, đăng xuất nếu đang có phiên, rồi chọn **Vào nhanh Admin** hoặc **Vào nhanh User**. Admin mở thẳng `/admin`; User mở trang tìm kiếm. Có thể đăng xuất để đổi vai trò. Form username/password vẫn dùng được cho tài khoản cá nhân.

Hai nút dùng tài khoản trải nghiệm riêng `demo_admin` / `demo_user`, được đánh dấu `users.is_demo=true`. Không nhúng mật khẩu, API_TOKEN hoặc provider key vào frontend. Đây là tài khoản dùng dữ liệu thật của môi trường development: Admin có thể lưu thay đổi vào dự án; User vẫn tuân theo grants, API 403, quota, ảnh private và scope RAG/Agent.

## Bật / tắt trên development

Cần backend đang chạy, migration mới và một Admin cá nhân hoạt động:

```bash
python3 scripts/administration/quick_login.py enable
python3 scripts/administration/quick_login.py disable
```

Trên Docker Snap ở máy này, thêm `ACCOUNTS_USE_SG=1` trước lệnh. Helper chỉ thao tác `.env` development và backend của Compose chính. Lần đầu bật sẽ tạo hai tài khoản trải nghiệm; nếu tên đã thuộc tài khoản thường, setup từ chối và không ghi đè. User trải nghiệm được cấp các thư viện đang hoạt động tại lần tạo đầu. Những lần bật lại giữ các grants đã được Admin chỉnh sửa. Có thể cấp/thu hồi thêm tại Quản trị → Tài khoản.

Lệnh tắt khóa hai tài khoản trải nghiệm, thu hồi phiên và đặt `AUTH_QUICK_LOGIN_ENABLED=false`. Chỉ đặt cờ false cũng chặn các phiên demo ngay từ request kế tiếp. Tài khoản cá nhân và thông tin đăng nhập Admin đã có được giữ nguyên. Khi bật lại, cần đăng nhập nhanh bằng phiên mới. Vai trò hai tài khoản trải nghiệm được cố định; chúng không thay thế Admin cá nhân cuối cùng trong kiểm tra last Admin.

## Giới hạn môi trường

`AUTH_QUICK_LOGIN_ENABLED` mặc định false. Chỉ cho phép `APP_ENV=development/test` và toàn bộ CORS origins là localhost/127.0.0.1/::1. Production hoặc public origin bật cờ sẽ bị từ chối khi khởi tạo; API cũng kiểm tra điều kiện này độc lập. Không dùng chế độ trải nghiệm khi đưa hệ thống lên public hosting.

Bản production-like http://127.0.0.1:8088 tiếp tục đăng nhập tài khoản thông thường; không bật đường tắt Admin ở đó. Tài khoản demo không đăng nhập qua `/auth/login` bằng mật khẩu, và session demo không hợp lệ khi tính năng tắt hoặc trong production.

## API và kiểm chứng

- `GET /api/v1/auth/me` thêm `quick_login_roles: ["admin","user"]` khi đã bật và các tài khoản sẵn sàng; ngược lại `[]`. Snapshot tài khoản thêm `is_demo`.
- `POST /api/v1/auth/quick-login` nhận đúng `{ "role": "admin" | "user" }`, kiểm tra Origin, throttle, tài khoản đã được provision/active/đúng role, rồi cấp session HttpOnly + CSRF như đăng nhập thường. Không cho chỉ định username tùy ý.
- Tắt tính năng trả 404; tài khoản trải nghiệm bị khóa/chưa chuẩn bị trả 409; giới hạn đăng nhập trả 429. Các API sau đó vẫn áp RBAC và ACL thông thường.
- Migration `20261108_quick_login` bổ sung cờ is_demo (mặc định false cho tài khoản cũ), partial unique index cho demo role. Không đổi bảng ảnh, vector manifest hoặc active pointer.

Kiểm thử browser trên môi trường local đã chuẩn bị, chỉ đăng nhập/tìm kiếm/đăng xuất:

```bash
python3 scripts/checks/check_quick_login_browser.py
```

[Báo cáo thực chạy](../verification/quick_login/REPORT.md) · [Phân quyền](../architecture/ACCESS_CONTROL.md) · [Tài khoản cá nhân](ACCOUNTS.md).
