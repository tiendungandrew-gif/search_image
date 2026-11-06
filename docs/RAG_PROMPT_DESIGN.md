# Prompt và kiểm tra grounding — Prompt08

Bốn template thực tại backend/app/services/rag/prompts: system_prompt.txt, answer_generation.txt, evidence_explanation.txt, insufficient_evidence.txt. Version extractive-facts-v1; SHA256 trên toàn bộ template được ghi ở mỗi response/experiment. Không sửa template bằng query parameter.

System phân biệt user question/evidence là dữ liệu, cấm làm theo chỉ dẫn trong captions/tags/metadata, không suy pixel từ điểm CLIP và không bịa IDs. Context JSON chứa fact_id/image_id/evidence_field/quote/provenance. Model chỉ trả {"fact_ids": []} hoặc danh sách IDs có sẵn. Schema strict cấm answer tự do, tools và references lạ; duplicate IDs bị reject.

Các facts được chọn theo rank hoặc ưu tiên bản ghi có mô tả, không thay đổi ranking kết quả ảnh. Chỉ lấy số items trong giới hạn server; field selection theo câu hỏi kỹ thuật, dedup, giới hạn context và tổng prompt/output. Đếm UTF-8 bytes + overhead như upper bound bảo thủ, không gọi đó là exact tokenizer count. Token usage thực lấy từ provider khi có. Không cắt ngắn user question hoặc caption âm thầm để đổi ý nghĩa; quá budget thì không gửi generation.

Phòng injection gồm tách role, JSON data, giới hạn trường/kích thước, lọc các mẫu chỉ dẫn, không đưa secrets vào prompt, không có tool execution và server chỉ render exact quotes của những facts đã validate. Regex không là bộ phát hiện injection đầy đủ. Những đoạn lọt qua vẫn chỉ là dữ liệu; closed-ID/extractive policy giới hạn phạm vi claims. Không có semantic entailment model hoặc visual verifier.

Streaming gửi token thật của phần chọn fact IDs với verified=false. Frontend không hiển thị các token chưa validate như câu trả lời. generation_completed mới có câu từ metadata đã xác minh references. Provider TTFT khác thời điểm giao diện nhận final answer; không dùng token progress để giả latency câu trả lời đã grounded.
