# Đăng nhập với nền collage — 19/11/2026

Form Lens bo góc nằm giữa nền ảnh nhiều kích thước, lấy cảm hứng từ cách trình bày ảnh của Pinterest. Desktop hiển thị bảy cột, tablet năm cột và mobile ba cột. Các cột cuộn chậm theo hai hướng, có lớp phủ teal để form dễ đọc. Form đăng nhập chính xuất hiện trước hai nút trải nghiệm Admin/User; vẫn giữ hiện/ẩn mật khẩu, lỗi/loading và liên hệ quản trị viên.

Nền là ảnh mẫu công khai được sao chép nguyên bản từ bộ scikit-image đã có trong project; nguồn và giấy phép giữ tại `frontend/public/images/login/credits.json`. Không gọi API thư viện khi chưa đăng nhập, không đưa ảnh riêng vào public assets. Không thêm dịch vụ ảnh ngoài, video hoặc thư viện animation. Các ảnh lặp lại dùng chung URL/cache trình duyệt.

Nút dừng/bật chuyển động hoạt động cho collage; reduced motion tắt animation. Lớp ảnh trang trí có aria-hidden và không nhận thao tác chuột/bàn phím. Tab từ logo đi vào tên đăng nhập; form giữ tương phản bằng nền đặc.

## Kiểm chứng

- [67/67 frontend unit/component](test.txt), [ESLint](lint.txt), [TypeScript/Vite build](build.txt) đạt.
- [Browser matrix](browser.json): Chromium desktop 1440px, mobile 390px, narrow 320px và Firefox 1280px đều đạt. [Log](browser.txt), [script](check.mjs).
- Kiểm tra ảnh decode thật, nền thực sự chuyển động, dừng giữ vị trí, bật lại, reduced motion, không tràn ngang, thứ tự Tab, hiện/ẩn mật khẩu, axe không violation, quick login User và đăng xuất.
- Đã xem trực quan [desktop](desktop.png) và [mobile](mobile.png); lưu thêm [320px](narrow.png) và [Firefox](firefox.png). Chưa kiểm chứng thiết bị vật lý/screen reader.

Lượt lint đầu phát hiện script kiểm chứng tạm của lần trước còn trong `frontend/test-results`. Đã xóa đúng file tạm do agent tạo (bản kiểm chứng lưu ở tài liệu), chạy lại lint đạt. Không thay rule ESLint để bỏ lỗi.

Backend/model/index/grants giữ nguyên. Chưa commit; bản production-like 8088 chưa cập nhật.
