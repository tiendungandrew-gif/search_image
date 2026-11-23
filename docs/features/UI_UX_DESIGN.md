# Thiết kế giao diện và trải nghiệm — Phase 10

Thiết kế nền tảng dưới đây được giữ theo Phase 10. Giao diện tài khoản hiện tại có trang khám phá ảnh, form gọn, gallery và hỗ trợ điện thoại/bàn phím; xem [cập nhật 10/11/2026](USER_INTERFACE.md).

Giữ tên Lens và bảng màu kem/xanh sage của giao diện hiện có. Giao diện đặt một truy vấn ở trung tâm: nhập lời mô tả, thêm ảnh nếu cần, chọn phương thức, rồi xem gallery theo thứ hạng. Sidebar phân biệt API liveness, hạ tầng và dữ liệu thực. Không chèn ảnh mẫu, score giả, trace giả hoặc nội dung AI cố định vào trải nghiệm thật.

## Các màn hình

| Màn hình | Hành vi |
|---|---|
| `/` | Tìm văn bản, ảnh, đa phương thức, nhiều điều kiện, Agent; controls theo capability |
| Gallery | Rank, ảnh private, caption, kích thước, nguồn, tags, loại điểm và evidence |
| Dialog chi tiết | Ảnh gốc, metadata từ API, ID, ngày tạo, giấy phép, score và evidence |
| Giải thích | Người dùng yêu cầu sau retrieval; giữ nguyên gallery, trạng thái generation và citations |
| Agent | Public events, bước/tool thực, entities, quan hệ, nguồn, trạng thái partial/timeout/error |
| `/evaluation` | Bảng lịch sử benchmark qua API có xác thực; giá trị chưa đo hiển thị rõ |

Form hỗ trợ tiếng Việt/Anh, tối đa 2000 ký tự, Enter để tìm và Shift+Enter để xuống dòng, không gửi khi IME đang composition. Top-K theo runtime, tối đa 50. Image-only không gửi phần text đang giữ trong draft. Auto định tuyến theo loại đầu vào tại backend và kiểm tra capability tương ứng; không tự chuyển truy vấn quan hệ chưa hỗ trợ sang Agent.

Upload hỗ trợ chọn file, kéo thả đúng một file, JPEG/PNG/WebP, kiểm tra MIME/empty/size theo giới hạn backend (hiện 20 MiB), preview, tên, dung lượng và bỏ ảnh. File ảnh chỉ làm query; UI không gọi ingestion. Backend vẫn quyết định tính hợp lệ của bytes.

Advanced controls có dataset, city, MIME, tags-any và giới hạn kích thước; các filters được kết hợp AND trên backend. Fusion có RRF, weighted RRF, weighted score; controls chỉ bật khi có cả text và ảnh. Rerank là tùy chọn. Agent không nhận các metadata filters chưa được contract hỗ trợ. Ngày chụp và trình dựng AST thủ công chưa được đưa lên form; cây AND/OR được hiển thị từ phân tích thực của backend.

Gallery bảo toàn thứ hạng. Không coi cosine/RRF/reranker là xác suất và không so sánh chúng bằng thang phần trăm. Evidence có ba trạng thái: metadata khớp, metadata không khớp, chưa xác minh. Score ngữ nghĩa không đổi trạng thái chưa xác minh thành có bằng chứng. Dialog đóng bằng nút hoặc Escape, chuyển ảnh bằng nút/mũi tên, giữ focus trong modal và trả focus về nút mở. Không bổ sung download/share công khai.

## Loading, empty và lỗi

Skeleton có hình học cố định; skeleton và placeholder không phải kết quả. Ảnh lỗi có nút thử lại có chủ đích. Query không khớp hiển thị khác với database rỗng. Provider quota/timeout không xóa gallery. Hủy yêu cầu không bị ghi thành network error và không có retry AI tự động từ UI.

## Responsive và accessibility

Token CSS trong `styles/index.css` quản lý surface/text/muted/accent/border/error/focus ở cả theme. Breakpoint 1100/800/520 px: sidebar chuyển xuống dưới, controls wrap, gallery thành một cột trên điện thoại, dialog cuộn trong viewport; bảng evaluation cuộn ngang trong region riêng. Ảnh có aspect ratio ổn định, object-fit contain, decoding async và lazy network.

Mục tiêu thực hành WCAG 2.2 AA: label thật, semantic landmark, skip link, focus ring, nút ít nhất 44 px, disabled capability, role/status/alert, modal native, reduced motion, plain text AI và link nguồn HTTPS an toàn. Axe và keyboard được kiểm tra tự động. Chưa có đánh giá NVDA/VoiceOver bởi người dùng, thiết bị iOS/Android vật lý, zoom 400% toàn bộ workflow hoặc chứng nhận WCAG; xem phạm vi chính xác trong [FRONTEND_TESTING.md](../testing/FRONTEND_TESTING.md).
