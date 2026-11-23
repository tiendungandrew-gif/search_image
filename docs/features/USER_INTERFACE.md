# Giao diện tìm kiếm ảnh đa chủ đề — 20/11/2026

Mở http://localhost:5173 để tìm và xem ảnh công khai ngay khi chưa đăng nhập.
Bấm **Đăng nhập** hoặc mở `/login` để dùng tài khoản cá nhân, đăng ký hoặc dùng
**Vào nhanh User** / **Vào nhanh Admin** khi development đã bật
[đăng nhập nhanh](../operations/QUICK_LOGIN.md). Khách chọn **Tìm bằng ảnh** sẽ
được đưa sang đăng nhập. Bộ lọc/thư viện trên trang khách chỉ có dữ liệu công khai.

## Trang giới thiệu dành cho khách

Khi chưa đăng nhập, trang chủ có banner **Hình dung điều bạn thích. Để Lens tìm thấy.**, ảnh mẫu xếp lớp (mèo, cà phê, thiên hà) và phần giới thiệu tìm kiếm Việt–Anh, ảnh công khai và quyền lợi thành viên. Ảnh trang trí là tài nguyên local đã có của trang đăng nhập; không phải kết quả tìm kiếm hay dữ liệu thư viện riêng.

**Thử tìm ảnh ngay** đặt con trỏ vào ô tìm kiếm hiện có; **Khám phá cùng Lens** mở đăng nhập/đăng ký. Banner không thay đổi phạm vi ảnh công khai. Sau đăng nhập, banner nhường chỗ cho lời chào gọn và không gian tìm ảnh của thành viên.

Các ảnh nổi nhẹ bằng CSS transform; nút **Tạm dừng hoạt ảnh** / **Bật hoạt ảnh** điều khiển chuyển động. Khi thiết bị bật `prefers-reduced-motion`, hoạt ảnh tự tắt và nút điều khiển được ẩn. Bố cục chuyển thành một cột trên điện thoại.

## Thanh tìm kiếm và gợi ý

Ô tìm kiếm nằm trên thanh đầu trang và luôn có thể dùng khi cuộn gallery. Nhập ít nhất hai ký tự để nhận gợi ý từ khóa: ví dụ `forest`, `cat`, `thiên nhiên`, `ca phe` hoặc `kiến trúc`. Gợi ý dùng một danh sách từ khóa chung về nhiều chủ đề trong frontend, hỗ trợ so khớp có/không dấu; không truy cập lịch sử tìm kiếm hoặc metadata riêng của tài khoản và không gọi API khi gõ.

- Bấm một gợi ý để điền mô tả tiếng Anh tương ứng. Thao tác này chưa gửi tìm kiếm.
- Dùng ↑ / ↓ để chọn; Enter điền gợi ý đang chọn. Enter lần nữa hoặc nút kính lúp gửi yêu cầu tìm ảnh.
- Esc đóng danh sách, giữ nội dung đã gõ; Tab rời ô cũng đóng danh sách.
- Không có gợi ý phù hợp thì vẫn có thể nhập và tìm tự do. Từ khóa chung không cam kết thư viện hiện có đủ ảnh tương ứng.

Nút **Tìm bằng ảnh** mở phần chọn ảnh tham chiếu. Nút **Tùy chọn tìm kiếm** mở các chế độ **Mô tả / Dùng ảnh / Kết hợp**, bộ lọc, số kết quả và **Bắt đầu lại**. Các lựa chọn này dùng cùng trạng thái với ô tìm trên thanh đầu; không có một form riêng trong phần giới thiệu.

## Trang chủ

Trang người dùng có thanh tìm kiếm cố định, lời chào **Một ý tưởng, nhiều góc nhìn.** gọn và gallery **Khám phá thư viện** được đưa lên gần đầu trang. Số thư viện được chia sẻ hiện ở desktop. Gallery dùng ảnh thật từ API theo quyền tài khoản, không có ảnh trang trí trộn vào kết quả.

Các nhóm **Thiên nhiên**, **Động vật**, **Kiến trúc**, **Ẩm thực**, **Con người**, **Đồ vật** là chip gợi ý; chọn sẽ điền mô tả, đánh dấu chủ đề tương ứng nhưng chưa gửi tìm kiếm. Người dùng vẫn nhập được bất kỳ chủ đề nào. Trên mobile có thể vuốt ngang dải gợi ý.

Gallery ban đầu tìm tối đa 12 ảnh bằng truy vấn chung `a photograph`, trong giới hạn Top-K runtime. Preview không gọi Gemini và không tự retry khi lỗi; có nút tải lại. Thư viện rỗng/chưa sẵn sàng không phát sinh preview search.

**Lưới lớn** / **Lưới gọn** thay đổi mật độ ảnh, giữ nguyên dữ liệu và thứ tự từ API. Bố cục nhiều cột xếp ảnh từ trên xuống mỗi cột, rồi chuyển sang cột kế; kết quả tìm kiếm có nhãn thứ hạng. Desktop mặc định bốn cột, gọn năm cột; mobile hai hoặc ba cột. Tỷ lệ thumbnail dựa trên kích thước ảnh, giới hạn khung quá dài/rộng; mở chi tiết để xem ảnh đầy đủ.

Caption gọn tối đa hai dòng và nguồn thư viện nằm dưới ảnh; khi thiếu tiêu đề/caption hiển thị **Ảnh trong thư viện** thay mã kỹ thuật. Ảnh tải gần viewport, cửa sổ chi tiết có metadata/nguồn/giấy phép và điều hướng bàn phím.

## Tìm ảnh

| Cách tìm | Thao tác |
| --- | --- |
| **Mô tả** | Viết điều bạn nhớ, hoặc bấm một gợi ý để điền mô tả, rồi chọn **Tìm kiếm ảnh**. |
| **Dùng ảnh** | Chọn hoặc kéo thả một ảnh JPEG, PNG, WebP để tìm ảnh tương tự. |
| **Kết hợp** | Thêm ảnh tham chiếu và mô tả điều bạn muốn tìm. |

Chọn gợi ý chỉ điền mô tả tiếng Anh; người dùng chủ động gửi tìm kiếm. Chọn chủ đề trong chế độ **Dùng ảnh** chuyển sang **Kết hợp** và giữ ảnh tham chiếu. Câu nhập tự do không được tự dịch. Ảnh tham chiếu không tự thêm vào thư viện. Chuyển về **Mô tả** bỏ ảnh cũ.

**Tùy chọn kết quả** cho phép đổi số ảnh và chọn cách tìm theo nhiều điều kiện hoặc theo mối liên hệ. **Thư viện và bộ lọc** giới hạn thư viện, thành phố, thẻ, định dạng và kích thước theo metadata đã lưu. Các mục này mặc định thu gọn. **Bắt đầu lại** xóa mô tả, ảnh tham chiếu và bộ lọc, đưa số kết quả về 10 và chọn lại **Mô tả**.

Gallery nằm dưới lời chào và dải gợi ý, dùng toàn bộ chiều rộng. Bấm ảnh hoặc tiêu đề để xem ảnh lớn, chú thích, nguồn thư viện và giấy phép. Nút **Sửa tìm kiếm** đưa về ô tìm. Giải thích AI vẫn cần người dùng bấm yêu cầu sau khi nhận ảnh.

## Tài khoản và quản trị

Form đăng ký chia thành **Thông tin cá nhân** và **Bảo mật tài khoản**; hai ô tên đặt cạnh nhau trên desktop và xếp dọc trên mobile. Có hướng dẫn ngay trong form và dấu xác nhận khi mật khẩu đủ độ dài/trùng khớp. [Ảnh và kiểm chứng thiết kế](../verification/registration_design/REPORT.md).

Chọn **Đăng ký** dưới form để tạo tài khoản bằng tên hiển thị, tên đăng nhập, mật khẩu từ 12 ký tự và xác nhận. Đăng ký xong trở về đăng nhập với tên được điền sẵn; tài khoản mới dùng ngay thư viện chung cho thành viên; thư viện riêng cần Admin cấp thêm. [Hướng dẫn tài khoản](../operations/ACCOUNTS.md).

Trang đăng nhập dùng form nổi ở giữa trên nền collage ảnh đa chủ đề cuộn chậm, lớp phủ teal giúp dễ đọc. Form tài khoản nằm trước hai nút trải nghiệm Admin/User. Nền dùng ảnh mẫu công khai, không đọc thư viện riêng khi chưa đăng nhập. Nút **Tạm dừng chuyển động** / **Bật chuyển động** điều khiển hiệu ứng; khi thiết bị chọn giảm chuyển động, nền đứng yên. Desktop có bảy cột ảnh, mobile ba cột và form co giãn theo màn hình. [Kiểm chứng collage](../verification/login_collage/REPORT.md).

Thanh đầu trang có **Tìm ảnh**, tài khoản, nút chuyển giao diện sáng/tối và **Đăng xuất**. Trên điện thoại, nút theme và tài khoản dùng biểu tượng có tên truy cập cho trình đọc màn hình. Form đăng nhập có **Hiện mật khẩu** / **Ẩn mật khẩu**.

Admin có mục **Quản trị** riêng. Trang tổng quan thêm lối tắt **Thêm và quản lý ảnh**, **Quản lý thành viên**, **Theo dõi xử lý ảnh** đến các trang hiện có. User chỉ thấy các thư viện được cấp; quyền đọc/ghi và phạm vi tìm kiếm tiếp tục do backend kiểm tra. Xem [tài khoản và phân quyền](../operations/ACCOUNTS.md).

## Bàn phím và màn hình nhỏ

- Dùng Tab / Shift+Tab để chuyển điều khiển; Enter hoặc Space để kích hoạt nút, mở mục thu gọn.
- Ô tìm trên thanh đầu là ô một dòng: Enter chọn gợi ý đang được đánh dấu hoặc gửi tìm kiếm nếu chưa chọn gợi ý; không xử lý Enter khi đang ghép ký tự bằng IME.
- Trong cửa sổ ảnh: ← / → chuyển ảnh, Esc đóng; focus trở về nút đã mở ảnh.
- Có liên kết bỏ qua thanh điều hướng, focus ring, nhãn thật, trạng thái/lỗi được thông báo, và hỗ trợ reduced motion.
- Gallery đổi số cột theo màn hình và chế độ lưới. Hướng dẫn được đặt sau gallery để ưu tiên nội dung ảnh.

## Mã nguồn và kiểm chứng

`SearchForm`, `SearchGuide`, `SearchWorkspace` quản lý trải nghiệm tìm kiếm; `SearchAutocomplete` và `searchSuggestions` xử lý gợi ý. `SearchForm` được đưa lên header bằng React portal để giữ một trạng thái truy vấn/bộ lọc. `useDiscovery` tải preview có giới hạn và hủy khi rời trang/đổi phiên; `GalleryView` đổi mật độ ảnh, `TravelThemes` cung cấp chip chủ đề. `ResultImage` và `ImageDetailDialog` xử lý xem ảnh. `styles/consumer-gallery.css` tinh chỉnh giao diện người dùng trên nền `travel.css`, `commercial.css` và `navbar-search.css`; các tùy chọn kỹ thuật vẫn có ở workspace vận hành. Docker development gắn `frontend/public` để cập nhật ảnh tĩnh; Dockerfile production copy thư mục này vào build. Bản thiết kế [Phase 10](UI_UX_DESIGN.md) mô tả nền tảng ban đầu.

Chạy kiểm thử giao diện thật trên development có dữ liệu và đăng nhập nhanh đã chuẩn bị:

```bash
backend/.venv/bin/python scripts/checks/check_consumer_browser.py
```

Kiểm thử chỉ đăng nhập, tìm ảnh, đọc thông tin và đăng xuất. Có Chromium desktop/mobile/320 px và Firefox, kiểm tra gợi ý khi gõ, chọn chủ đề, chuột/phím lên xuống, axe ở cả theme sáng/tối, cuộn tải ảnh, đổi lưới, bộ lọc thư viện, ba cách tìm, và các lối tắt Admin. [Báo cáo gallery người dùng](../verification/consumer_ui/REPORT.md) ghi kết quả hiện tại; kiểm tra tự động không thay thế đánh giá bằng thiết bị hoặc trình đọc màn hình thực. [Báo cáo thanh tìm kiếm](../verification/navbar_search/REPORT.md) và [báo cáo giao diện khám phá](../verification/commercial_ui/REPORT.md) giữ bằng chứng của phiên bản trước.
