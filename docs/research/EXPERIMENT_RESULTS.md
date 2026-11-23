# Kết quả thí nghiệm Prompt07

Các số liệu được tổng hợp từ immutable experiments tại `evaluation/results/phase07/`, mỗi experiment có config/provenance/source archive và raw result. Không ghi đè Phase05/06 outputs. JSON/CSV/Markdown/PNG/SVG đã được sinh từ các lượt chạy thực.

## Trạng thái chất lượng

Người dùng xác nhận chưa có human labels và yêu cầu công cụ gán nhãn trước. Trang local có24 semantic queries/10 images với240 grade judgments chưa điền. Semantic Recall@1/5/10, Precision@10, MRR@10, nDCG@10 và constraint-quality comparisons hiện **unavailable**. Không dùng unit fixtures, filename hoặc model scores làm qrels.

Exact-byte identity và ANN-vs-exact là experiments khác, được báo riêng khi có raw results. Corpus10/K10 có recall saturation và không đại diện large-scale search. Không có GPU comparisons.

## Measurements

Đã lưu **32 experiments**, gồm **21 lượt benchmark / 7,360 attempts / 737 lỗi**. Các lỗi đều được giữ trong raw samples; không gộp tất cả workloads thành một SLO. [Suite controlled/matrix](../verification/phase07/suites/20261104T093924_4026c284.json), [JSON/CSV/report tự sinh](../../evaluation/reports/phase07/REPORT.md).

### Fast Search và image upload

| Cấu hình | N thành công / lỗi | P50 ms | P90 ms | P95 ms | Thành công/s |
| --- | --- | --- | --- | --- | --- |
| [fast_default_head1](../../evaluation/results/phase07/20261104T101019_benchmark_c505f295d7/result.json) | 500 / 0 | 107.44 | 145.80 | 150.90 | 8.65 |
| [image_after](../../evaluation/results/phase07/20261104T094413_benchmark_016c347034/result.json) | 300 / 0 | 121.18 | 130.56 | 138.08 | 8.01 |

Fast final:500/500 full-server samples,0 warmup failures/12 warmup,0 timeouts. P90≤300ms và P95≤500ms **đạt trong workload đã đo**: C1/K10/candidate50/CLIP CPU4threads/10 ảnh. Server mean112.94ms, arithmetic median107.53ms, std18.72ms; client P90148.35ms/P95153.09ms. Nearest-rank P50 khác arithmetic median khi N chẵn. P90 descriptive block-bootstrap CI95%[140,60;147,83]ms không là production SLA confidence.

59 runtime snapshots gồm warmup/steady-state cho thấy API CPU trung bình148.91% theo đơn vị một logical CPU (có thể vượt100% do multi-thread); peak sampled RSS/HWM1267.09MiB. Đây là toàn process, không memory riêng từng query. Không có GPU; OS/page-cache không kiểm soát.

### Concurrent load

| Cấu hình | N thành công / lỗi | P50 ms | P90 ms | P95 ms | Thành công/s |
| --- | --- | --- | --- | --- | --- |
| [load_fast_c1](../../evaluation/results/phase07/20261104T095051_benchmark_09d9264c9f/result.json) | 300 / 0 | 133.52 | 147.43 | 148.95 | 7.70 |
| [load_fast_c5](../../evaluation/results/phase07/20261104T095132_benchmark_6fe8167b67/result.json) | 478 / 22 | 145.26 | 184.58 | 194.54 | 33.16 |
| [load_fast_c10](../../evaluation/results/phase07/20261104T095149_benchmark_f713978774/result.json) | 217 / 283 | 198.95 | 229.47 | 241.15 | 30.08 |
| [load_fast_c20](../../evaluation/results/phase07/20261104T095159_benchmark_1bff5d5b0d/result.json) | 68 / 432 | 257.24 | 312.77 | 372.66 | 19.50 |
| [load_mixed_open8](../../evaluation/results/phase07/20261104T095205_benchmark_ddf52692ff/result.json) | 160 / 0 | 100.15 | 140.42 | 151.42 | 8.01 |

Closed-loop5/10/20 clients có error-rate4,4%/56,6%/86,4%, toàn bộ INFERENCE_BUSY, không timeout. Successful sample counts478/217/68; c20 chỉ kéo dài3,49s và không đủ100 success samples cho bootstrap đáng tin. Không dùng fail-fast để tuyên bố throughput ổn định. Mixed load offered8/s trong20s,160 attempts/0 errors, concurrency cap5; đây không phải cùng profile/SLO với fast. Cần repeated sustained representative workload trước capacity claims.

### Ablation latency

| Cấu hình | N thành công / lỗi | P50 ms | P90 ms | P95 ms | Thành công/s |
| --- | --- | --- | --- | --- | --- |
| [A0_whole](../../evaluation/results/phase07/20261104T094452_benchmark_bb696f814c/result.json) | 300 / 0 | 134.07 | 148.33 | 152.41 | 7.69 |
| [A1_multiquery](../../evaluation/results/phase07/20261104T094533_benchmark_833ec7552e/result.json) | 300 / 0 | 148.71 | 160.49 | 163.75 | 6.83 |
| [A2_rrf](../../evaluation/results/phase07/20261104T094620_benchmark_01151f1a21/result.json) | 300 / 0 | 141.22 | 153.39 | 155.65 | 7.26 |
| [A3_nonsel_filter](../../evaluation/results/phase07/20261104T094703_benchmark_ff869c8d80/result.json) | 300 / 0 | 139.72 | 153.43 | 156.66 | 7.35 |
| [A4_rerank](../../evaluation/results/phase07/20261104T094747_benchmark_53a3137b7f/result.json) | 300 / 0 | 150.39 | 162.02 | 164.57 | 6.72 |
| [A5_text_only](../../evaluation/results/phase07/20261104T094834_benchmark_e060438714/result.json) | 300 / 0 | 135.13 | 147.82 | 150.23 | 7.58 |
| [A5_paired_rrf](../../evaluation/results/phase07/20261104T094916_benchmark_eaee1c2363/result.json) | 300 / 0 | 146.43 | 167.35 | 179.91 | 6.59 |
| [A5_paired_score](../../evaluation/results/phase07/20261104T095004_benchmark_3cec04222f/result.json) | 300 / 0 | 142.00 | 156.19 | 167.77 | 6.82 |

A0…A4 cùng10 multi-intent cases, A5 cùng2 paired cases; mỗi cấu hình300 attempts/0 errors, C1. Các số ở bảng dùng HEAD2 trong matrix gốc, không nhầm thành cấu hình bàn giao HEAD1. A3 là filter không chọn lọc, chỉ đo overhead. Chưa có nhãn nên Recall/nDCG/constraint satisfaction và paired quality CI đều chưa đo. Resource sampling không bật cho từng A-run; không suy CPU từng ablation từ số fast.

### Model comparison CPU

| Model | Chiều | Khởi tạo process mới ms | Encoding P50 / P90 ms | Peak RSS MiB | Kiểm tra index |
| --- | --- | --- | --- | --- | --- |
| [clip](../../evaluation/results/phase07/20261104T101257_model-comparison_ace1b38e21/result.json) | 512 | 3859.78 | 22.35 / 63.80 | 1174.41 | 10/10, CLIP active giữ nguyên |
| [siglip2](../../evaluation/results/phase07/20261104T101307_model-comparison_4c67e77ccf/result.json) | 768 | 6219.71 | 41.15 / 163.13 | 1855.54 | 10/10, CLIP active giữ nguyên |

Hai model chạy fresh process trên cùng10 images/28 cases, dùng processor/tokenizer/collection riêng. Encoding bao gồm input read/decode/preprocessing khi có image; không coi đây là pure forward latency hoặc full HTTP latency. Filesystem cache warm/uncontrolled. Lượt index SigLIP đầu đi qua durable reindex10 ảnh/batch4,4,2 trong4.030,61ms; lượt lặp idempotent không phải throughput reindex mới. Cả hai4/4 self identities ở rank1; không có bằng chứng model nào tốt hơn về semantic quality/tiếng Việt.

### Profiling và optimization

[Query plans/config thật](../../evaluation/results/phase07/20261104T101319_profile_344aa63687/result.json): candidate batch join0,188ms, tags0,028ms; pool5/checked-out0 tại thời điểm quan sát. Corpus có0/10 captions và0/10 tagged images. Qdrant10 points/512 Cosine, indexed_vectors_count0, HNSW m16/ef_construct100/full_scan_threshold10.000, payload_schema rỗng; không chứng minh HNSW quality hoặc scalability. ANN-vs-exact overlap được ghi riêng với K=N10.

[ABBA pooled/paired analysis](../../evaluation/results/phase07/20261104T101633_optimization-analysis_8b0e4c6291/result.json): HEAD1/HEAD2 mỗi600 samples, full mean117,25/123,50ms, P90148,02/148,90ms. Object stage19,31→14,84ms nhưng full mean xấu hơn6,25ms; paired family bootstrap CI95%delta[4,21;7,82]ms. P90 block-bootstrap intervals chồng nhau. Ranked IDs giống nhau trên12 queries/1.200 samples. **Giữ default1**, không quảng bá tăng tốc end-to-end hoặc semantic-quality improvement.

### Quality hiện có

[Upload identity thật qua API](../../evaluation/results/phase07/20261104T101005_evaluate_f6a6877b9f/result.json):4/4 queries, Recall@1/5/10=1, Precision@10=0,1, MRR@10=1, nDCG@10=1. Chỉ là exact-byte identity với một relevant UUID/query trên corpus đã SHA-dedup.24 semantic queries/240 grades chưa gán; semantic metrics/constraint satisfaction/VI-versus-EN comparison chưa đo.

[Biểu đồ latency](../../evaluation/reports/phase07/latency.png), [load/error](../../evaluation/reports/phase07/load.png), [model CPU/RSS](../../evaluation/reports/phase07/models.png). Bản SVG cùng thư mục; summary.csv/queries.csv chứa kết quả xuất. Không có biểu đồ chất lượng giả.


## Cách diễn giải

Latency successful-only đi kèm failure/timeout/status counts và sample coverage. Load-level latency nhỏ do503 fail-fast không chứng minh capacity tốt. Fast target chỉ cho workload fast đủN/coverage/zero errors, không áp tự động cho advanced/mixed. Component object-check gain không thay full end-to-end improvement nếu các span khác chi phối.

Quality-versus-latency recommendation hiện giữ operational CLIP/core defaults và không chọn model/fusion winner khi thiếu relevance data. Dùng [methodology](EVALUATION_METHODOLOGY.md), [ablation](ABLATION_STUDY.md), [optimization](PERFORMANCE_OPTIMIZATION.md) và [model protocol](MODEL_COMPARISON.md) để tái lập và hiểu giới hạn. Khi có labels phải freeze version/splits, validate hashes rồi chạy quality/paired analysis; không tune held-out test.
