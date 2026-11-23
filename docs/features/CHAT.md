# Chat riêng giữa các tài khoản

Biểu tượng bong bóng **Tin nhắn** nằm trên thanh dọc cố định bên trái, dưới logo
và các mục điều hướng. Trên desktop, khung chat chiếm cột riêng cao hết màn hình
và đẩy thanh tìm kiếm/lưới ảnh sang phải; nội dung bên cạnh vẫn thao tác được.
Đóng chat trả lại chiều rộng mà không tải lại ảnh. Màn hình nhỏ dùng drawer phủ
phần nội dung, vẫn giữ thanh điều hướng. Chuông thông báo chỉ
hiện chấm đỏ khi có tin chưa đọc, bấm chuông để xem các cuộc trò chuyện chưa đọc.
Đăng nhập tài khoản cá nhân,
chọn **Tin nhắn mới**, tìm tên hiển thị/tên đăng nhập rồi chọn người nhận.
Tài khoản khách và tài khoản trải nghiệm không được đọc hoặc gửi chat.

- Tin nhắn văn bản tối đa 4.000 ký tự, Enter để gửi, Shift+Enter để xuống dòng.
- Nhận ảnh JPEG/PNG/WebP tối đa 10 MB và 25 megapixel; máy chủ loại metadata,
  thu nhỏ cạnh dài tối đa 1.920 px và chuyển JPEG chất lượng 85 trước khi lưu.
- Ảnh chat nằm trong prefix MinIO `chat/`, không nhập vào corpus/index tìm kiếm.
  Chỉ hai người tham gia được tải ảnh qua endpoint có xác thực.
- Lịch sử gần nhất 50 tin, có tải tin cũ. Mã tin nhắn phía client giúp gửi lại
  sau lỗi mạng mà không tạo tin trùng.
- Đánh dấu đã đọc bằng mốc tin nhắn cụ thể trong chính cuộc trò chuyện;
  hộp thư hiển thị số tin chưa đọc. Danh sách trả tối đa 100 cuộc trò chuyện.
- Giới hạn 60 lần gửi/bắt đầu cuộc trò chuyện mỗi phút cho mỗi tài khoản.

## Triển khai và vận hành

Áp dụng migration `20261123_private_chat` bằng quy trình migration hiện có,
khởi động lại backend và build/cập nhật frontend. Development đã áp dụng migration.
Backup cần bao gồm PostgreSQL và các object dưới `chat/` trong bucket private.
Không mở public bucket hoặc dùng đường dẫn ảnh chat như đường dẫn ảnh tìm kiếm.

Bản này dùng HTTP polling: tin mới mỗi 3 giây khi mở cuộc trò chuyện; hộp thư
mỗi 5 giây khi mở menu và 15 giây khi đóng. Tạm dừng khi tab bị ẩn, không cần
Redis hay dịch vụ realtime trả phí. Lưu trữ nằm trong database nên không phụ
thuộc bộ nhớ của một process. Chưa đo tải production với 100 người đồng thời;
cần đo cả chat, upload và tìm kiếm AI trước khi chốt cấu hình máy chủ.

Kiểm thử tích hợp: `backend/tests/integration/test_chat.py` chạy qua QA tách biệt,
bao gồm idempotency, phân trang, chưa đọc, CSRF, ảnh riêng và tài khoản thứ ba.
