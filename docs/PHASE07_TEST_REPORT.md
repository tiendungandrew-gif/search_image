# Báo cáo Prompt07 — Evaluation, benchmarking và optimization

Ngày thực hiện: 04/11/2026. Phase07 có framework/annotation/measurement deliverables; **semantic quality gate chưa được nghiệm thu khi chưa có human labels**. Người dùng đã yêu cầu tạo công cụ gán nhãn trước. Không bắt đầu Prompt08.

## A. Tóm tắt triển khai

Đã bổ sung frozen dataset/query snapshots, offline human-label workbench, strict label validation, Recall/Precision/Hit/MRR/nDCG/constraint metrics, grouped counts, seeded uncertainty helpers, immutable experiment/source archives, closed/open-loop load, safe runtime profiling, controlled A/B/BA object-check optimization và standalone report generation. Existing core/multimodal API/index/data được giữ.

## B. Tệp thay đổi

Backend modules `app/evaluation/{contracts,dataset,statistics,tracking,benchmark,quality,models,profiling,reporting,analysis}.py`, metric modules cũ được mở rộng tương thích; CLI evaluation/download model; SigLIP adapter; generic collection license; repository statement reuse; bounded object windows/config/private runtime endpoint. Annotation template, frozen28 queries/snapshot, experiment configs, suite/verifier commands và tests được bổ sung. Các báo cáo chuyên đề có tên đúng yêu cầu trong docs; README/current-state docs được cập nhật khi bàn giao.

Không sửa source fingerprint của CLIP image encoder/ingestion decoder, không overwrite baseline vectors, activate alternative model hoặc tạo fake metadata. Git commit có thể null do chưa commit/runtime không có git; source hashes/archives là fallback được ghi rõ.

## C. Dataset và ground truth

10 public sample images từ scikit-image-v0.25.2,28 query cases:12 single EN/VI,10 multi EN/VI,4 exact-identity,2 paired EN/VI.24 semantic cases cần human review. Actual UUID/hash/license/available/index-ready và content được kiểm. Family split giữ related queries cùng dev/test. Corpus nhỏ và chưa có nhãn không phù hợp scientific quality claims hoặc model selection.

[DATASET_AND_GROUND_TRUTH](DATASET_AND_GROUND_TRUTH.md) mô tả annotation protocol. Export draft không được tự thành verified; signed-off export cần tên/version/exhaustive review. Một số scenarios có thể no-answer; user phải xác nhận thay vì tự gán negative.

## D. Retrieval quality

Semantic Recall@1/5/10, Precision@10, MRR@10, nDCG@10 thực: **chưa đo**. Numeric unit fixtures không là evidence semantic quality. Graded/binary thresholds/no-answer/unknown denominators được định nghĩa tại [EVALUATION_METHODOLOGY](EVALUATION_METHODOLOGY.md). Exact-instance identity qua4 uploads thật: Recall@1/5/10=1, Precision@10=0,1, MRR@10=1, nDCG@10=1; chỉ chấm UUID/hash self-match, không thay semantic image similarity. [Raw identity](../evaluation/results/phase07/20261104T101005_evaluate_f6a6877b9f/result.json).

## E. Model comparison

Hai model thật đã chạy: CLIP512 revision3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268 và SigLIP2-768 revision75de2d55ec2d0b4efc50b3e9ad70dba96a7b2fa2; mỗi model dùng processor/tokenizer/manifest/collection riêng qua durable reindex path. Official checkpoint availability đã kiểm, weights tải riêng, không đổi active baseline. CPU-only cold/encoding/resources và index completeness được ghi trong actual experiment artifacts. Không claim multilingual/model superiority khi chưa có judgments.

## F. Latency/load

| Cấu hình | N thành công / lỗi | P50 ms | P90 ms | P95 ms | Thành công/s |
| --- | --- | --- | --- | --- | --- |
| [fast_default_head1](../evaluation/results/phase07/20261104T101019_benchmark_c505f295d7/result.json) | 500 / 0 | 107.44 | 145.80 | 150.90 | 8.65 |
| [image_after](../evaluation/results/phase07/20261104T094413_benchmark_016c347034/result.json) | 300 / 0 | 121.18 | 130.56 | 138.08 | 8.01 |

| Cấu hình | N thành công / lỗi | P50 ms | P90 ms | P95 ms | Thành công/s |
| --- | --- | --- | --- | --- | --- |
| [load_fast_c1](../evaluation/results/phase07/20261104T095051_benchmark_09d9264c9f/result.json) | 300 / 0 | 133.52 | 147.43 | 148.95 | 7.70 |
| [load_fast_c5](../evaluation/results/phase07/20261104T095132_benchmark_6fe8167b67/result.json) | 478 / 22 | 145.26 | 184.58 | 194.54 | 33.16 |
| [load_fast_c10](../evaluation/results/phase07/20261104T095149_benchmark_f713978774/result.json) | 217 / 283 | 198.95 | 229.47 | 241.15 | 30.08 |
| [load_fast_c20](../evaluation/results/phase07/20261104T095159_benchmark_1bff5d5b0d/result.json) | 68 / 432 | 257.24 | 312.77 | 372.66 | 19.50 |
| [load_mixed_open8](../evaluation/results/phase07/20261104T095205_benchmark_ddf52692ff/result.json) | 160 / 0 | 100.15 | 140.42 | 151.42 | 8.01 |

Mục tiêu Fast P90≤300ms/P95≤500ms đạt ở C1/corpus10/K10/CLIP float32/CPU4threads; không là SLO production. Fast full-server sample coverage500/500; client P90148,35ms/P95153,09ms. CPU Core7 240H/16 logical/15,11GiB RAM; peak sampled API RSS1.267,09MiB. Load5/10/20 errors4,4%/56,6%/86,4%, đều INFERENCE_BUSY; c20 chỉ68 successes/3,49s, không sustained-capacity proof.21 benchmark runs/7.360 attempts/737 errors được giữ. [Số liệu/biểu đồ/raw provenance](EXPERIMENT_RESULTS.md).


N/sample sizes, hardware/cache/concurrency/error accounting nằm trong từng result. Full ASGI/client/component boundaries tách riêng. No GPU results. Cache-cold OS/HNSW không được giả lập bằng model restart. Matrices có closed-loop1/5/10/20 clients và fixed-rate mixed load; overload outcomes được giữ.

## G. Multi-intent evaluation

AND/OR/2/3/4+/required/optional VI/EN query contracts và per-condition label UI đã có. Human UNKNOWN không bị coi false; model UNKNOWN là abstention. Constraint accuracy/coverage và overall success framework có thể chạy khi labels đầy đủ; actual semantic-condition success chưa đo. Không dùng cosine làm visual verification.

## H. Ablation

A0…A4 giữ cùng multi-intent query set; A3 là nonselective filter overhead, không selective-quality claim. Paired text-only/RRF/score dùng cùng paired IDs. Raw latency có thể so; Recall/nDCG/constraint gains/paired bootstrap quality chưa thực hiện vì thiếu labels. Không gộp incompatible tasks hoặc chọn best weights từ held-out data.

## I. Optimization

Profiling ban đầu500/C1 ghi object eligibility/checks mean34.48ms và vector retrieval44.58ms. Đã thêm bounded HEAD windows1/2 trong existing MinIO slots, bảo toàn rank/availability/error policy; ABBA300 requests/run/cùng query/seed, actual setting được sampler xác nhận. [PERFORMANCE_OPTIMIZATION](PERFORMANCE_OPTIMIZATION.md) và result artifacts ghi cả improvements lẫn residual bottlenecks, không quảng bá component-only gain như full speedup.

## J. Kiểm thử

- Backend **124 passed**:117 unit và7 integration thật (indexing/core/advanced/runtime), không skip trong lượt verifier cuối. [Log](verification/phase07/backend_tests.txt), [summary](verification/phase07/backend_tests.json).
- Frontend **10 unit passed**, TypeScript/ESLint/Vite build qua. [Log](verification/phase07/frontend_checks.txt).
- Playwright Chromium **14 browser tests passed** trên desktop/mobile, gồm2 tests công cụ annotation. Không tự gán nhãn corpus. [Log](verification/phase07/browser.txt).
- Python Ruff/format qua, Compose build/start/HTTP smoke/index preservation qua. [Verifier](verification/phase07/summary.json). Scientific benchmark chạy riêng, không suy kết quả benchmark từ flag functional benchmark_requested=false.
- Focused evaluator/report/ABBA suite **22 passed** sau chỉnh cách biểu diễn model repeats; real report generation từ32 experiments tạo JSON/CSV/Markdown và3 nhóm PNG/SVG. Không có semantic-quality chart khi thiếu labels.
- CLIP và SigLIP2 model comparisons thực đều measured, verify index10/10 và active pointer giữ nguyên. Dataset validation đối chiếu10/10 original hashes qua API thành công. Raw experiments ghi từng kết quả, không dùng doubles cho các phép này.

Một lượt focused pytest trong sandbox dừng ở test async/thread; đã dừng riêng process đó và chạy lại ngoài sandbox22/22 pass. Đây là giới hạn môi trường thực thi, không được bỏ qua rồi báo pass. Không còn lỗi functional test/lint/type chưa xử lý trong các checks đã chạy.

Một lượt Docker test đầu có2 failures do base runtime không cài git; experiment tracking đã sửa để dùng source archive/hash và git_status thay vì yêu cầu cài git. [Initial redacted log](verification/phase07/backend_tests_initial_no_git.txt) được giữ. Lượt model download đầu timeout/DNS/certificate; retry dùng system CA/TLS verification. Không có tests được báo pass dựa trên mock thay cho real integrations.

Metrics/load/accounting/report/contract tests dùng explicit fixtures; labels có human_verified trong unit fixtures không được sử dụng cho actual dataset. Real model/store/API integration và browser có artifacts riêng. Source fingerprints/JSON/links/secret scans và execution limitations phải được kiểm khi chốt report.

## K. Findings

1. CLIP fast C1 đạt mục tiêu đo trên10 ảnh; workload lớn và concurrency cao chưa đạt reliability cần thiết. Nhìn riêng P90 của successful requests ởc5/c10 sẽ che mất lỗi4,4%/56,6%.
2. HEAD2 giảm object-stage mean khoảng23% nhưng full mean/P90 không tốt hơn; giữ default1. Ranked IDs invariant trên12 queries/1.200 samples; semantic relevance regression vẫn chưa biết.
3. SigLIP2-768 load/index/query thật, cùng28 cases và index riêng; tốn init/RSS/encoding cao hơn CLIP trong lượt đo này, chưa có nhãn để đánh đổi chi phí với chất lượng.
4. Qdrant chỉ10 points và0 indexed HNSW vectors; ANN overlap không là retrieval relevance. PG join/tag plan nhanh ở corpus này, chưa có căn cứ thêm index mới.
5. Corpus0/10 captions,0/10 tagged images. Công cụ gán nhãn sẵn sàng nhưng240 semantic judgments chưa được điền; không thể chọn semantic model/fusion/rerank winner.

Không có bằng chứng quality-versus-latency winner khi chưa có human qrels. Candidate/ANN/model alternatives được trace theo model/index manifests; ANN overlap/self identity không thay semantic quality. Capacity phải xét error rate cùng latency, không chỉ nhìn fastest successful requests.

## L. Giới hạn và phần chưa nghiệm thu

Human semantic labels/quality gates, relevant large corpus, parser/translation accuracy, repeated representative stress, CUDA và cache-cold working set còn mở. Public samples có thể overlap pretraining, chưa audit.28 cases ít và same family translations có correlation, không đủ generalization. Exact hash dedup không bảo đảm loại near duplicates. Không claim toàn Phase07 research quality complete khi thiếu labels; tool/workflow đã chuẩn bị để người dùng tiếp tục annotation.

## M. Prompt08 readiness

Core có stable image IDs, private content URLs, source/license/dimension metadata, optional captions/tags và typed assessments. Profiling xác nhận0/10 captions và0/10 tagged images, chưa đủ evidence mô tả cho grounded explanations; semantic relevance/constraint verification còn giới hạn. RAG phải dùng evidence thật, không invent captions hoặc coi UNKNOWN là truth; latency budget cần đo riêng generation. Chưa triển khai RAG/Agent/multi-hop, không tự sang Prompt08.

## Checklist nghiệm thu cuối

- [x] Dataset/query snapshots, hash/UUID/index validation, không ghi đè dữ liệu cũ.
- [x] Công cụ annotation offline, draft/verified/export/import và strict label validation.
- [x] Metrics/formulas/tests/aggregation theo task/language/mode và denominators.
- [x] CLIP/SigLIP2 chạy thật, model/index compatibility và isolated reindex.
- [x] Latency/load/profiling/ABBA/ablation latency thực, raw failures được giữ.
- [x] JSON/CSV/Markdown/PNG/SVG, immutable experiments/source archives và CLI tái lập.
- [x] Backend/frontend/browser/lint/type/build checks đã chạy và qua.
- [ ] Người đánh giá hoàn tất24 queries/240 grade judgments và condition labels.
- [ ] Semantic Recall/Precision/MRR/nDCG, constraint quality và VI/EN comparisons trên nhãn đã review.
- [ ] Quality ablation/paired confidence intervals, quality–latency/model selection và corpus đủ đại diện.

**Kết luận:** đã bàn giao phần triển khai và thực nghiệm khả thi của Prompt07; toàn bộ research quality gate chưa được nghiệm thu khi chưa có human labels. Không bắt đầu Prompt08. Báo cáo chi tiết và artifact links tại [EXPERIMENT_RESULTS](EXPERIMENT_RESULTS.md); bước tiếp theo thuộc Prompt07 là dùng công cụ gán nhãn rồi chạy lại quality evaluation.

[Kiểm tra bàn giao cuối](verification/phase07/final_checks.json) ghi counts, readiness, source fingerprint/archive và kiểm tra secrets. [Danh sách source thay đổi so với Phase06](verification/phase07/source_changes.json):42 tệp thêm,16 tệp sửa,không tệp nào bị xóa; fingerprint194 source/config files, CLIP encoder/ingestion decoder giữ nguyên. Tài liệu và results được giữ riêng; Git chưa có commit. Link/JSON/traceability/11 structural Mermaid checks đã qua, không có tuyên bố render mới vì diagrams không đổi ở Phase07.

Sửa cuối ở evaluator: fast_targets_observed chỉ áp profile fast. Raw image-run cũ giữ boolean theo phiên bản framework đã chạy (so cùng ngưỡng số học), không được dùng làm bằng chứng Fast Search SLO; báo cáo hiện hành xác định SLO bằng profile và500 text requests ở cấu hình final.
