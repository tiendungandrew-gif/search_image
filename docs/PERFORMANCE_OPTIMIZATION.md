# Profiling và tối ưu có kiểm chứng — Prompt07

Không đổi model weights, embedding-space manifest, active collection hoặc ranking để làm benchmark nhanh. Không thêm Redis, query-result cache hoặc LLM. Đổi execution order của object checks phải giữ metadata/payload eligibility, private-object access và result order.

## Bottleneck đã quan sát

Lượt profiling ban đầu500 fast requests/C1: full server mean130.53ms, P90142.19ms/P95144.77ms,0 errors. Component means: Qdrant query44.58ms, text embedding25.80ms, batch metadata13.93ms, eligibility/object checks34.48ms. Raw [baseline profiling](../evaluation/results/phase07/20261104T084629_benchmark_0255e8a3fd/result.json). Không cộng component P90 để suy full latency.

Đã chọn kiểm tra object là thay đổi semantics-preserving có thể kiểm chứng. Qdrant/compatibility network calls vẫn là bottleneck khác; chưa đổi transport/index configuration khi chưa có controlled evidence. Không thêm PostgreSQL index chỉ vì thấy sequential scan trên bảng10 rows.

## Thay đổi được triển khai

`SearchService.format_results` gom những candidates đã qua payload/PG filters, kiểm HEAD theo cửa sổ1 hoặc2, dùng chính MinIO executor/semaphore2 slots có sẵn. Chờ theo gather input order, không reorder theo I/O completion. Window không lớn hơn số kết quả còn thiếu; không HEAD cả pool100 khi chỉ cần10. Missing objects/size mismatch vẫn bị loại, service failure vẫn503, cancellation giữ underlying I/O slot tới khi thực sự xong.

SEARCH_OBJECT_CHECK_CONCURRENCY có bounds1…2; default1; mức2 giữ cho thử nghiệm. Top-K/dedup/score/filter/evidence policies không đổi. Unit test tạo completion order đảo nhau và missing object để kiểm rank, peak in-flight và không speculative-fetch vượt remainingK. Core/image/private content regressions dùng actual stores/model.

## Controlled measurement

ABBA order: head1 rep1 → head2 rep1 → head2 rep2 → head1 rep2, mỗi run300 requests/warmup12/cùng seed/query set/CPU4threads. API được recreate giữa các config và đợi search-ready; sampler ghi actual setting từng run. Lượt thí nghiệm gốc kết thúc ở2; cấu hình bàn giao đã về1. Suite hiện khôi phục width ban đầu sau ABBA. So sánh pooled raw successful samples theo config, không average các run percentiles; bootstrap và per-query differences có thể dùng để mô tả uncertainty, không thay human quality labels.

Before/after result IDs được đối chiếu theo query ID, không chỉ so số results. Điều này chứng minh ranking invariance trên workload đã chạy, không chứng minh semantic relevance. Semantic quality regression vẫn unavailable do người dùng chưa có qrels. [Kết quả](EXPERIMENT_RESULTS.md) ghi actual end-to-end/component effects, kể cả không đạt improvement đáng tin cậy.

Đo sơ bộ ABBA cho thấy window2 giảm thời gian object stage, trong khi full P90 còn chịu compatibility/Qdrant jitter. Không quảng bá component gain như full-pipeline speedup. Nếu confidence chưa đủ, giữ nhận định giới hạn; không chọn best run hoặc bỏ failures để đạt target.

## Giới hạn còn lại

Một inference slot/API process, queue8/wait50ms có thể trả503 khi nhiều clients. Source image previews chưa có thumbnails riêng. Qdrant HTTP/registry checks và object service calls có network overhead thật. CPU-only, corpus10 và uncontrolled OS cache không đủ kết luận large-scale performance. Các thay đổi candidate depth/fusion/rerank/model phải chờ labels để đánh giá quality-versus-latency; hiện giữ retrieval defaults đã có.

## Kết luận controlled ABBA

Pooled600 mẫu mỗi width: HEAD1 mean117,25ms/P90148,02ms/P95153,56ms; HEAD2 mean123,50ms/P90148,90ms/P95151,28ms. Object-stage mean19,31→14,84ms nhưng full mean tăng6,25ms. Paired family bootstrap của mean delta có CI95%[4,21;7,82]ms, chỉ mô tả workload đã đo. P90 block-bootstrap intervals chồng nhau. Không chứng minh tăng tốc toàn request; giữ default1. Toàn bộ1.200 responses giữ cùng ranked IDs theo từng query trong12 cases; đây là ranking invariance, không semantic quality regression score. [Phân tích raw](../evaluation/results/phase07/20261104T101633_optimization-analysis_8b0e4c6291/result.json).

Lượt final default1 có500/0 errors, P90145,80ms/P95150,90ms. Không dùng khác biệt giữa lượt final và lượt profiling cũ như causal speedup: thời điểm/runtime conditions khác nhau. Profiling PostgreSQL ghi batch join0,188ms, tags0,028ms trên10 ảnh; chưa có căn cứ thêm index để tối ưu tải lớn. Qdrant indexed_vectors_count=0/full_scan_threshold10.000: corpus nhỏ dùng plain scan, không chứng minh HNSW tuning.
