# Bình luận ảnh

Bình luận nằm trong cửa sổ chi tiết ảnh, dưới thông tin ảnh và trước phần ảnh
cùng chủ đề. Hiển thị tên tác giả, avatar, thời gian, số bình luận và phân trang
20 bình luận/lượt (mới nhất trước); nút làm mới lấy thay đổi từ người khác.

- Người đăng nhập bằng tài khoản cá nhân được gửi văn bản tối đa 2.000 ký tự.
  Khách chỉ đọc bình luận của ảnh công khai và được mời đăng nhập để gửi.
- Tác giả xóa được bình luận của mình. Quản trị viên xóa được để kiểm duyệt.
- Đọc, gửi và xóa đều kiểm tra ảnh available, chưa xóa/ẩn và quyền thư viện
  hiện tại. Không có ngoại lệ cho ảnh bị ẩn chỉ vì từng bình luận trước đó.
- Session/CSRF hiện có bảo vệ mutation; server luôn lấy tác giả từ phiên đăng
  nhập. Nonce theo tài khoản tránh bình luận trùng khi gửi lại sau lỗi mạng.
- Giới hạn 30 lượt gửi/phút/tài khoản. Nội dung render như văn bản thuần,
  không thực thi HTML và không phân tích Markdown.

Migration `20261123_image_comments` (sau profiles/favorites) thêm bảng
`image_comments`; không thay corpus. Dữ liệu bình luận nằm trong PostgreSQL,
được bao gồm trong backup database. Development đã áp dụng migration và nạp API.

Các API nằm dưới `/api/v1/images/{image_id}/comments`. GET hỗ trợ `before`
để tải trang cũ. POST nhận `body` và `client_id` UUID. DELETE thêm ID bình luận;
quyền xóa được xác minh lại ở server, không phụ thuộc trạng thái nút ở client.

Kiểm thử: `backend/tests/integration/test_comments.py` trong QA độc lập,
`frontend/src/features/search/ImageComments.test.tsx` và `commentsApi.test.ts`.
Đã kiểm tra gửi/đọc/xóa trên hai phiên trình duyệt riêng, tải lại và mobile.
