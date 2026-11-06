# Triển khai RAG — Prompt08

## Evidence thực

EvidenceRetriever tái sử dụng ImageRepository.candidates: available image, ready embedding, đúng index/hash/metadata_revision, original receipt chưa xóa. Qdrant payload phải khớp UUID/index/model manifest/source hash/revision, MinIO stat xác nhận original theo policy hiện hành. Truy vấn metadata/tags theo batch, không N+1 SQL. IDs trùng bị loại; ảnh không còn đủ điều kiện bị loại và cảnh báo. Không GET ảnh để gửi sang LLM hoặc tự tạo caption/tag.

Caption có caption_source; tag có source/verified; metadata có PostgreSQL provenance, revision và manifest. Caption máy không thành visual truth. Chỉ đưa những trường cho phép vào context; extra JSON/relational entities/OCR chưa có không được tự điền. Context không coi filenames/title/scores là mô tả nội dung ảnh. Caption chứa mẫu chỉ dẫn đáng ngờ hoặc trường quá dài bị bỏ toàn bộ; không cắt một nửa câu rồi coi là claim mới.

## Grounding được triển khai

LLM chọn fact_ids từ context thật, không được xuất câu tự do. Server xác minh schema/IDs, dựng citations và câu tiếng Việt/Anh từ nguyên văn giá trị metadata. Đây là RAG trích xuất có kiểm soát; không phải bộ suy luận thị giác hoặc trình đánh giá semantic relevance. Trích dẫn đúng nguyên văn ngăn tạo mô tả mới, nhưng không chứng minh caption nguồn là đúng với pixel hoặc câu trả lời giải quyết hết câu hỏi.

supported: chỉ các trường kỹ thuật có thật như width/height/media_type/source_dataset/license, khi câu hỏi về metadata. partially_supported: mô tả/caption/tag được trích đúng nhưng chưa xác minh thị giác. insufficient_evidence: không có fact hữu ích hoặc model không chọn được fact. generation_unavailable: RAG tắt, thiếu config, overload, timeout/provider error hoặc output/citations không hợp lệ. Không dùng status do model tự khai báo.

## Lifecycle và lỗi

RAG_ENABLED=false mặc định; provider instance chỉ tạo khi bật. Một HTTP pool riêng, giới hạn concurrent calls, không hàng chờ vô hạn. Retry mặc định0, tối đa1 chỉ cho429/500/502/503 trước body, vẫn trong total generation deadline. Hủy/disconnect đóng HTTP stream; dừng tính phí phía provider là best effort. Không retry sau khi đã nhận token. Không log prompt/response/key.

API timeout riêng cho RAG, Fast Search giữ timeout2s. Generation timeout trả ảnh đã truy xuất và mã LLM_TIMEOUT thay vì câu trả lời bịa. Semantic Search errors vẫn được trả đúng; không giấu search failure thành kết quả rỗng. Token usage là số provider báo, thiếu thì null. Các mẫu kỹ thuật trong bounded in-memory ring không chứa query/caption/headers.

## Cấu hình Gemini/OpenAI

Gemini mặc định dùng [GenerateContent/streamGenerateContent native](https://ai.google.dev/api/generate-content), header x-goog-api-key. Có tùy chọn RAG_GEMINI_API_STYLE=openai_compatible với endpoint /v1beta/openai theo [tài liệu Google](https://ai.google.dev/gemini-api/docs/openai). Native adapter chuẩn hóa usageMetadata/modelVersion/finishReason và không xuất thought parts. Các lượt compatible gặp timeout được giữ nguyên; native được kiểm riêng, không coi một probe thành cải thiện đã chứng minh. OpenAI hỗ trợ cùng giao thức [Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create); adapter OpenAI chưa được gọi thật nếu chỉ có Gemini key.

```env
RAG_ENABLED=true
RAG_MODEL_PROVIDER=gemini
RAG_MODEL_ID=gemini-3.5-flash-lite
RAG_MODEL_ENDPOINT=https://generativelanguage.googleapis.com/v1beta
RAG_GEMINI_API_STYLE=native
RAG_REASONING_EFFORT=minimal
RAG_API_KEY=
```

Điền key trong .env ignored/mode0600. GEMINI_API_KEY cũng được đọc khi RAG_API_KEY trống; OpenAI tương tự với OPENAI_API_KEY. Không đặt key vào VITE_*, URL hoặc frontend. OpenAI cần provider=openai, endpoint=https://api.openai.com/v1, model có trong tài khoản và tham số reasoning/token tương thích model; bỏ RAG_REASONING_EFFORT nếu model không hỗ trợ. Không giả cấu hình OpenAI đã được kiểm chứng bằng Gemini.

Self-hosted endpoint dùng provider=openai_compatible, API key tùy server. Endpoint chỉ do operator cấu hình, không nhận URL/model override từ request; credentials/query/fragment trong URL bị từ chối. Provider-managed revision được ghi rõ, không giả biết immutable weights revision của Gemini. Runtime trả returned_model và prompt hash cho tái lập.

`RAG_GEMINI_API_STYLE=native` dùng endpoint /v1beta; đổi style=openai_compatible phải đổi endpoint thành /v1beta/openai. OpenAI vẫn dùng /v1 + Chat Completions. Không trộn protocol vào cùng endpoint. Các failure/success probes không bảo đảm Google latency hoặc account capacity ổn định.

Cấu hình vận hành hiện dùng một retry cho HTTP429/500/502/503 trước khi đọc generation body, sau khi ghi nhận lỗi server transient trong browser test. Read timeout/partial stream không được retry; tổng deadline5s vẫn giữ. Tham số retry được lưu trong generation_config, không suy tất cả request chỉ có một upstream attempt.
