# Hồ sơ, ảnh đại diện và ảnh yêu thích

- `/profile`: hồ sơ cá nhân của tài khoản đang đăng nhập. Chỉnh tên hiển thị
  (1–120 ký tự), giới thiệu (tối đa 500 ký tự), thay và xem trước ảnh đại diện.
  Tên đăng nhập không đổi. Trang hồ sơ này không công khai cho khách.
- `/favorites`: bộ sưu tập riêng, tải 24 ảnh/lượt. Nút trái tim nằm trên thẻ ảnh,
  ảnh liên quan và chi tiết ảnh. Có lối vào từ thanh bên và menu tài khoản.
- Avatar chấp nhận JPEG/PNG/WebP tối đa 5 MB và 25 megapixel. Backend giải mã,
  bỏ metadata, cắt giữa thành ảnh vuông JPEG 256×256. Lưu ở prefix `avatars/`
  trong MinIO private; chỉ tài khoản đăng nhập được đọc qua endpoint avatar.
  Avatar cập nhật trong menu tài khoản, thanh bên, danh sách người dùng/chat.
- Tài khoản trải nghiệm không chỉnh hồ sơ hoặc lưu ảnh; khách được mời đăng nhập.

## Quyền truy cập và lưu trữ

Yêu thích chỉ lưu liên kết `user_id` / `image_id`, không sao chép file ảnh.
Lưu lặp cùng ảnh không tạo bản ghi trùng. Xóa yêu thích chỉ tác động dữ liệu
của chính người dùng. Mọi lần liệt kê/count/status kiểm tra lại ảnh available,
chưa xóa, không bị ẩn và thuộc phạm vi thư viện hiện tại. Có thể gỡ yêu thích
ngay cả sau khi quyền xem ảnh bị thu hồi.

Migration: `20261123_profiles_favorites`, sau `20261123_private_chat`. Thêm các
trường `users.bio`, `users.avatar_key` và bảng `image_favorites`; không sửa corpus.
Backup cần bao gồm PostgreSQL và MinIO, kể cả prefix `avatars/`.

Frontend gom truy vấn trạng thái yêu thích thành lô tối đa 50 ảnh, dùng cache
riêng theo tài khoản; mọi mutation cần session/CSRF hiện có. Ảnh đại diện được
đổi URL phiên bản sau mỗi lần cập nhật, tránh hiển thị ảnh cũ từ cache.

Kiểm thử tích hợp: `backend/tests/integration/test_profiles.py` trong QA độc lập.
Kiểm thử frontend: `frontend/src/features/profile/*.test.*`. Kiểm tra trình duyệt
đã bao gồm lưu/bỏ yêu thích và tải lại, chỉnh hồ sơ, tải avatar và mobile.
