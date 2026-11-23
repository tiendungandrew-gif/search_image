# Kiểm chứng tìm kiếm song ngữ và không dấu — 19/11/2026

Đã tái hiện lỗi: `con meo` trả ảnh người/gấu bông, trong khi `con mèo` trả mèo.
Kiểm chứng cũ chỉ dùng câu có dấu và HTTP 200 nên bỏ sót lỗi này. Không coi
những bài kiểm tra cũ là bằng chứng hỗ trợ tiếng Việt không dấu.

Bản sửa tự khôi phục dấu theo ngữ cảnh bằng model ký tự local, giữ ô nhập nguyên
văn và hiển thị câu đã hiểu. Đã bật development http://localhost:5173. Không chọn
ngôn ngữ, không API dịch, không dùng bảng riêng ánh xạ từ `meo` sang `cat`.
Chưa commit; production-like 8088 vẫn là release cũ.

| Kiểm tra | Kết quả |
| --- | --- |
| Backend unit/security/reliability | 275 pass; [log QA](../phase11/runs/20261119T155534_589413_fast.log) |
| Frontend unit | 72 pass / 18 files |
| Frontend build, ESLint; Python Ruff; git diff --check | Pass |
| Model thật: 5 cặp EN/VI, 10 ảnh mẫu | Cả 10 câu đưa đúng ảnh mục tiêu lên đầu; [dữ liệu](model.json) |
| 11 cặp không dấu/có dấu, gồm `con meo`, `meo`, `2 con meo`, `con cho` | Khôi phục đúng, vector bằng câu có dấu; [dữ liệu](model.json) |
| English, padding, NFC/NFD, cache copy/eviction, token limit | Pass trong model smoke |
| Serving API qua session User | 12 câu pass; 5 câu về mèo bắt buộc ảnh đầu là mèo, không chỉ HTTP 200; [dữ liệu](api.json) |
| Chromium desktop, mobile 390px, narrow 320px; Firefox | 4 pass; [browser log](../consumer_ui/browser-all.txt) |

API kiểm tra `con meo`, `con  meo`, `meo`, `con mèo`, `a cat` dựa trên caption
COCO có nhãn mèo hoặc hash ảnh mẫu Chelsea. Kiểm tra thêm giới hạn thư viện,
ảnh private và cache. Browser gửi nguyên `con meo`, kiểm tra caption ảnh đầu
và dòng thêm dấu; text/image/multimodal, filter thư viện vẫn hoạt động.
Đã xem [ảnh chụp kết quả thực](../consumer_ui/results-desktop.png): cả ba ảnh là mèo.

[Trước sửa](cat-debug/query-2.json) và [sau sửa](api.json) giữ lại bằng chứng lỗi.
Thời gian thêm dấu nằm ở stage `query_normalization_ms` trong artifact API;
câu lặp dùng cache. Không coi lượt kiểm tra này là p95/SLA
hoặc đánh giá tải đồng thời. Image index vẫn
`b4597021-4b91-491d-99ae-0617a6ca389c`; không rebuild index hay sửa quyền thư viện.

Full Docker build đã gặp timeout khi tải dependency từ PyPI, không coi là pass.
Development đang dùng image dựng offline từ image trước sửa và package
`py3langid==0.4.0` đã đối chiếu SHA256 của wheel và toàn bộ RECORD; `uv pip check`
đạt. Build context local ở `.cache/build/accents`; image cũ giữ ở tag
`ai-image-search-backend:before-accent-fix`. Repo đã cập nhật pyproject/uv.lock;
full build thông thường cần mạng truy cập các registry hoạt động. Không đổi
Dockerfile chuẩn để bỏ qua lockfile hoặc kiểm tra dependency.

Đây là regression/smoke nhỏ, chưa phải benchmark chất lượng toàn bộ corpus.
Tên riêng, từ đa nghĩa, câu dài, dấu trộn lẫn và độ chính xác hai ngôn ngữ cần
bộ đánh giá đại diện hơn. [Thiết kế, giới hạn và lệnh chạy lại](../../features/BILINGUAL_SEARCH.md).
