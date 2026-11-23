# Trang khách có banner giới thiệu — 20/11/2026

Trang chủ chưa đăng nhập có banner ảnh xếp lớp, giới thiệu tìm kiếm Việt–Anh, nút tập trung vào ô tìm và nút mở đăng nhập. Thành viên tiếp tục dùng lời chào gọn và gallery hiện có. Ảnh banner lấy từ tài nguyên login local; quyền tìm kiếm/public dataset giữ nguyên.

Hoạt ảnh CSS transform có điều khiển tạm dừng/tiếp tục; tự tắt theo prefers-reduced-motion. Bố cục một cột trên điện thoại. Không thêm thư viện animation hay request dịch vụ ảnh.

Kiểm chứng:
- Frontend build đạt, 91 modules.
- Vitest: 78/78 tests, 19 files.
- Guest browser: 4/4 (desktop 1440, mobile 390, narrow 320, Firefox 1280). Kiểm tra banner, focus ô tìm, reduced motion, pause/resume thực tế, Axe WCAG, không tràn ngang, tìm Việt–Anh và login gate.
- Member browser desktop: 1/1; xác nhận banner guest vắng mặt và tìm kiếm thành viên hoạt động.
- git diff --check đạt.

Ảnh: landing-desktop.png, landing-mobile.png, landing-narrow.png, landing-firefox.png.

Lần chạy browser đầu trong sandbox không khởi động được Chromium; chạy lại ngoài sandbox và các kiểm tra đều đạt. Không commit, không deploy 8088.
