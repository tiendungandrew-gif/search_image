# Ablation có kiểm soát — Phase 07

Các JSON configs thực tại `evaluation/experiments/phase07/`, dùng immutable source/dataset/query manifests và cùng seed/K/candidate budget. CLI không tạo labels từ model. Latency ablation có thể chạy khi chưa có nhãn; quality ablation phải chờ human verified judgments.

## Text multi-intent

| Mã | Điều kiện |
| --- | --- |
| A0 | Giữ nguyên whole text, mode=text, không AST fan-out/rerank |
| A1 | Whole+per-clause retrieval, final whole-query cosine rescore |
| A2 | Multi-query RRF final fusion |
| A3 | A2 thêm media-type filter bao phủ mọi media type trong current corpus |
| A4 | A3 thêm lightweight constraint-aware rerank |

Các run A0…A4 chọn cùng10 multi-intent cases, không trộn paired cases vào một run rồi gọi comparable baseline. A3 là **nonselective filter overhead experiment**, không chứng minh selective filtering quality gain; filter JPEG/PNG/WebP giữ cùng eligible corpus hiện tại. Nếu đổi predicate làm eligible universe khác, cần qrels đúng filter context, không so như cùng task.

A1 dùng RRF để chọn bounded preliminary union rồi rescore whole vector; không phải unlimited whole-corpus candidate union. Caps/fan-out/unknown evidence/strict policies vẫn áp dụng. A0 không trả semantic assessments không có nghĩa human conditions false; human satisfaction scoring phải dựa labels trên returned IDs, verification coverage báo riêng.

## Paired ablation

A5_text dùng chính2 paired query IDs/texts nhưng bỏ image signal; A5_rrf/A5_score dùng cả text+image và cùng reranker. Task identity/query set giữ nguyên, executed mode được ghi để thể hiện signal bị ablate. Đây là modality experiment khác text multi-intent; không gộp quality averages với A0…A4. RRF và score khác numeric scales, không dùng raw score lớn hơn để tuyên bố chất lượng tốt hơn.

## Statistics và kết luận được phép

Quality harness kiểm same dataset/query/labels hashes, paired query IDs và source config; cluster bootstrap theo content family giữ VI/EN pairs. Không có adequate human data thì không có Recall/nDCG/constraint-gain CI, không suy “nhiều stage tốt hơn”. Tập paired chỉ một family rất nhỏ nên không đủ independent groups cho robust CI. Corpus10/K10 gây recall saturation và giới hạn generalization.

Latency đã được định nghĩa theo full ASGI, đủ samples và actual errors; chart/report dùng raw experiments. [EXPERIMENT_RESULTS](EXPERIMENT_RESULTS.md) ghi số thực và phạm vi còn unavailable. Source archives/configs giữ khả năng tái lập; không tune held-out labels hoặc tự chọn best model trước annotations.

## Latency thực tế, chưa có quality scores

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

Mỗi run300/C1/0 errors, HEAD2; settings và raw IDs được lưu. Chưa có resource samples riêng từng A-run và chưa có semantic labels nên không kết luận thành phần nào cải thiện chất lượng. Quality evaluator `evaluate --labels ... --config .../A0.json` đến A5 dùng chính request_options của benchmark; numeric HTTP fixtures kiểm việc chọn scope/ranking-metric denominators, không thay actual human labels.
