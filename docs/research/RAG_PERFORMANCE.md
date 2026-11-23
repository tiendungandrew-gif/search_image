# Hiệu năng và timeout RAG — Prompt08

Cập nhật06/11/2026: đã có corpus510 ảnh/500 captions; phần mềm đạt152 backend tests,13 frontend unit và16 browser cases. Human quality review chờ xác nhận theo lựa chọn của người dùng. [Báo cáo hiện hành](../archive/PHASE08_COMPLETION_REPORT.md); các số liệu05/11 bên dưới là lịch sử. Không tự chuyển Prompt09.

Mục tiêu Fast Semantic Search P90≤300ms và mục tiêu RAG time-to-last-token≤3s là hai mục tiêu riêng. Không cộng các component percentile để chứng minh end-to-end percentile. Provider TTFT tính đến delta nội dung đầu tiên; TTLast đến delta cuối của selection JSON. Câu trả lời đã validate đến sau bước validation/server render; frontend không coi token chưa kiểm là answer.

Budget dự kiến: retrieval300ms, metadata100ms, context50ms, generation2200ms, validation/serialize150ms, allowance200ms. Đây là kế hoạch, không số đo. Generation deadline vận hành5s, overall request8s; normal search vẫn2s. Deadline cao hơn target không bảo đảm đạt target, và deadline thấp không biến timeout thành latency thành công.

Triển khai reuse async HTTP pool, bounded concurrency2, context/items/output bounded, retry0 mặc định, không gọi LLM khi không có evidence hoặc tắt module. Không thêm cache/query retention/Redis. Gemini tính toán ở dịch vụ ngoài; chỉ đo latency/usage phía client và process API, không giả biết GPU/RAM của provider.

Chỉ dùng raw results để đánh giá mục tiêu. Lượt cold đầu có LLM_TIMEOUT với ảnh được giữ; lượt warm metadata thực tiếp theo có generated/citations hợp lệ. Không bỏ lượt lỗi để nói hệ thống ổn định. Kết quả định lượng chốt tại [báo cáo Phase08](../archive/PHASE08_TEST_REPORT.md). Hạ tầng đo local CPU Core7 240H/16 logical/15,11GiB RAM, CLIP CPU4threads, model generation remote; network/provider load/cache không kiểm soát.

Deadline được tăng từ3 lên5s sau các lỗi integration thực, không đổi mục tiêu3s. Đã thêm deterministic aclosing cho upstream async generator và luôn trả admission slot khi hủy kể cả giữa event emission; unit cancellation kiểm tài nguyên được trả. Các thay đổi này không bảo đảm khắc phục jitter/capacity của Gemini. Các run trước và sau thay đổi được giữ riêng; không suy causal gain nếu điều kiện mạng/provider khác nhau.

Cấu hình vận hành hiện dùng một retry cho HTTP429/500/502/503 trước khi đọc generation body, sau khi ghi nhận lỗi server transient trong browser test. Read timeout/partial stream không được retry; tổng deadline5s vẫn giữ. Tham số retry được lưu trong generation_config, không suy tất cả request chỉ có một upstream attempt.

Nghiệm thu native đã có144 backend tests pass; browser từng có16/16 pass ở lượt compatible, nhưng lượt native cuối hiện15/16 do một LLM_TIMEOUT. Không đổi assertion để giấu outage; logs các lượt được giữ. Không có căn cứ kết luận đổi protocol khắc phục hoàn toàn provider latency.

## Số đo chốt

| Protocol / cấu hình | Attempts / generated / unavailable | Client P90 ms | Provider TTFT P90 ms | TTLast P90 từ service ms |
| --- | --- | --- | --- | --- |
| [openai_compatible/R1](../../evaluation/results/phase08/20261105T042632_rag_37780e9449/result.json) | 5 / 0 / 0 | 103.42 | — | — |
| [openai_compatible/R2](../../evaluation/results/phase08/20261105T042632_rag_37780e9449/result.json) | 5 / 0 / 0 | 135.88 | — | — |
| [openai_compatible/R3](../../evaluation/results/phase08/20261105T042632_rag_37780e9449/result.json) | 5 / 3 / 2 | 5261.02 | 4353.80 | 4699.60 |
| [openai_compatible/R4](../../evaluation/results/phase08/20261105T042632_rag_37780e9449/result.json) | 5 / 0 / 5 | 5207.81 | — | — |
| [native/R1](../../evaluation/results/phase08/20261105T050046_rag_4b6c513c95/result.json) | 5 / 0 / 0 | 87.14 | — | — |
| [native/R2](../../evaluation/results/phase08/20261105T050046_rag_4b6c513c95/result.json) | 5 / 0 / 0 | 142.83 | — | — |
| [native/R3](../../evaluation/results/phase08/20261105T050046_rag_4b6c513c95/result.json) | 5 / 5 / 0 | 2151.82 | 1845.20 | 2122.30 |
| [native/R4](../../evaluation/results/phase08/20261105T050046_rag_4b6c513c95/result.json) | 5 / 5 / 0 | 3673.09 | 3448.03 | 3643.47 |

Native10/10 completed nhưngR4 cóTTLastP903.643,47ms; mục tiêu3s chưa đạt toàn workload. Fast500 requests/0 errors/P90144,59ms/P95153,17ms. [Raw/report](../../evaluation/reports/phase08_20261105/REPORT.md); browser cuối vẫn có một timeout, không dùng benchmark10/10 thay tuyên bố reliability production.

`generation_ms` là toàn bộ Generator operation; `validation_ms` là subspan nên không cộng hai field này để suy latency. Server timings ở RAG service entry, còn client_total_ms bao gồm HTTP response đầy đủ. Byte/token upper bound là chính sách bảo thủ của context builder; token usage thực vẫn do provider báo.

Ngày06/11, Fast500/0 failures trên510 ảnh: P90142,89ms/P95153,57ms. RAG cap3/cap1 có8 completions mỗi nhóm, TTLast P901.366,70/1.968,15ms;16/16 dưới3s ở lượt này. N nhỏ và điều kiện khác lịch sử, không suy SLA hoặc causal improvement. Deadline8/12s thay5/8s; [số liệu và giới hạn hiện hành](../archive/PHASE08_COMPLETION_REPORT.md).
