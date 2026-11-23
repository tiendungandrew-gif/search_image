# Thiết kế nút Đăng nhập / Đăng ký — 19/11/2026

Chỉnh riêng kiểu trình bày các nút tài khoản. Nút gửi form Đăng nhập/Tạo tài khoản dùng nền chuyển sắc teal, viền và bóng nhẹ, mũi tên trên nền tròn. Nút chuyển Đăng ký/Đăng nhập được nâng từ chữ gạch chân thành nút viền đủ chiều rộng, cùng chiều cao/bo góc và biểu tượng. Có hover/press/focus-visible, trạng thái disabled dễ đọc, dark theme và reduced motion. Không đổi endpoint hay luồng xác thực.

Kiểm chứng: [70 test frontend](test.txt), [lint](lint.txt), [TypeScript/Vite build](build.txt) đều đạt. [Browser matrix](browser.json) trên Chromium desktop/mobile 390px/320px và Firefox dark đạt: nút chính disabled/enabled theo input, nút chuyển cao tối thiểu 44px, điều hướng qua lại, không tràn ngang và axe không violation. [Log](browser.txt), [script](check.mjs). Không submit tài khoản/mật khẩu hoặc tạo dữ liệu khi kiểm chứng browser.

Đã xem [desktop](login-desktop.png); lưu [mobile](login-mobile.png), [dark](login-firefox.png), [nút ở form đăng ký](signup-desktop.png). Code local ở http://localhost:5173; chưa commit, chưa cập nhật deployment 8088.
