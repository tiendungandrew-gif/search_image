# Giao diện khám phá ảnh cho người dùng — 19/11/2026

Cập nhật 20/11: bản có chuyển động đã hoàn tất và đạt 8 lượt kiểm tra trình duyệt;
xem [báo cáo mới, ảnh và video](../consumer_motion/REPORT.md). Phần dưới ghi lại
giai đoạn thiết kế gallery ban đầu; log browser hiện đã cập nhật theo bản mới.

Đã tinh chỉnh trang người dùng theo hướng ưu tiên ảnh: bỏ minh họa banner lớn, lời chào gọn, số thư viện được truy cập ở desktop, chip chủ đề và gallery nhiều kích thước. Thanh tìm kiếm vẫn cố định, các cách tìm/filters nằm trong panel hiện có. Giao diện đăng nhập và quản trị giữ bố cục riêng.

## Thay đổi

- Gallery kiểu nhiều cột, ảnh theo tỷ lệ metadata trong giới hạn khung an toàn, bo góc và hover nhẹ. Caption tối đa hai dòng, nguồn thư viện bên dưới; fallback thiếu tiêu đề là “Ảnh trong thư viện”, không đưa ID kỹ thuật lên thẻ người dùng.
- Lưới lớn/gọn có mật độ khác nhau: desktop bốn/năm cột, mobile hai/ba cột. Không sắp xếp lại mảng kết quả; thứ tự đọc là từ trên xuống mỗi cột rồi sang cột tiếp theo. Nhãn thứ hạng vẫn hiện khi tìm kiếm.
- Chủ đề chuyển từ thẻ lớn sang chip, có trạng thái đang chọn; trên mobile vuốt ngang. Chỉ điền mô tả và giữ ảnh/filters hiện có; không tự gửi search khi chọn.
- Bảng màu teal, nền sáng dịu/dark tương phản, font và khoảng cách gọn hơn. Hướng dẫn/thư viện nằm sau gallery. Giữ lazy loading, modal chi tiết và reduced motion; không thêm ảnh giả vào kết quả hoặc thư viện animation.

## Kiểm chứng

| Kiểm tra | Kết quả | Bằng chứng |
| --- | --- | --- |
| Frontend unit/component | 72 pass, 18 files | [test.txt](test.txt) |
| ESLint | Pass | [lint.txt](lint.txt) |
| TypeScript + Vite build | Pass | [build.txt](build.txt) |
| Chromium desktop 1440px | Pass | [browser-all.json](browser-all.json) |
| Chromium mobile 390px | Pass | [browser-all.json](browser-all.json) |
| Chromium narrow 320px | Pass | [browser-all.json](browser-all.json) |
| Firefox 1280px | Pass | [browser-all.json](browser-all.json) |

Lượt cuối 4 pass/0 fail/0 skip, [log](browser-all.txt). Dùng API/CLIP và dữ liệu development thật: User/Admin, preview theo quyền thư viện, gợi ý chuột/phím/IME, chọn chủ đề không tự gửi, đổi mật độ thực sự giảm chiều rộng card và giữ cùng thứ tự IDs, text/image/multimodal, filter thư viện, reset, ảnh private, modal/focus/phím, dark mode và logout. Axe không có violation trong các trạng thái được kiểm tra; không tràn ngang. Không gọi Gemini hoặc sửa ảnh/thư viện/grants.

Lượt đầu có timeout auth API, kỳ vọng màu dark của thiết kế cũ và một ảnh chưa tải trong thời hạn test 5 giây: [log đầu](initial-browser-all.txt), [report đầu](initial-browser-all.json). Probe xác nhận lazy loading vẫn tải khi cuộn vào viewport: [probe](probe.txt). Harness cuối chờ trạng thái đăng nhập sẵn sàng, dùng nút kiểm tra lại kết nối hiện có khi có lỗi, chờ ảnh tối đa 10 giây để bao phủ deadline tải ảnh 8 giây. Đã cập nhật kỳ vọng màu dark theo thiết kế mới. Không đổi timeout runtime, tắt lazy loading hoặc đánh dấu lượt đầu là pass.

Đã xem [desktop](viewport-desktop.png) và [mobile](viewport-mobile.png). Lưu thêm [320px](viewport-narrow.png), [dark](dark-desktop.png), [kết quả tìm](results-desktop.png). Đây là browser emulation, không phải nghiệm thu thiết bị vật lý/screen reader.

## Chạy và kiểm tra lại

Mở http://localhost:5173, đăng nhập User hoặc chọn Vào nhanh User trên development đã bật tài khoản trải nghiệm. User mới tự đăng ký chỉ thấy thư viện chung hoặc được cấp riêng như chính sách hiện có.

```bash
backend/.venv/bin/python scripts/checks/check_consumer_browser.py
```

Runner dùng `frontend/playwright.consumer.config.ts`; hỗ trợ `--project desktop`, `mobile`, `narrow`, `firefox`. Các bằng chứng giao diện cũ được giữ riêng. Không đổi backend/model/index/quyền; chưa commit và chưa triển khai release 8088.
