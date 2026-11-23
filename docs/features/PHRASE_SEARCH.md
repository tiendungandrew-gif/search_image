# Khớp cụm ngắn trong tìm kiếm ảnh

Các truy vấn chữ thông thường ở chế độ auto/text được kiểm tra metadata trước
khi dùng truy xuất vector. Khi có mô tả khớp nguyên cụm ngắn (2–5 từ), hệ thống
trả các ảnh khớp cụm và không bổ sung hàng xóm vector chỉ gần một phần truy vấn.

Ví dụ: `phở gà` khớp mô tả `Tô phở gà nóng hổi...`, không khớp
`Bát phở bò với trứng gà` và không lấy ảnh gà sống để lấp đủ top-k.

- Dùng tài liệu full-text và GIN index hiện có để lấy ứng viên có đủ từ.
  Ưu tiên full-text phrase match trước giới hạn candidate pool.
- Kiểm tra tiếp ở Python: từ phải liền nhau, cùng một trường caption hoặc
  description, không ghép từ cuối caption với đầu description.
- Hỗ trợ gõ không dấu và dấu một phần; giữ nghĩa các từ đã gõ dấu rõ ràng.
- Không coi tên quán trong title là bằng chứng ảnh mô tả đúng món ăn.
  Route tên địa điểm cụ thể vẫn được ưu tiên như trước.
- Không áp dụng chính sách này cho AND/OR, phủ định, filter expression,
  ảnh tham chiếu hoặc yêu cầu advanced/rerank rõ ràng.
- Metadata không khớp cụm: vẫn sử dụng semantic fallback hiện có. Đây không
  phải cơ chế xác minh trực tiếp nội dung thị giác, không bảo đảm mọi truy vấn
  chưa có metadata phù hợp đều có thể được trả lời chính xác.

Ngoại lệ ưu tiên độ chính xác cho cụm món ăn Việt ngắn: khi từ đầu là
`bún/phở/miến/cơm/cháo` (hoặc không dấu), đi kèm nguyên liệu
`gà/bò/heo/lợn/cá`, truy vấn auto/text thông thường không fallback sang vector
khi thiếu cụm khớp. Ví dụ `bun ga` không nhận ảnh gà sống hoặc bún thang chỉ
vì metadata chứa rời rạc cả `bún` và `gà`. Trả rỗng cùng cảnh báo
`FOOD_PHRASE_NOT_FOUND`, route `metadata_food_phrase`, `vector_calls=0`.
Quy tắc giữ dấu đã nhập, không coi `phố` là `phở`, không áp dụng cho
AND/OR/phủ định hoặc chế độ advanced và ảnh tham chiếu. Tên địa điểm khớp
vẫn giữ route riêng. Đây là chính sách dựa trên mô tả, có thể bỏ sót món ăn
được mô tả bằng cách khác; không xác minh nội dung ảnh bằng thị giác.

Route chẩn đoán: `metadata_phrase`, `ranking_version=metadata-phrase-v1`,
`vector_calls=0`. Không cần migration hoặc lập lại chỉ mục ảnh.
Mọi kênh tiếp tục kiểm tra ACL, ảnh bị ẩn/xóa, metadata revision và object receipt.

Câu yêu cầu rõ ràng như `tìm ảnh phở gà`, `tim anh pho ga`,
`show me pictures of phở gà` được bỏ phần mở đầu trước khi tra metadata và
mã hóa vector. Nội dung truy vấn ban đầu vẫn giữ trong `query_analysis.original_query`.
Không bỏ riêng từ `ảnh`/`anh` vì có thể thuộc tên hoặc chủ đề người dùng.

Nhãn ngôn ngữ không còn mặc định tiếng Anh cho chuỗi ASCII. Dấu tiếng Việt
được nhận diện sau chuẩn hóa NFC; chuỗi không dấu dùng bộ nhận diện cục bộ
en/vi với ngưỡng 0.90, còn trường hợp mơ hồ trả `und`. Nhãn này không dịch hay
thay đổi truy vấn. Bộ khôi phục dấu vẫn áp dụng quy tắc bảo thủ riêng; việc nhận
diện ngôn ngữ không thay thế kiểm tra mức phù hợp của kết quả.

Kiểm thử: `backend/tests/unit/test_text_matching.py`,
`backend/tests/integration/test_metadata_search.py` trong QA riêng.
