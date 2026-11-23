# Đánh giá Prompt06 — dataset, ground truth và E1–E5

> Tài liệu lịch sử theo phase; lệnh trong nội dung giữ tên đường dẫn cũ. Hướng dẫn hiện hành tại [danh mục tài liệu](../README.md) và [scripts](../../scripts/README.md).

Ngày tổng hợp 04/11/2026. Đã thực thi functional tests và latency benchmark; actual retrieval quality **chưa đo** do thiếu human-verified judgments. [PHASE06_TEST_REPORT](PHASE06_TEST_REPORT.md) là báo cáo nghiệm thu đầy đủ A–M; [quality status](../../evaluation/results/phase06_quality_status.json) và raw samples ghi rõ phạm vi bằng chứng.

## 1. Dataset và model cố định

Corpus hiện có10 ảnh công khai từ scikit-image-v0.25.2, license/provenance theo [sample manifest](../../datasets/sample_manifest.json). PostgreSQL/MinIO/Qdrant đã được verify cùng10 image IDs/vectors sau tests. Không thêm ảnh query vào dataset hoặc tạo captions/tags/labels suy đoán.

Paired model `openai/clip-vit-base-patch32`, revision `3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268`,512 float32/L2/Cosine; active index `6c3a8404-2971-46bf-ac9c-5c09bdec42b5`, generation1, collection `images_clip_v1_da55a7d099fd`. Hardware CPU Core7 240H/16 logical CPUs,4 Torch threads,15.11GiB total RAM. [Environment/model](../verification/phase06/environment_model.json) và [source snapshot](../verification/phase06/source_snapshot.json) ghi phiên bản/hash/config.

## 2. Ground truth và metric definitions

Chưa có corpus relevance judgments do người đánh giá xác nhận. [Advanced template](../../evaluation/relevance_labels/advanced_template.json) giữ human_verified=false/exhaustive_judgments=false và bị evaluator từ chối. Không đánh dấu verified để chạy số liệu, không tạo nhãn từ CLIP scores/filenames hoặc dùng unit fixtures làm real qrels.

Annotator cần freeze corpus IDs/index/request AST và ghi mỗi query: query_id, language/groups, request(text và optional reference image_id thật), exhaustive grades0…3 cho mọi corpus image, per-constraint true/false/null judgments và overall_satisfied_image_ids thỏa toàn AND/OR logic. Ghi annotator/provenance/version/dev-test split trước tuning. Cần groups hai/ba/bốn+ conditions, required/optional, AND/OR, VI/EN, paired color/object/scene/appearance/background; corpus10 chưa đủ các scenarios này.

Metric code và numeric unit fixtures đã chạy: Recall@1/5/10, Precision@10, MRR@10, nDCG@10; constraint accuracy chỉ trên verified predictions có known human truth, báo coverage riêng; UNKNOWN là abstention. Multi-intent success@10 yêu cầu ít nhất một actual Top10 image trong human overall_satisfied set. Constraint satisfaction@10 là tỷ lệ returned images được overall labels xác nhận. No-answer/unknown-label denominators được tách, không nhận success giả. Hướng dẫn/CLI tại [evaluation README](../../evaluation/README.md).

**Actual Recall@10, nDCG@10, constraint satisfaction/accuracy và multi-intent/multimodal quality: N/A, chưa đo.** Chưa có chất lượng hoặc improvement percentage hợp lệ để so methods, chọn weights hoặc thực hiện quality ablation. Việc parser xử lý dấu tiếng Việt không chứng minh multilingual embedding quality.

## 3. Cấu hình thực nghiệm

[Experiment configs](../../evaluation/experiments/phase06.json) và benchmark/evaluation scripts hỗ trợ:

| Mã | Retrieval / final ranking |
| --- | --- |
| E1 | Whole-query text cosine; image-only compatibility đo riêng |
| E2 | Whole+per-clause candidate union, final whole-query cosine rescore |
| E3 RRF / score | Multi-query với weighted RRF hoặc affine-normalized cosine fusion |
| E4 | Multi-query RRF rồi lightweight constraint-aware rerank |
| E5 RRF / score | Paired text+image fusion rồi cùng reranker, so hai fusion methods |

DefaultK10/C50, fan-out≤4/tổng requested entries≤1.000, union cap100, rerank prefix≤50. Weights/k/penalties là defaults chưa tune bằng labels. E2 dùng RRF cho preliminary pool cap rồi rescore whole-query; candidate truncation policy vẫn có thể ảnh hưởng recall. E5 rerank trên corpus10 có thể làm final ordering tương tự giữa fusion methods do union bao phủ cùng ảnh; không suy superiority khi không có human labels.

## 4. Kết quả latency đã đo

Mỗi cấu hình100 measured requests/warmup5 riêng/concurrency1, CPU warm model/pools, không query-result cache, full ASGI final-send duration join đủ100 samples. Advanced workload luân phiên EN/VI AND/OR,25 samples/group. Text baseline dùng đúng4 queries Prompt05; image reference là coffee.png, decode/inference thật mỗi request. Client duration/processing duration/full server duration tách trong artifacts.

| Cấu hình | P50 ms | P90 ms | P95 ms | Requests/s | Errors |
| --- | --- | --- | --- | --- | --- |
| E1 text | 104.14 | 145.30 | 148.12 | 8.670 | 0/100 |
| E1 image | 129.71 | 137.39 | 141.13 | 7.617 | 0/100 |
| E2 | 152.41 | 164.38 | 165.79 | 6.658 | 0/100 |
| E3 RRF | 119.30 | 156.15 | 157.76 | 7.685 | 0/100 |
| E3 weighted score | 113.75 | 156.16 | 158.75 | 7.966 | 0/100 |
| E4 | 156.59 | 165.40 | 167.29 | 6.460 | 0/100 |
| E5 RRF | 156.21 | 172.30 | 188.17 | 6.231 | 0/100 |
| E5 weighted score | 155.87 | 168.69 | 176.07 | 6.270 | 0/100 |

Raw JSON: [E1 text](../../evaluation/results/phase06_E1_text.json), [E1 image](../../evaluation/results/phase06_E1_image.json), [E2](../../evaluation/results/phase06_E2.json), [E3 RRF](../../evaluation/results/phase06_E3_rrf.json), [E3 score](../../evaluation/results/phase06_E3_score.json), [E4](../../evaluation/results/phase06_E4.json), [E5 RRF](../../evaluation/results/phase06_E5_rrf.json), [E5 score](../../evaluation/results/phase06_E5_score.json). Percentiles nearest-rank ceil(p*n), không cộng stage percentiles. Tổng800 successful/0 errors; failures không bị loại khỏi error-rate denominator.

Single-intent before P90 143.85ms, after145.30ms;100/100 requests giữ nguyên ranked image IDs. [Before](../../evaluation/results/phase06_single_before.json) và [regression](../verification/phase06/single_intent_regression.json) giữ actual samples/comparison. Các run tách thời điểm, chưa có confidence intervals; không coi mức chênh này là chứng minh non-inferiority hoặc cải thiện thuật toán.

## 5. Diễn giải và giới hạn

Fast text/image quan sát P90≤300ms/P95≤500ms trong điều kiện này; advanced paths được đo riêng. Không suy SLA từ corpus10/warm/concurrency1. Chưa đo cold-start, sustained/mixed indexing load, large HNSW working set, CUDA hoặc nhiều clients. Whole/clause/image forwards, metadata/object checks và JSON serialization có chi phí thật; không bỏ privacy/eligibility để làm benchmark đẹp.

Không có vision verifier, nên semantic color/object/spatial/absence constraints vẫn UNKNOWN. Metadata evidence chỉ xác nhận predicate metadata. Strict semantic requests trả409 thay vì claim verified; best effort có thể trả incomplete matches với warning. Label coverage, parser accuracy và calibrated fusion/rerank weights còn mở. Prompt07 có thể mở rộng corpus/labels/model comparison/statistical runs khi được yêu cầu, chưa tự thực hiện.
