# Multimodal Search — Prompt 06

Đã triển khai late fusion của text và reference image trên cùng paired CLIP/model manifest/index Prompt04. Không cộng embeddings để giả lập chỉnh sửa hình ảnh; không gọi LLM hoặc ingest query image. [API](ADVANCED_SEARCH_API.md), [multi-intent](MULTI_INTENT_SEARCH.md), [reranker](RERANKING_DESIGN.md) và [báo cáo nghiệm thu](../archive/ADVANCED_SEARCH_TEST_REPORT.md) là tài liệu triển khai hiện tại.

## Luồng đã triển khai

Validation/auth → lightweight analysis → batch whole-query/constraint text encoding → cùng image decoder/processor/encoder Prompt04–05 → independent Qdrant query_points → UUID union/fusion → batch PG eligibility/metadata → required-condition evidence gate → optional reranking → private MinIO content URLs → Top-K response. Mọi nhánh pin cùng registry/model/index; fingerprint, revision,512 dimensions, float32/L2/Cosine giữ nguyên. Không tạo collection hoặc migration mới.

Encoder được preload một lần/API process; executor một slot và queue/cancel bounds của Prompt05 vẫn áp dụng. Independent vector calls có bounded fan-out, default tối đa4 channels, tổng requested entries≤1.000, union pool≤100 mặc định. Whole query và image là hai nhánh ưu tiên; tối đa2 per-constraint branches còn lại khi paired. Encode mọi semantic clause trong một batch để dùng lại khi rerank; không một inference call cho từng leaf. Các nhánh Qdrant chạy concurrent, model inference dùng chung slot nên text và image forward không chạy đồng thời trên cùng model.

## Fusion thực tế

- `rrf` hoặc alias `weighted_rrf`: `sum(w_channel/(k+rank))`, k mặc định60, rank bắt đầu1. Weights được normalize theo tổng. Text total weight được chia đều cho whole-query và text-clause branches; image giữ image total weight. Khi không có image, text branches có trọng số bằng nhau.
- `weighted_score`: cosine chuyển thang xác định `s=(clip(cosine,-1,1)+1)/2`, rồi `sum(w_channel*s)`. Đây là đổi thang trên cùng embedding space, **không là calibration hoặc xác suất relevance**. Cần human labels trước khi chọn weights/method tốt nhất.
- Candidate không có trong một branch được contribution0, không suy đoán cosine thật bằng0, không normalize lại weights theo mỗi document/empty branch. Actual cosine chỉ xuất hiện trong contributing_branches khi branch thật trả candidate đó. Branch weight0 không đóng góp candidates. Empty branches giữ nguyên normalized global weights.
- Dedup UUID, score giảm dần, tie theo UUID; ghi contributing branch/rank/cosine/weight/contribution. Cap áp dụng sau fusion. Scores RRF/weighted_score/reranker có score_type và version riêng, không trộn rồi gọi là cosine.

Hai weights mặc định0.5/0.5, có thể bằng0 nhưng không đồng thời0; mỗi weight trong[0,1]. Đây là defaults chưa được tối ưu bằng quality evaluation. `retrieval_strategy=whole_query|multi_query` chỉ dùng thí nghiệm text; paired search yêu cầu fused để tránh bỏ image signal khi rescore.

## Query image và delivery

JPEG/PNG/WebP qua đúng resource-limited decoder/RGB/EXIF/alpha processing Prompt04 và decoder process reuse Prompt05. File≤20MiB/body≤21MiB, single frame,25M pixels/side≤10.000, parent decode deadline2s. Query bytes không được đưa vào MinIO/corpus/jobs/history; multipart temp spool đóng sau đọc, decoded image đóng sau inference. Không có public query URL.

Existing image_id dùng stored vector đã đối chiếu PG receipt/vector SHA. exclude_self mặc địnhtrue, UI dùngfalse. Kết quả sử dụng authenticated relative content proxy; frontend Authorization→blob preview, không gắn token vào URL hoặc lưu local/sessionStorage. Fixture chưa có thumbnail thì proxy fallback original.

## Giới hạn

Text instruction “similar but red” là semantic signal, chưa chứng minh compositional edit/object color hoặc absence/spatial relationship. Global CLIP scores không verify từng vật thể; semantic assessments vẫn UNKNOWN. Corpus10 hiện không chứa đầy đủ motorcycle/helmet/rain/color-edit scenarios, nên tests chỉ chứng minh pipeline/protocol, không chứng minh relevance. Việc parse tiếng Việt không làm CLIP hiện tại thành multilingual model đã được đánh giá.

Chạy benchmark RRF/score/rerank với [evaluation](../../evaluation/README.md). Raw measurements và E1–E5 comparison nằm trong báo cáo; chưa có human qrels nên không kết luận strategy nào cải thiện Recall/nDCG. Outer full request timeout2s vẫn áp dụng cho cả fast/advanced; không chuyển advanced latency vào số đo fast.
