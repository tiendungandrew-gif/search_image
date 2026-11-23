# Hoàn thiện giao diện du lịch — 17/11/2026

UI development tại http://localhost:5173 đã hoàn thiện luồng đăng nhập, banner resort, chủ đề khách sạn/nghỉ dưỡng/điểm đến, gợi ý từ khóa và gallery. Backend và dữ liệu thư viện tiếp tục cung cấp kết quả thật theo quyền tài khoản. Mã nguồn chưa commit theo yêu cầu.

## Lỗi đã sửa

Lượt desktop ngày 11/11 dừng ở bước ảnh banner có `naturalWidth = 0`; bằng chứng cũ giữ tại [browser-desktop.txt](browser-desktop.txt). Container Vite chỉ gắn `src` và `index.html`, thiếu `public`. URL banner trả HTTP 200 nhưng nội dung là HTML của SPA. Đã bổ sung bind mount read-only `frontend/public` vào development Compose và recreate riêng frontend.

Dockerfile production cũng thiếu bước copy `public`; đã bổ sung để image mới có ảnh nền và banner. Playwright kiểm tra trực tiếp status, Content-Type và chữ ký PNG trước luồng UI, sau đó xác nhận ảnh decode được trong trình duyệt.

## Kiểm chứng

| Kiểm tra | Kết quả | Bằng chứng |
| --- | --- | --- |
| Vitest unit/component | 67/67, 16 file | [test.txt](test.txt) |
| ESLint | Qua, không warning | [lint.txt](lint.txt) |
| TypeScript + Vite build | Qua | [build.txt](build.txt) |
| Chromium desktop 1440 × 1000 | Qua | [browser-all.json](browser-all.json) |
| Chromium mobile 390 × 844 | Qua | [browser-all.json](browser-all.json) |
| Chromium narrow 320 × 780 | Qua | [browser-all.json](browser-all.json) |
| Firefox 1280 × 900 | Qua | [browser-all.json](browser-all.json) |
| Docker frontend production | Build qua; có index và PNG, checksum khớp nguồn và Vite dist | [packaging.json](packaging.json) |

Browser chạy trên API và CLIP hiện có: đăng nhập User/Admin, User bị chặn Admin API (403), preview theo quyền thư viện, gợi ý không gửi search khi gõ/chọn, chọn chủ đề không tự gửi, đổi lưới giữ thứ tự, tìm text/image/multimodal và lọc thư viện, dialog/focus/phím, reset, theme tối và đăng xuất. Axe kiểm tra các trạng thái được chọn không có violation; không tràn ngang. Tổng 4 pass, 0 fail, 0 skip; log tại [browser-all.txt](browser-all.txt).

Ảnh kiểm tra trực quan: [desktop](viewport-desktop.png), [mobile](viewport-mobile.png), [320 px](viewport-narrow.png), [đăng nhập](login-desktop.png) và [giao diện tối](dark-desktop.png).

## Phạm vi nghiệm thu

Ảnh resort là minh họa, không nhập vào index hoặc kết quả tìm kiếm. Không thay model, backend, grants hay nội dung thư viện. Không gọi Gemini để kiểm thử. Image `ai-image-search/frontend:travel-ui-check` chỉ dùng kiểm chứng đóng gói; bản production-like ở 8088 chưa được cập nhật. Kiểm thử không chấm chất lượng relevance, thiết bị vật lý hoặc screen reader.

Chạy lại khi development đã có dữ liệu và đăng nhập nhanh:

```bash
backend/.venv/bin/python scripts/checks/check_travel_browser.py
```

Có thể chọn riêng `--project desktop`, `mobile`, `narrow` hoặc `firefox`.
