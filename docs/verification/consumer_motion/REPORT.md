# Chuyển động giao diện — hoàn tất 20/11/2026

Đã thêm vào giao diện người dùng:

- Nội dung chính xuất hiện nhẹ; quầng nền một lượt, không chuyển động liên tục.
- Thẻ ảnh xuất hiện theo thứ hạng, delay tối đa 224 ms; ảnh fade khi decode xong.
- Chủ đề/nút phản hồi hover và nhấn; ảnh zoom nhẹ trong khung.
- Đổi mật độ lưới dùng View Transitions khi browser hỗ trợ, fallback đổi trực tiếp.
- Dialog mở 260 ms, đóng 170 ms, chuyển ảnh nhẹ; giữ thao tác Esc, phím mũi tên
  và cơ chế trả focus. Không trì hoãn đóng ở chế độ giảm chuyển động hoặc ngoài
  giao diện consumer. Timer đóng được hủy khi component unmount.
- `prefers-reduced-motion` tắt animation/transition và đóng dialog ngay.
- Hộp ảnh căn giữa màn hình; hover không lấn phản hồi nhấn nút.

Không thêm thư viện motion, không thay thuật toán tìm, thứ hạng, quyền truy cập
hoặc cơ chế lazy loading. Hiệu ứng chủ yếu dùng transform/opacity; không có
animation layout hoặc tải thêm ảnh trang trí.

## Kiểm chứng

[Build](build.txt), ESLint và `git diff --check` đạt.
[76 frontend unit tests / 19 files](test.txt) đạt. Bốn test mới kiểm tra đóng sau animation,
đóng ngay khi reduced motion, giữ hành vi workspace khác và hủy timer khi rời trang.
Đây là kiểm thử jsdom, không phải bằng chứng render/hiệu năng trên browser thật.

`frontend/consumer-e2e/motion.spec.ts` và bộ acceptance hiện có đã đạt **8 pass,
0 fail, 0 skip, 0 retry** trên Chromium desktop 1440px, mobile 390px, narrow
320px và Firefox 1280px. [Log cuối](browser-all.txt) · [JSON](browser-all.json).

Đã kiểm tra chuyển động bật, hover/nhấn, đổi lưới giữ thứ tự IDs và không gửi lại
search, ảnh decode xong hiện đầy đủ, dialog căn giữa cả hai trục (sai lệch dưới
2px), mở/đóng/đổi ảnh, focus, reduced motion và tràn ngang. Acceptance hiện có
vẫn kiểm tra text/image/multimodal, tìm `con meo` ra mèo, quyền User, thư viện,
ảnh private, theme tối và Axe trong các trạng thái kiểm tra.

Đã xem ảnh chụp [desktop](dialog-desktop.png), [mobile](dialog-mobile.png) và
trích frame video để rà bố cục/chuyển trạng thái. Video bản cuối:
[desktop](preview-desktop.webm), [mobile](preview-mobile.webm),
[320px](preview-narrow.webm), [Firefox](preview-firefox.webm).

Chạy lại:

```bash
backend/.venv/bin/python scripts/checks/check_consumer_browser.py
```

Lượt kiểm tra trước bị lỗi xác thực công cụ; phiên 20/11 đã thực thi được và
kiểm tra đầy đủ bản cuối. Khi xem video lượt đầu đã phát hiện dialog lệch góc
trên; sửa margin căn giữa, bổ sung kiểm tra vị trí và chạy lại toàn bộ 8 ca đạt.

Đây là browser emulation, không phải thử trên điện thoại vật lý hoặc đo FPS/p95.

Chưa commit. Development Vite đang mount source; bản production-like 8088 chưa
được cập nhật.
