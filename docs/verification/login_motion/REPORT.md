# Chuyển động trang đăng nhập — 19/11/2026

Đã bổ sung nền gradient chuyển động chậm, đường nét xoay nhẹ, ba thẻ minh họa nổi, hiệu ứng xuất hiện form và phản hồi hover/press cho nút. Artwork dùng HTML/CSS và SVG hiện có, không tải thêm ảnh, video hoặc thư viện animation. Các animation liên tục chỉ thay đổi transform; không di chuyển form hoặc làm thay đổi bố cục.

Nút Tạm dừng chuyển động/Bật chuyển động có trạng thái aria-pressed; dừng animation toàn trang đăng nhập. Khi prefers-reduced-motion=reduce, animation/transition tắt và ẩn nút điều khiển. Mobile 390px/320px ẩn artwork lớn, giữ nền chuyển động nhẹ. Các hiệu ứng nằm trong trang đăng nhập; auth/session và dữ liệu không đổi. Chưa commit và chưa triển khai production-like.

Kiểm chứng frontend: [67/67 unit/component](test.txt), [lint](lint.txt), [TypeScript/Vite build](build.txt) đều qua. Browser kiểm tra transform thực sự thay đổi, pause giữ vị trí, resume, reduced motion, mobile không tràn ngang, axe, hiện/ẩn mật khẩu, quick login User và đăng xuất. [Kết quả browser](browser.json), [log](browser.txt), [script kiểm chứng](check.mjs).

Lượt harness đầu thiếu browser context riêng cho axe; lượt thứ hai đọc transform trên Firefox trước khi browser hoàn tất frame pause. Script cuối chờ hai animation frames trước khi đo trạng thái dừng; không thay thời lượng hoặc hiệu ứng để che kết quả. Bằng chứng các lượt trước giữ tại browser-initial.txt và browser-second.txt.

Ảnh: [desktop](desktop.png), [mobile](mobile.png), [320px](narrow.png), [Firefox](firefox.png). Screenshot tĩnh không thể hiện chuyển động; mở http://localhost:5173 và đăng xuất để xem trang đăng nhập.
