# Tinh chỉnh thiết kế đăng ký — 19/11/2026

Form đăng ký rộng 520px trên desktop, phân thành hai nhóm thông tin và bảo mật. Tên hiển thị/tên đăng nhập nằm cạnh nhau trên desktop, xếp dọc ở mobile. Đã tinh chỉnh header, badge, viền nhấn, đổ bóng, ô nhập/placeholder/focus, khoảng cách, hướng dẫn quyền thư viện và nút tạo tài khoản. Collage được phủ màu dịu hơn; giữ theme sáng/tối và reduced motion.

Dấu xác nhận độ dài và xác nhận trùng khớp cập nhật khi gõ; không gọi đây là đánh giá độ mạnh mật khẩu. Chỉnh mật khẩu/xác nhận xóa lỗi cũ để tránh thông báo chưa khớp còn tồn tại sau khi sửa. Các kiểm tra phía server và API đăng ký giữ nguyên.

- [70 tests / 17 files](test.txt), [ESLint](lint.txt), [TypeScript/Vite build](build.txt) đều qua.
- [Browser](browser.json), [log](browser.txt), [script](check.mjs): Chromium desktop/mobile 390px/320px và Firefox dark đều qua. Kiểm tra hai cột/một cột, không tràn ngang, focus khi chuyển form, axe không violation, mismatch không gửi API, sửa xác nhận xóa lỗi, hai dấu xác nhận, hiện mật khẩu và quay về đăng nhập.
- Kiểm thử browser không tạo tài khoản trong database chính; luồng tạo thật đã kiểm chứng tại [nghiệm thu đăng ký](../registration/REPORT.md).

Đã xem [desktop](desktop.png); lưu [mobile](mobile.png), [320px](narrow.png), [dark](firefox.png). Không chứng nhận thiết bị vật lý hoặc screen reader. Bản local cập nhật tại http://localhost:5173 → Đăng ký; chưa commit, chưa triển khai 8088.
