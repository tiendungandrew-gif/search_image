# Nghiệm thu giao diện dễ sử dụng — 09/11/2026

Đã triển khai trên frontend development http://localhost:5173 với backend local và thư viện thật 513 ảnh. [Hướng dẫn sử dụng](../../features/USER_INTERFACE.md). Production-like ở 8088 vẫn dùng release đã triển khai trước đó.

## Thay đổi

- Ba cách tìm nổi bật: **Mô tả**, **Dùng ảnh**, **Kết hợp**. Gợi ý điền mô tả, hướng dẫn ngắn và danh sách thư viện được cấp quyền.
- Thu gọn số kết quả, cách xử lý nâng cao và bộ lọc; đưa nút tìm kiếm lên trước các tùy chọn. Giao diện người dùng không hiện ID ảnh, cosine, fusion weights hoặc các điều khiển vận hành.
- Gallery dùng toàn chiều rộng, nút mở ảnh lớn trên ảnh và tiêu đề; metadata/giấy phép tiếp tục lấy từ API thật.
- Chữ/nút lớn hơn, bố cục điện thoại, focus rõ, thông báo trạng thái/lỗi, bàn phím và reduced motion; cả giao diện sáng/tối.
- Hiện/ẩn mật khẩu; lối tắt Admin đến thư viện, thành viên và tiến trình xử lý ảnh.
- Giữ các kiểu tìm nâng cao ở **Tùy chọn kết quả**. Chuyển về mô tả bỏ ảnh ẩn; **Bắt đầu lại** xóa cả bộ lọc để tránh tìm nhầm phạm vi.

## Kết quả thực chạy

| Kiểm tra | Kết quả | Bằng chứng |
| --- | --- | --- |
| Frontend unit/component | 59/59, 14 file | [test.txt](test.txt) |
| ESLint, không warning | Qua | [lint.txt](lint.txt) |
| TypeScript strict + Vite production build | Qua | [build.txt](build.txt) |
| Chromium 1440 × 1000 | Qua | [browser-all.json](browser-all.json) |
| Chromium mobile 390 × 844 | Qua | [browser-all.txt](browser-all.txt) |
| Chromium mobile 320 × 780 | Qua | [browser-all.txt](browser-all.txt) |
| Firefox 1280 × 900 | Qua | [browser-all.txt](browser-all.txt) |
| Ruff cho browser runner | Qua | `ruff check scripts/checks/check_usability_browser.py` |

Mỗi browser flow đăng nhập nhanh bằng bàn phím, kiểm tra User gọi Admin API nhận 403, chọn thư viện được cấp, tìm ba ảnh thật bằng mô tả/ảnh/kết hợp, mở ảnh bằng Enter, chuyển ảnh bằng phím mũi tên, đóng bằng Esc và khôi phục focus, xóa bộ lọc, chuyển theme, đăng xuất và dùng lối tắt Admin. Không ghi nội dung thư viện, không gửi yêu cầu Gemini trong kiểm thử giao diện.

Axe kiểm tra các tags `wcag2a`, `wcag2aa`, `wcag21aa`, `wcag22aa` tại màn đăng nhập, trang tìm, kết quả, dialog, trang tìm tối, đăng nhập tối, tổng quan Admin và thành viên: không có violation trong các trạng thái đó. Các trạng thái được kiểm tra không tràn ngang. Đây là kiểm tra tự động và bàn phím bằng trình duyệt, chưa phải đánh giá screen reader, thiết bị di động vật lý hoặc chứng nhận WCAG.

## Dữ liệu và cấu hình

[Kiểm kê sau thay đổi](inventory-after.json) vẫn có 513 ảnh, 513 object receipts, 1.054 embeddings sẵn sàng của các index lịch sử, 516 MinIO objects. Active index giữ nguyên generation 3 với 513 points; số embeddings lịch sử không phải số ảnh. Đối chiếu corpus với snapshot đã nghiệm thu ở tác vụ đăng nhập nhanh: không thay đổi counts/jobs/indexes/collections/active pointer/objects.

[preservation.json](preservation.json) xác nhận hash backend auth/access, `.env`, deployment env và stylesheet gốc không đổi so với [baseline](baseline.json). CSS mới nằm riêng trong `discovery.css`. Scan các file ứng viên Git và build assets với các secret local đã cấu hình không thấy giá trị secret trùng khớp. Phiên đăng nhập, audit và bộ đếm sử dụng phát sinh khi kiểm thử là hoạt động bình thường.

## Chạy lại

Từ repo root, khi development đang chạy, có dữ liệu và đăng nhập nhanh đã chuẩn bị:

```bash
backend/.venv/bin/python scripts/checks/check_usability_browser.py
```

Có thể giới hạn `--project desktop`, `mobile`, `narrow` hoặc `firefox`. Cần Node/dependencies và Playwright browsers như môi trường hiện có; runner dùng `scripts/browser_environment.py`. Browser report tại [browser-all.json](browser-all.json); kết quả test/lint/build tại [checks.json](checks.json).

Ảnh chụp để duyệt: [đăng nhập](login-desktop.png), [tìm kiếm desktop](home-desktop.png), [kết quả thật](results-desktop.png), [điện thoại 390 px](home-mobile.png), [màn hình 320 px](home-narrow.png), [chế độ tối điện thoại](dark-mobile.png).
