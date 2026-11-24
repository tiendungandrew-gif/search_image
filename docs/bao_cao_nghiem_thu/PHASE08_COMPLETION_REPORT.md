# Nghiệm thu bổ sung Phase 08 — 06/11/2026

> Tài liệu lịch sử theo phase; lệnh trong nội dung giữ tên đường dẫn cũ. Hướng dẫn hiện hành tại [danh mục tài liệu](../README.md) và [scripts](../../scripts/README.md).

**Triển khai và kiểm thử phần mềm đã đạt trên corpus510 ảnh. Human quality review tiếp tục chờ theo lựa chọn của người dùng. Không đánh dấu chất lượng ngữ nghĩa đã nghiệm thu; không bắt đầu Phase 09.** Báo cáo05/11 và các lượt thất bại được giữ nguyên tại [báo cáo ban đầu](PHASE08_TEST_REPORT.md).

## A. Tóm tắt triển khai

Đã bổ sung dữ liệu có caption, downloader tái lập, provenance cho caption, index mới có thể rollback, retry/hủy yêu cầu ở giao diện, đồng bộ deadline, đóng Gemini stream khi STOP, workload VI/EN và trang human review offline. RAG vẫn dùng SearchService/CLIP hiện có, optional JSON/SSE, kiểm evidence và trích citations từ PostgreSQL/Qdrant/MinIO thật. Không gửi ảnh tới Gemini hoặc thay ranking của Fast Search.

## B. Tệp tạo và sửa

Thêm `backend/app/cli/download_coco.py`, `scripts/prepare_rag_corpus.py`, `scripts/check_rag_review.mjs`, `evaluation/annotation/rag_review.html`, workload `evaluation/rag/test_cases/coco_v1.jsonl`, benchmark config, source tests và [hướng dẫn dữ liệu](../research/RAG_DATASET.md). Cập nhật provider/context/config/API, ingestion schema/fingerprint, RAG CLI/evaluation, Docker packaging, ExplanationPanel và verification runners. Danh sách/hash cụ thể tại [source audit](../verification/phase08_completion_20261106/source_audit.json).

## C. Kiến trúc và corpus đang phục vụ

SearchService → batch evidence hiện hành → bounded facts/context → Gemini chọn fact IDs → server kiểm ID/quote → dựng câu và citations. Cả Search and Explain và Explain Existing Results được giữ.

Active index `69ac9c03-d218-40de-97bd-e6ba595e27f1`, generation2, collection `images_clip_coco_phase08_v1_1ea0b3304d04`: **510 ảnh/510 vectors**, CLIP512 cosine/L2. Model manifest `7f843c0bf81c571eee3b12621fc41811cea174113e6802684e9063b447e707dc` và encoder/decoder giữ nguyên. Default ingestion target/worker đã được đồng bộ với index mới.

Index baseline `6c3a8404-2971-46bf-ac9c-5c09bdec42b5` vẫn10 ảnh/10 vectors; trước/sau migration corpus đều verify pass. SigLIP và experiments cũ không bị activate/ghi đè/xóa. [Quy trình và bằng chứng](../verification/phase08_completion_20261106/corpus/summary.json).

## D. Dữ liệu và evidence

Đã tải500 JPEG COCO val2017, tổng85.406.189 bytes, seed42;500 accepted/0 failed/0 duplicates. Mỗi ảnh có caption gốc và caption_source dạng annotation ID; toàn bộ caption/source/license được giữ trong local provenance. Dữ liệu và weights không đưa vào Git. [Download receipt](../verification/phase08_completion_20261106/dataset_download.json), [verify510](../verification/phase08_completion_20261106/corpus/verify.json), [snapshot có500 captions](../../evaluation/datasets/manifests/phase08_coco_v2.json).

Chọn license IDs4/5/7/8 theo annotation gốc, giữ URL ảnh/Flickr và license từng ảnh. COCO Consortium là nguồn annotations; annotation license không thay giấy phép của ảnh. [Nguồn và cách tái lập](../research/RAG_DATASET.md). Checksum được quan sát trên TLS/ZIP CRC, không có publisher-signed digest. Chưa audit near duplicates hoặc overlap với pretraining.

Worker tạo510 embeddings trong355,65s, khoảng1,434 ảnh/s, gồm decode/preprocess/embed/upsert/verify, không tính bước nhập originals. Model init2.775,56ms; peak RSS1.038.068KiB,128 batches. [Raw worker metrics](../verification/phase08_completion_20261106/corpus/worker.json).

## E. Model và cấu hình vận hành

Gemini native, `gemini-3.5-flash-lite`, returned model cùng ID; revision provider-managed. Temperature0,1; max input4096/context2048/output128; reasoning minimal; stream bật; concurrency2. Generation deadline8s, whole-request12s, retry1 chỉ cho429/500/502/503 trước body trong tổng budget. Không tự retry timeout/partial stream. API key ở .env ignored/mode0600.

Frontend timeout65s bao phủ server cap60s, có hủy ngay/thử lại thủ công; câu trả lời cũ không đè yêu cầu mới sau hủy. Native STOP kết thúc stream mà không chờ EOF. Deadline dài hơn không chứng minh đạt target3s. [Runtime cuối sau fault tests](../verification/phase08_completion_20261106/final_runtime.json).

## F. Prompt và grounding

Bốn templates/extractive-facts-v1 giữ cơ chế closed fact IDs. Context kỹ thuật chỉ gửi trường liên quan, bỏ caption thừa. Câu hỏi mô tả nhận caption gốc, provenance vẫn unverified về thị giác. Answer là trích xuất có dẫn nguồn, chưa là free-form synthesis hoặc vision verification. Captions/metadata tiếp tục bị coi là untrusted, có injection/size guards và strict citation validation.

## G. API và giao diện

POST /rag/explain và /rag/explain/stream đã gọi Gemini thật; JSON/SSE, navigation tới ảnh và giữ kết quả khi AI lỗi được kiểm chứng. GET /images/{id} bổ sung caption optional để snapshot không làm mất mô tả có sẵn. Thiếu caption/visual facts trả insufficient_evidence, không gọi LLM hoặc bịa mô tả. Các search API giữ contracts.

Disabled, refused endpoint và real-provider0,1s timeout: **3/3 pass**, giữ images, không fabricated citations; cấu hình được khôi phục. [Fault injection](../verification/phase08_completion_20261106/fallback_cases.json). Health/live, readiness PostgreSQL/Qdrant/MinIO và search health đều200 ở bước cuối.

## H. Đánh giá grounding và chất lượng

Workload32 API attempts:8 mỗi R1/R2/R3/R4;8 câu hỏi thuộc4 family có VI/EN, retrieval query tiếng Anh và question theo ngôn ngữ. **16/16 generation completed,0 unavailable/HTTP errors;22/22 citation IDs và exact caption quotes hợp lệ.** Không suy visual truth/relevance từ số liệu này.

Relevance, faithfulness và semantic unsupported-claim rate **chưa đo**: người dùng chọn ngày06/11 “Chưa đánh giá được; giữ mục chất lượng chờ xác nhận”. [Trạng thái](../verification/phase08_completion_20261106/human_review_status.json). Caption do dataset cung cấp không phải nhãn query relevance hoặc nhãn câu trả lời.

Trang `.cache/evaluation/rag_phase08_coco_review.html` có16 frozen answers, ảnh/evidence thật, không nhúng token, không gọi mạng hoặc tự lưu. Draft luôn chưa verified; export verified cần người đánh giá xem đủ/điền counts/tên/xác nhận. Browser kiểm trang này pass:16 cases, ảnh loaded,0 JS errors,0 remote requests, từ chối xác nhận khi chưa review. [Kết quả](../verification/phase08_completion_20261106/review_ui.json).

## I. Hiệu năng đo thật

Fast Search: **500/500 success,0 failures/timeout**, warmup12/0 errors, full ASGI samples500, C1/K10/candidates50, CLIP CPU4threads trên510 ảnh. Server P50 **123,64ms**, P90 **142,89ms**, P95 **153,57ms**, P99 **174,03ms**, max **591,10ms**,7,59success/s. P90≤300/P95≤500 đạt trong điều kiện đo; không là production capacity/SLA claim. [Raw500](../../evaluation/results/phase08_completion/20261106T040458_benchmark_2dc80f5824/result.json).

| Nhóm | Requests/generated | Client P90 ms | Provider TTFT P90 ms | TTLast từ service P90 ms |
| --- | --- | --- | --- | --- |
| R1 Search | 8/0 | 140,90 | — | — |
| R2 Metadata | 8/0 | 104,72 | — | — |
| R3 cap3 | 8/8 | 1.424,74 | 1.158,48 | 1.366,70 |
| R4 cap1 | 8/8 | 2.059,12 | 1.808,86 | 1.968,15 |

**16/16 RAG TTLast dưới3s trong lượt mới**, max1.968,15ms; N8/cấu hình nên nearest-rank P90/P95 là maximum. Đây là exploratory trial, không đủ chứng minh độ ổn định dài hạn. Lượt05/11 có timeout/vượt3s vẫn được giữ; corpus, context, protocol/time window khác nhau nên không kết luận causal speedup. [Raw RAG](../../evaluation/results/phase08_completion/20261106T035619_rag_f1012fd73b/result.json).

CPU Intel Core7 240H/16 logical, RAM15.845.068KiB, không đo GPU. Client Python3.12.3/server3.12.12, actual versions/hardware trong experiment. Remote Gemini hardware/network load không kiểm soát. Server RAG timings từ service entry sau validation; client latency bao gồm HTTP hoàn chỉnh. Không cộng percentile/subspans; generation_ms đã chứa validation_ms.

[Report JSON/CSV/Markdown](../../evaluation/reports/phase08_20261106/REPORT.md), [32 per-case rows](../../evaluation/reports/phase08_20261106/rag_cases.csv), [RAG PNG](../../evaluation/reports/phase08_20261106/rag_latency.png), [Fast PNG](../../evaluation/reports/phase08_20261106/latency.png), có SVG cùng thư mục. Không vẽ semantic-quality charts khi chưa có nhãn.

## J. Kiểm thử tự động

- Backend **152 passed** =142 unit +10 integration thật, gồm3 RAG/Gemini cases. [Log](../verification/phase08_completion_20261106/full_v2/backend_tests.txt).
- Frontend **13 unit passed**; TypeScript/ESLint/build qua. [Log](../verification/phase08_completion_20261106/full_v2/frontend_checks.txt).
- Browser **16/16 passed**, desktop/mobile, search/multimodal/annotation/RAG/navigation. [Log](../verification/phase08_completion_20261106/full_v2/browser.txt).
- Ruff/format, Node syntax và review UI checks qua. [Summary full](../verification/phase08_completion_20261106/full_v2/summary.json).
- Fault injection thật3/3, final runtime pass, verify510 pass. Các provider doubles chỉ dùng unit tests, không thay real Gemini assertions.

Lượt full đầu150 pass/2 fail do thiếu template trong Docker image và assertion giả định corpus10 phủ hết hai nhánh. Đã thêm Docker COPY template; test fusion kiểm numerical contribution của union trên510 ảnh và vẫn giữ strict both-branch assertion khi filter tập10 ảnh. Không sửa engine/ranking hoặc che failure. [Log lượt lỗi được giữ](../verification/phase08_completion_20261106/full/backend_tests.txt).

## K. Giới hạn và mục còn mở

Human review còn pending theo người dùng; chưa có semantic Recall@10/nDCG/answer quality/visual unsupported-claim rate. Corpus500 có caption không thay bộ nhãn benchmark. Chưa kiểm large-scale/cold-cache/high-concurrency/GPU, không có bằng chứng OpenAI live integration từ Gemini tests. API quản trị sửa/xóa metadata chưa thuộc phần hoàn thiện này. Provider outages/quota vẫn có thể xảy ra dù lượt mới pass.

## L. Sẵn sàng Phase 09 và bàn giao

Đã có retrieval/evidence/context/generation/citations/JSON/SSE/telemetry và corpus caption để tích hợp sau. Mã nguồn, tests, measurement artifacts và công cụ human review được bàn giao; **chưa xác nhận nghiệm thu chất lượng ngữ nghĩa**. Không có Agent Planner/tool calling/multi-hop hoặc thay đổi tự động sang Phase 09.

[Kiểm tra bàn giao cuối](../verification/phase08_completion_20261106/final_checks.json). Người dùng có thể tiếp tục đánh giá offline và nạp verified labels bằng CLI theo [hướng dẫn](../research/RAG_DATASET.md).
