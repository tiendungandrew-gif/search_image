# Giao diện tìm kiếm ảnh đa chủ đề — 19/11/2026

Đã đổi trang đăng nhập, header, banner, gallery và hướng dẫn sang khám phá hình ảnh tổng quát tại http://localhost:5173. Banner dùng biểu tượng và hình khối, không dùng ảnh resort. Sáu nhóm gợi ý gồm Thiên nhiên, Động vật, Kiến trúc, Ẩm thực, Con người và Đồ vật; người dùng vẫn nhập được chủ đề bất kỳ.

Gợi ý từ khóa bổ sung các chủ đề chung với tên tiếng Việt có/không dấu và mô tả tiếng Anh. Gợi ý du lịch vẫn có thể tìm như một chủ đề trong nhiều chủ đề. Gallery ban đầu dùng `a photograph` thay truy vấn khách sạn/resort. Chọn chủ đề chỉ điền mô tả; khi có ảnh tham chiếu, chuyển sang kết hợp và giữ ảnh, bộ lọc thư viện.

## Kiểm chứng

- Frontend: 67/67 tests, 16 files; ESLint và TypeScript/Vite build đạt. [Unit/component](test.txt), [build](build.txt).
- Chromium desktop, Chromium 320px và Firefox đạt trong [lượt toàn bộ](browser-all.txt).
- Mobile 390px lần đầu timeout chờ preview search; snapshot lúc đó có các cách tìm chưa sẵn sàng. Không coi lần này là pass. Chạy lại riêng mobile đạt toàn bộ luồng: [kết quả mobile](browser-mobile.txt).
- Browser kiểm tra đăng nhập User/Admin, giới hạn thư viện và User 403, gợi ý/chủ đề không tự gửi, text/image/multimodal, giữ filters/ảnh, đổi lưới, dialog/bàn phím/focus, reset, dark mode và logout. Axe không có violation trong các trạng thái đã kiểm tra, không tràn ngang.
- Unit lần đầu còn kỳ vọng nút Khách sạn cũ: [lượt đầu](test-initial.txt). Đã cập nhật kỳ vọng sang Thiên nhiên; lượt cuối 67/67.

Đã xem ảnh [desktop](viewport-desktop.png) và [320px](viewport-narrow.png); ảnh [mobile](viewport-mobile.png), [đăng nhập](login-desktop.png) và [dark](dark-desktop.png) lưu kèm. Không đánh giá thiết bị vật lý hoặc screen reader.

Backend/model/index/grants không đổi. Không commit; bản production-like 8088 chưa triển khai UI mới. Tên file runner/config `travel` giữ để tương thích lệnh cũ; bằng chứng mới ở thư mục này, báo cáo UI resort cũ được giữ riêng.

Chạy lại trên development có dữ liệu và quick login:

```bash
backend/.venv/bin/python scripts/checks/check_travel_browser.py
```
