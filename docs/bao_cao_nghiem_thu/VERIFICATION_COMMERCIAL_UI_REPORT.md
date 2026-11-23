# Giao diện khám phá ảnh — 10/11/2026

Trang người dùng tại http://localhost:5173 được thiết kế theo phong cách website khám phá ảnh thương mại. Có phần giới thiệu và ảnh ghép thật, ô tìm gọn, gallery ngay khi thư viện sẵn sàng, điều hướng đến các phần chính và bố cục điện thoại. [Hướng dẫn sử dụng](../../features/USER_INTERFACE.md).

## Chức năng đã triển khai

- Ảnh ghép ở desktop; dải ba ảnh trước ô tìm trên điện thoại. Mỗi ảnh lấy từ kết quả API có xác thực, thuộc thư viện mà tài khoản được quyền đọc.
- Gallery **Khám phá thư viện** gợi ý tối đa 12 ảnh qua truy vấn tiếng Anh có sẵn, tôn trọng giới hạn Top-K runtime. Tải một lần khi workspace sẵn sàng, hủy khi rời trang/đổi phiên; lỗi chờ người dùng bấm tải lại. Preview dùng search quota hiện có, không gọi Gemini.
- **Mô tả**, **Dùng ảnh**, **Kết hợp** và các lựa chọn nâng cao tiếp tục dùng API hiện có. Gợi ý **Thiên nhiên**, **Kiến trúc**, **Cà phê** điền câu tiếng Anh; form ghi rõ hướng dẫn ngôn ngữ. Không thêm cơ chế dịch tự động cho câu nhập.
- **Lưới lớn** / **Lưới gọn** thay đổi số cột, giữ nguyên thứ tự kết quả. Ảnh tải gần vùng xem, mở được bằng nút trên ảnh hoặc chú thích; dialog tiếp tục hiển thị ảnh đầy đủ và giấy phép.
- Hướng dẫn và danh sách thư viện chuyển xuống sau gallery. Navbar/footer dẫn đến các phần thật của trang. Quản trị và workspace vận hành giữ bố cục riêng.
- Chuyển đến đầu phần kết quả sau khi tìm để tránh thanh điều hướng che nội dung; focus trở lại nút mở khi đóng dialog. Theme sáng/tối và reduced motion tiếp tục hoạt động.

## Kiểm chứng

| Kiểm tra | Kết quả | Bằng chứng |
| --- | --- | --- |
| Frontend unit/component | 62/62, 15 file | [test.txt](test.txt) |
| ESLint, không warning | Qua | [lint.txt](lint.txt) |
| TypeScript strict + Vite build | Qua | [build.txt](build.txt) |
| Chromium 1440 × 1000 | Qua | [browser-all.json](browser-all.json) |
| Chromium mobile 390 × 844 | Qua | [browser-all.json](browser-all.json) |
| Chromium mobile 320 × 780 | Qua | [browser-all.json](browser-all.json) |
| Firefox 1280 × 900 | Qua | [browser-all.json](browser-all.json) |
| Ruff browser runner | Qua | `ruff check scripts/checks/check_commercial_browser.py` |

Mỗi browser flow kiểm tra đăng nhập nhanh bằng bàn phím, User gọi Admin API nhận 403, preview chỉ chứa nguồn được cấp quyền, đổi lưới giữ thứ tự, cuộn tải đủ 12 ảnh thật, gợi ý tiếng Anh, bộ lọc thư viện và ba loại truy vấn. Dialog được kiểm tra Enter, mũi tên, Esc và khôi phục focus. Sau reset và đổi theme, kiểm tra đăng xuất, lối tắt quản lý thành viên của Admin và Admin quay về trang tìm ảnh.

Axe chạy các tags WCAG 2 A/AA, 2.1 AA, 2.2 AA ở trang đăng nhập, trang khám phá, kết quả, dialog, trang khám phá tối, đăng nhập tối và các trang Admin được đi qua. Các trạng thái này không có violation và không tràn ngang. Kiểm tra bằng trình duyệt tự động chưa thay thế kiểm tra screen reader hoặc thiết bị di động vật lý.

Ba unit tests bổ sung kiểm tra preview không chạy khi chưa sẵn sàng/tôn trọng giới hạn kết quả, phản hồi cũ không hiện sau đổi credentials, hủy request khi unmount và chỉ retry khi người dùng yêu cầu. Các kiểm thử hiện có vẫn xác nhận chuyển về mô tả bỏ ảnh ẩn và reset xóa bộ lọc.

## Phạm vi thay đổi

Mã mới chính: `DiscoveryHero.tsx`, `useDiscovery.ts`, `styles/commercial.css`; tích hợp tại `App`, `SearchWorkspace`, `SearchForm`, `SearchGuide`, `ResultGallery`. CSS mới giới hạn ở `.consumer-site`, được import sau các stylesheet hiện có.

Không thay model, thuật toán retrieval, backend auth/access, migration hoặc nội dung thư viện. [preservation.json](preservation.json) ghi đối chiếu hash backend auth/access, `.env`, deployment env và stylesheet discovery gốc với [baseline](baseline.json). Thao tác browser chỉ đọc/tìm kiếm, tạo phiên và audit/usage thông thường; không gọi provider hoặc ghi nội dung ảnh. Bản production-like 8088 tiếp tục dùng release đã triển khai trước tác vụ.

## Duyệt giao diện và chạy lại

- [Desktop trong một màn hình](viewport-desktop.png), [trang chủ đầy đủ](home-desktop.png).
- [Điện thoại 390 px](viewport-mobile.png), [màn hình hẹp 320 px](viewport-narrow.png).
- [Kết quả tìm kiếm](results-desktop.png), [chế độ tối điện thoại](dark-mobile.png).

Từ repo root khi development có dữ liệu và đã chuẩn bị đăng nhập nhanh:

```bash
backend/.venv/bin/python scripts/checks/check_commercial_browser.py
```

Có thể thêm `--project desktop`, `mobile`, `narrow` hoặc `firefox`. Runner dùng môi trường trình duyệt local trong `scripts/browser_environment.py`. [browser-all.txt](browser-all.txt) và [checks.json](checks.json) lưu kết quả thực chạy. [Báo cáo 09/11](../usability/REPORT.md) giữ bằng chứng của phiên bản trước.
