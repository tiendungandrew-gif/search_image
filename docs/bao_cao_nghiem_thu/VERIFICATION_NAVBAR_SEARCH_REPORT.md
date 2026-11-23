# Thanh tìm kiếm và gợi ý khi gõ — 10/11/2026

Đã chuyển form tìm kiếm của người dùng lên thanh đầu trang tại http://localhost:5173. Ô nhập, nút tìm, nút tìm bằng ảnh và nút tùy chọn nằm trong cùng thanh cố định. Bộ lọc, số kết quả và chế độ tìm mở trong panel. Dùng React portal để giữ một trạng thái truy vấn/ảnh/bộ lọc; phần giới thiệu không còn form thứ hai.

## Gợi ý từ khóa

Gõ từ hai ký tự để nhận tối đa năm gợi ý phù hợp từ danh sách từ khóa chung trong frontend. Có so khớp tiếng Anh và tiếng Việt có/không dấu (`coffee`, `cà phê`, `ca phe`, `cat`, `meo den`). Danh sách này không lấy lịch sử hoặc metadata riêng của người khác và không gọi API/provider khi gõ. Câu nhập tự do không được tự dịch; có thể gửi tìm kiếm dù không có gợi ý.

Click hoặc ↑/↓ rồi Enter điền mô tả tiếng Anh, chưa gửi tìm kiếm. Enter tiếp theo hoặc nút tìm mới gửi yêu cầu. Esc giữ nguyên câu đã gõ và đóng danh sách; Tab hoặc click ra ngoài cũng đóng. Có xử lý IME, combobox/listbox/active descendant và cuộn gợi ý đang chọn vào vùng nhìn thấy.

## Kiểm chứng thực chạy

| Kiểm tra | Kết quả | Bằng chứng |
| --- | --- | --- |
| Frontend unit/component | 67/67, 16 file | [test.txt](test.txt) |
| ESLint | Qua, không warning | [lint.txt](lint.txt) |
| TypeScript + Vite build | Qua | [build.txt](build.txt) |
| Chromium 1440 × 1000 | Qua | [browser-all.json](browser-all.json) |
| Chromium mobile 390 × 844 | Qua | [browser-all.json](browser-all.json) |
| Chromium mobile 320 × 780 | Qua | [browser-all.json](browser-all.json) |
| Firefox 1280 × 900 | Qua | [browser-all.json](browser-all.json) |
| Ruff browser runner | Qua | `ruff check scripts/checks/check_navbar_browser.py` |

Browser kiểm tra ô nhập thực sự nằm trong header, gợi ý xuất hiện khi gõ, chọn bằng chuột/phím, Esc giữ nội dung và số request search phát sinh khi gõ/chọn gợi ý bằng 0. Luồng tiếp tục kiểm tra text/image/multimodal với ảnh và API thật, giữ bộ lọc thư viện, reset, dialog/focus, theme, User nhận 403 ở Admin API, Admin và đăng xuất. Đã kiểm tra axe trong thanh tìm khi danh sách gợi ý mở và trong các trạng thái trang/modal chính; không có violation ở các trạng thái được kiểm tra, không tràn ngang. Chưa đánh giá với screen reader hoặc điện thoại vật lý.

Unit tests kiểm tra ánh xạ từ khóa, Unicode có/không dấu, giới hạn gợi ý, từ không có trong danh sách, Enter chọn rồi gửi, Esc/Tab/click và giữ ảnh/bộ lọc khi gửi từ header.

## Mã nguồn và phạm vi

`SearchAutocomplete.tsx`, `searchSuggestions.ts`, `navbar-search.css`; tích hợp trong `App`, `SearchWorkspace`, `SearchForm`. Các workspace quản trị/vận hành vẫn tách riêng. Không thay backend, model, quyền truy cập hoặc dữ liệu thư viện; không gọi Gemini trong các lượt kiểm tra này. Bản development dùng code mới, bản production-like 8088 giữ release đã triển khai.

Kiểm thử gần đây về quick login/usability/commercial đã cập nhật thao tác mở panel cho layout mới; bằng chứng lịch sử của các lần chạy trước giữ nguyên. Kết quả hiện tại ở [browser-all.txt](browser-all.txt) và [checks.json](checks.json).

Ảnh chụp: [thanh tìm trên desktop](viewport-desktop.png), [gợi ý trên desktop](autocomplete-desktop.png), [gợi ý trên điện thoại](autocomplete-mobile.png), [màn hình 320 px](viewport-narrow.png).

Chạy lại khi development có dữ liệu và đăng nhập nhanh đã chuẩn bị:

```bash
backend/.venv/bin/python scripts/checks/check_navbar_browser.py
```

Có thể thêm `--project desktop`, `mobile`, `narrow` hoặc `firefox`. [Hướng dẫn sử dụng](../../features/USER_INTERFACE.md).
