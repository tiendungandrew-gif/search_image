# Nghiệm thu đăng nhập nhanh hai vai trò

08/11/2026. Hai nút **Vào nhanh Admin** / **Vào nhanh User** đã được bổ sung trên màn hình đăng nhập development. Admin đi thẳng `/admin`, User đi `/`. Tài khoản cá nhân vẫn dùng form đăng nhập cũ. Xem [hướng dẫn bật/tắt](../../operations/QUICK_LOGIN.md).

## Phạm vi triển khai

- Tạo riêng demo_admin/demo_user, có cờ is_demo, không dùng mật khẩu/API key nhúng trong frontend.
- Feature flag mặc định tắt; chỉ cho localhost development/test. Settings từ chối flag trên production/public origin, API cũng tự kiểm tra lại điều kiện này.
- Session/CSRF/throttle/RBAC/ACL dùng cơ chế hiện có. Phiên demo bị chặn khi tính năng tắt, tài khoản khóa hoặc chạy production.
- Demo Admin không được tính như Admin cá nhân cuối cùng. Không thể đổi role hai tài khoản demo bằng API quản trị; User có grants thực và vẫn bị chặn API Admin.
- Helper enable/disable xử lý idempotent, không ghi đè tên thuộc tài khoản cá nhân, không tự khôi phục các grants đã bị Admin thu hồi.
- Development localhost:5173 đã bật sẵn. Bản production-like localhost:8088 tiếp tục đăng nhập thường bằng image release cũ; không triển khai đường tắt Admin ở đó.

## Kiểm tra thực chạy

| Kiểm tra | Kết quả |
| --- | --- |
| Backend unit/security/reliability | 257 pass |
| Integration PostgreSQL/Qdrant/MinIO | 19 pass; có 3 ca quick-login mới |
| Frontend unit | 54 pass |
| TypeScript, ESLint, production frontend build | Pass |
| Ruff check/format và Python compile | Pass |
| Browser desktop/mobile | 2 pass, gồm Admin/User, route, session HttpOnly, 403, tìm 3 ảnh và đăng xuất; axe không vi phạm |
| Dữ liệu và secrets | 513 ảnh/index/objects/jobs giữ nguyên, production env/encoder/decoder giữ nguyên, không có secret match |

Các ca mới xác nhận: feature default off; chặn production/public origin kể cả cấu hình bị sửa bằng chương trình; input role/username không hợp lệ; Origin giả; khóa tài khoản; revoke session; last Admin thật; User 403; grant bị thu hồi giữ nguyên qua lần bật lại; login throttle; đăng nhập bằng mật khẩu tài khoản thật; không đưa password/hash vào response; loading/error/retry ở hai nút. Browser dùng dịch vụ thật và CLIP hiện có để User tìm ảnh, kiểm tra ảnh private, chuyển vai trò và đăng xuất. Không dùng ca này để chấm relevance/RAG.

Migration `20261108_quick_login` chỉ bổ sung users.is_demo mặc định false và partial unique index. Trước rollout có pg_dump hợp lệ (pg_restore --list pass) tại `.cache/auth/backups/before-quick-login-main.dump`, quyền 0600. Chụp inventory lần đầu bị gián đoạn do backend được recreate khi lệnh chụp còn chạy; backup đã tạo trước đó và đã xác minh, inventory được chụp lại khi backend healthy. Không đánh dấu lần bị gián đoạn là pass. Một lỗi type trong test frontend (tham số exact của Testing Library) đã sửa; bảng trên dùng lượt chạy cuối.

Quick login là tài khoản trải nghiệm local dùng dữ liệu hiện có; các thay đổi Admin thực hiện được lưu vào dự án. Chính sách thư viện/ảnh và quyền truy cập vẫn áp dụng ở backend. Giao diện production ở cổng 8088 không được bật tính năng này.
