# Báo cáo nghiệm thu Phase 06 — Multimodal và Multi-intent Search

> Tài liệu lịch sử theo phase; lệnh trong nội dung giữ tên đường dẫn cũ. Hướng dẫn hiện hành tại [danh mục tài liệu](../README.md) và [scripts](../../scripts/README.md).

Ngày bàn giao: 04/11/2026. Timestamps từng lượt chạy giữ trong artifacts. Báo cáo cuối được đối chiếu với [verifier summary](../verification/phase06/summary.json), [runtime](../verification/phase06/final_runtime.json) và [source snapshot](../verification/phase06/source_snapshot.json). Chỉ nghiệm thu Phase 06; không tự triển khai Phase 07.

## A. Tóm tắt triển khai

Đã có combined text+image late fusion, multi-intent query analysis/decomposition tiếng Việt/Anh theo mẫu, typed AND/OR constraint AST, required/optional/negated conditions, bounded multi-query candidates và optional lightweight reranking. Core CLIP/Qdrant/PG/MinIO và fast single-vector path Phase 05 được giữ. UI dùng APIs thật, có mode/fusion/weights/rerank controls, real image previews và hiển thị điều kiện chưa xác minh.

Đây là baseline retrieval hoạt động trên corpus10 ảnh, không phải hệ thống hiểu ngôn ngữ hoặc xác minh thị giác tổng quát. Không có human relevance judgments, vì vậy chưa nghiệm thu quality improvement. Không có LLM/RAG/Agent/multi-hop trong search path. Functional smoke, tests và latency không thay thế quality labels.

## B. Tệp tạo hoặc sửa

| Phần | Tệp chính / thay đổi |
| --- | --- |
| Typed input | `backend/app/schemas/constraints.py`, `filters.py`, `search.py`: AST, validation, aliases, fusion/rerank options và additive response fields; Filters re-export giữ imports cũ |
| Query understanding | `backend/app/services/query/query_models.py`, `constraint_parser.py`, `query_classifier.py`, `query_decomposer.py`: bounded EN/VI patterns, grouping, uncertain fallback và relational refusal |
| Advanced retrieval | `backend/app/services/search/fusion.py`, `multi_intent.py`, `evidence.py`, `reranker.py`: actual candidate union/fusion, tri-state hard gate, stored-vector scoring, rerank budgets/fallback |
| Shared core/API | `search_service.py`, `backend/app/api/v1/search.py`, `health.py`, `backend/app/core/config.py`, `backend/app/main.py`: reuse encode/metadata/private result path, route telemetry, capabilities và OpenAPI |
| UI | `frontend/src/features/search/SearchWorkspace.tsx`, app badge/styles, API client/types: auto/multi-intent/paired modes, controls, score/evidence labels |
| Tests | `backend/tests/unit/test_advanced_search.py`, `backend/tests/integration/test_real_advanced_search.py`, cập nhật Phase05 compatibility test; frontend client test và browser flows |
| Evaluation/commands | `backend/app/evaluation/advanced_metrics.py`, `evaluation/scripts/evaluate_advanced.py`, mở rộng benchmark CLI, E1–E5 configs/label template, shared verifier --advanced, `scripts/verify_advanced_search.sh`, Makefile/.env.example |
| Tài liệu | [MULTIMODAL_SEARCH](../features/MULTIMODAL_SEARCH.md), [MULTI_INTENT_SEARCH](../features/MULTI_INTENT_SEARCH.md), [RERANKING_DESIGN](../features/RERANKING_DESIGN.md), [ADVANCED_SEARCH_API](../features/ADVANCED_SEARCH_API.md), [PHASE06_EVALUATION](PHASE06_EVALUATION.md), PHASE06_TEST_REPORT này; cập nhật baseline/current-state docs, evaluation README và ba architecture/sequence diagrams |

Không thay image encoder/ingestion decoder fingerprints, model weights/revision, schema, active index hoặc collection. Không tạo commit; source và cấu hình bàn giao có SHA256 inventory để đối chiếu. Không ghi query image vào corpus/jobs/MinIO.

## C. Query understanding

Hỗ trợ SINGLE_INTENT, MULTI_INTENT, IMAGE_SIMILARITY, TEXT_IMAGE và UNSUPPORTED_RELATIONAL_QUERY. NFC/whitespace normalization giữ dấu tiếng Việt; language là heuristic, không đánh giá multilingual retrieval. Original query luôn được bảo toàn cho whole-query retrieval.

Grammar nhận AND/và, OR/hoặc, parentheses với AND ưu tiên OR, comma list có conjunction rõ, required/optional prefixes và without/không có. Giữ nguyên “person wearing a red helmet” thành cụm; có/màu/đang/trong/gần/giống không tự thành các nhánh Boolean. Tag/city/source chỉ nhận metadata syntax có chủ đích hoặc explicit AST, không suy đoán từ caption. AST tối đa8 leaves/depth2, IDs unique; whole/image dành cho internal branches. Oversized metadata expressions và reserved IDs trả422 để bảo vệ whole-query/image signals.

Các mẫu không chắc chắn, chẳng hạn “black and white cat”, giữ toàn câu qua fast fallback và warning. Explicit AST vẫn authoritative. Nhận diện một số mẫu city where/thành phố nơi để trả409 UNSUPPORTED_RELATIONAL_QUERY; không tự đoán city hoặc gọi agent. Parser có coverage giới hạn, chưa có parser accuracy corpus.

## D. Multimodal search

Combined input dùng `/api/v1/search/multimodal`, JSON existing image_id hoặc upload multipart; text-only/image-only vẫn hỗ trợ. Text+image gửi qua core `/search` bị422 theo v1 routing design. Independent text/image vectors cùng manifest đi qua Qdrant rồi late fusion; không cộng vectors để giả lập compositional image editing.

Model thật: `openai/clip-vit-base-patch32`, registry ID `02593ce4-5531-49eb-8b46-89e6ecaef50c`, revision `3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268`,512 float32/L2/Cosine. Active index `6c3a8404-2971-46bf-ac9c-5c09bdec42b5`, generation1, collection `images_clip_v1_da55a7d099fd`, manifest SHA `7f843c0bf81c571eee3b12621fc41811cea174113e6802684e9063b447e707dc`. [Environment/model](../verification/phase06/environment_model.json) ghi actual runtime/config.

Ảnh query dùng decoder/image tower Phase 04–05, JPEG/PNG/WebP/byte/pixel/frame/resource bounds giữ nguyên; temporary bytes không được publish. UI gọi authenticated content proxy và tạo blob previews, token chỉ trong memory. [Desktop](../verification/phase06/desktop.png) và [mobile](../verification/phase06/mobile.png) được chụp sau khi cuộn và xác nhận cả10 previews đã giải mã; không dùng hardcoded result images.

## E. Candidate fusion

RRF/weighted_rrf alias dùng `sum(normalized_weight/(k+rank))`, defaultk60. Weighted-score đổi cosine sang[0,1] bằng `(clip(c,-1,1)+1)/2` rồi cộng theo weights. Đây là đổi thang xác định, chưa calibrated relevance probability. Default modality weights0.5/0.5; text share chia đều cho whole/per-clause branches. Không có image thì text channels có weights bằng nhau.

Missing branch contribution0, không renormalize theo document/empty branch hoặc giả missing cosine là actual score0. Dedup UUID, tie UUID deterministic, keep branch/rank/cosine/weight/contribution. Weights có bounds và không đồng thờizero. E3/E5 chạy cả hai methods nhưng chỉ có latency comparisons; chưa đủ human labels để chọn phương pháp tốt hơn.

## F. Multi-intent và logical constraints

Whole-query + selected positive semantic clause queries, batch text encode, tối đa4 vector channels/tổng requested entries≤1.000/union pool default100. Negative clauses được encode cho soft scoring, không tạo positive retrieval để giả absence. Paired input ưu tiên whole-query+image, các slots còn lại cho per-clause signals.

Top-level filters reuse payload pushdown và PG authoritative checks. Candidate metadata lấy batch; required AST hard-gate chạy độc lập rerank. AND ưu tiên tất cả required conditions, OR cho phép một required branch; optional branch không bypass mandatory condition. Known violated logical expression bị loại; missing/semantic evidence là UNKNOWN, best effort giữ và warning. Strict loại required metadata unknown; required semantic leaf trả409 VERIFIER_UNAVAILABLE. Metadata negative trên giá trị có thật có thể được verify; tags thiếu chưa chứng minh absence vì annotations không exhaustive.

Response canonical satisfied/violated/unknown và uppercase compatibility evidence giữ phân biệt rõ. High cosine chỉ hỗ trợ relevance ranking, không chuyển semantic condition thành VERIFIED_MATCH. Bounded pool có thể trả ít hơnK; không pad kết quả giả. E2 là multi-query union với whole-query cosine rescore; E3 fusion; E4 fusion+rerank; E5 paired fusion+rerank.

## G. Reranking

Lightweight reranker batch lấy stored candidate vectors, verify digest/manifest/dimension, tính actual whole/per-clause cosine. Whole relevance trong paired path kết hợp text/image signals theo weights. AND semantic score blend minimum/weighted mean, OR maximum; optional preference và metadata rewards tách riêng. Unknown/mismatch penalties có bounds, weights configurable, ranking_version=constraint-linear-v1 và score_type=reranker. [RERANKING_DESIGN](../features/RERANKING_DESIGN.md) ghi công thức đầy đủ.

Rerank off/request default, selected prefix default50 và≥K, timeout default200ms, outer request deadline2s. Không trộn tail raw RRF scores vào reranked scores. Failure/timeout theo error hoặc explicit skip+warning; không bỏ hard constraints hoặc publish partial ranking mutation. Model/digest mismatch không fallback. Basic search không phụ thuộc reranker. Có protocol thay thế khi tương lai có compatible VLM và quality/latency evidence; hiện không tải thêm model.

## H. API thực tế

[API examples](../verification/phase06/api_examples.json) lưu HTTP responses thật cho EN AND/OR, VI AND, paired RRF/weighted-score với “similar but red” và strict refusal. Integration còn kiểm image-only compatibility, existing image_id, text-only multipart, bad/empty inputs, metadata AND/OR/strict unknown và unsupported relational query. Returned IDs/metadata/URLs đến từ corpus và private stores thật.

[Validation guard cases](../verification/phase06/validation_guard_cases.json) xác nhận HTTP422 thật cho reserved constraint ID và oversized metadata expression, sau khi image mới đã chạy toàn suite. Không sửa source của image encoder hoặc index để xử lý hai input cases này.

Aliases query/search_mode, flat multipart weights/fusion/rerank hoặc canonical options JSON được validate; không trộn hoặc duplicate fields. Response bổ sung query_analysis, effective route/channels/vector calls/limits/versions, contributions, score components và evidence. Full-response ASGI metrics ghi sau final send; response processing_ms/latency_ms không bị gọi nhầm complete latency. Không query text/images/credentials trong metrics sink.

Runtime cuối search-ready200; metadata/objects/vectors/encoder/index healthy, advanced capabilities true, RAG/agent false. Năm foundation containers healthy; indexing-worker running, chưa có container healthcheck, heartbeat vẫn unknown. Alembic giữ `928b88dc3f68 (head)`. [Index preservation](../verification/phase06/index_preserved.txt) vẫn10 images/10 vectors, cùng IDs/manifest, không orphan hoặc missing embeddings.

## I. Retrieval quality

Recall@1/5/10, Precision@10, MRR@10, nDCG@10, constraint accuracy/verification coverage, overall constraint satisfaction và multi-intent success code đã có và unit-test bằng explicit numeric fixtures. Advanced evaluator hỗ trợ E1–E5, per-query và macro theo language, exhaustive corpus IDs, frozen requests/constraints/reference IDs và human judgments. Template chưa verified bị từ chối trước HTTP calls: [guard evidence](../verification/phase06/unverified_labels_rejected.json).

**Actual Recall/nDCG/constraint accuracy/multi-intent success: chưa đo.** [Quality status](../../evaluation/results/phase06_quality_status.json) ghi not_measured; [PHASE06_EVALUATION](PHASE06_EVALUATION.md) tách dataset/ground truth/configurations/latency evidence. Không có exhaustive human relevance/per-condition/overall-query labels, không sinh qrels từ CLIP/filenames hoặc coi self-match là accuracy. UNKNOWN predictions là abstention, accuracy trên verified predictions phải kèm coverage, không đổi unknown thành success.

Corpus10 thiếu nhiều motorcycle/helmet/rain/compositional-edit scenarios và quá nhỏ cho ablation đáng tin. Unit/integration tests chứng minh logic/pipeline, không chứng minh mọi query đúng ngữ nghĩa. [Evaluation README](../../evaluation/README.md) ghi annotation groups hai/ba/bốn+ conditions, required/optional, AND/OR, VI/EN, color/object/scene/appearance/background; quality ablations chờ adequate labels.

## J. Hiệu năng thực tế

Hardware: Intel Core7 240H/16 logical CPUs,15.11GiB total RAM; CPU inference4 Torch threads, Python3.12.12, Torch2.15.0+cpu, Transformers4.57.6, Pillow12.3.0, NumPy2.5.4, Qdrant client1.20.0, FastAPI0.162.0. Model/index như mụcD; corpus10/K10/C50, warm model/pools, warmup5 riêng, concurrency1, không query-result cache. Mỗi cấu hình100 measured requests, join đủ100 full server samples; client latency/stages/result IDs/errors giữ trong raw JSON. Nearest-rank ceil(p*n), successful-only percentiles kèm error counts. Không cộng stage percentiles.

| Cấu hình | Requests / errors | P50 ms | P90 ms | P95 ms | Requests/s |
| --- | --- | --- | --- | --- | --- |
| E1 · single-intent text | 100 / 0 | 104.14 | 145.30 | 148.12 | 8.670 |
| E1 · image-only | 100 / 0 | 129.71 | 137.39 | 141.13 | 7.617 |
| E2 · multi-query + whole rescore | 100 / 0 | 152.41 | 164.38 | 165.79 | 6.658 |
| E3 · multi-intent RRF | 100 / 0 | 119.30 | 156.15 | 157.76 | 7.685 |
| E3 · multi-intent weighted score | 100 / 0 | 113.75 | 156.16 | 158.75 | 7.966 |
| E4 · multi-intent RRF + rerank | 100 / 0 | 156.59 | 165.40 | 167.29 | 6.460 |
| E5 · text+image RRF + rerank | 100 / 0 | 156.21 | 172.30 | 188.17 | 6.231 |
| E5 · text+image weighted score + rerank | 100 / 0 | 155.87 | 168.69 | 176.07 | 6.270 |

Single-intent before P90 **143.85ms**, after **145.30ms**; **100/100 requests giữ nguyên ranked UUIDs**. Cả fast text và image quan sát P90≤300ms/P95≤500ms, trong đúng corpus10/warm/concurrency1 này. Các paths advanced cũng được ghi riêng; không suy ra SLA hoặc strategy superiority.

Raw outputs: [E1 text](../../evaluation/results/phase06_E1_text.json), [E1 image](../../evaluation/results/phase06_E1_image.json), [E2](../../evaluation/results/phase06_E2.json), [E3 RRF](../../evaluation/results/phase06_E3_rrf.json), [E3 weighted score](../../evaluation/results/phase06_E3_score.json), [E4](../../evaluation/results/phase06_E4.json), [E5 RRF](../../evaluation/results/phase06_E5_rrf.json), [E5 weighted score](../../evaluation/results/phase06_E5_score.json). Advanced samples luân phiên EN/VI AND/OR, mỗi subgroup25 requests; subgroup latency không là language quality evaluation.

Before/after single-intent dùng cùng4 queries, pinned model/index/corpus/hardware, warmup5/concurrency1: [before](../../evaluation/results/phase06_single_before.json) và [regression artifact](../verification/phase06/single_intent_regression.json) ghi actual P50/P90/P95/rate và exact ranked UUID comparison. Không có statistical confidence intervals; không suy non-inferiority hoặc quality improvement từ một lượt đo.

Advanced component costs có analysis/decomposition, batch text/image inference, Qdrant query_points, fusion, batch metadata/filter, reranking và private object checks. Stored candidate vector reads được báo riêng trong effective settings, nằm trong full latency/rerank span khi rerank bật; E2 whole-query rescore có thêm stored-vector read trong total. Đây không phải claim rằng mọi micro-operation có span độc lập. Paired forward và object checks còn chi phí thật; không bỏ validation/privacy để giảm latency.

Mục tiêu fast P90≤300ms/P95≤500ms chỉ được đánh giá trong workload fast trên máy/corpus này. Advanced paths đo riêng và không được giấu vào fast distribution. Một run RRF/score không đủ kết luận superiority; chưa có sustained stress, mixed indexing/search load, cold-start, large-corpus/HNSW working-set, CUDA hoặc confidence bounds.

## K. Automated testing

| Kiểm tra | Kết quả cuối / bằng chứng |
| --- | --- |
| Backend unit + real integration | **101 passed**, gồm95 unit và6 real integration; [log](../verification/phase06/backend_tests.txt) |
| Frontend unit/type/lint/build | **10 unit passed**, TypeScript/ESLint/Vite build qua; [log](../verification/phase06/frontend_checks.txt) |
| Browser desktop/mobile | **12 passed**,0 skipped/flaky/unexpected; tất cả paired previews được kiểm decode sau cuộn; [summary](../verification/phase06/browser.json) |
| Build/start/HTTP smoke | Qua Compose build/start và live/ready/OpenAPI/docs/UI/proxy; [summary](../verification/phase06/summary.json), [smoke](../verification/phase06/http_smoke.txt) |
| Benchmarks |8×100=**800 requests thành công**,0 lỗi, full server coverage100/100 mỗi cấu hình; raw samples tại mụcJ |
| Preservation |10 images/10 points, same index/manifest, không orphan/missing embedding; [verify](../verification/phase06/index_preserved.txt) |

Unit mocks chỉ kiểm logic/errors/scoring/metric formulas; integration dùng CLIP/Qdrant/PG/MinIO thật. Rerank failure và timeout cases monkeypatch riêng reranker/timing trong actual app, không được gọi là real dependency outage. Có regression batch/retry/idempotency/recovery indexing Phase 04, Phase05 text/image/invalid/missing collection/index mismatch và no query-ingest writes.

Một lượt verifier sau khi phiên làm việc đổi bị dừng ở browser vì Node/npm/Chromium đặt trong /tmp đã bị dọn; [environment failure](../verification/phase06/verifier_missing_node.json) giữ trạng thái đó. Đã khôi phục đúng Node22.23.4/npm11.21.1 từ image frontend và Chromium156.0.8078.4 vào project tools/cache, rồi chạy lại verifier. Đây là dependency của môi trường kiểm thử, không được coi là browser tests đã pass ở lượt bị dừng.

Lượt mở rộng assertion ảnh trên mobile ban đầu chờ mọi offscreen lazy image giải mã trước khi cuộn, nên11 passed/1 failed. Đã sửa test theo user flow: cuộn từng ảnh, giữ per-image naturalWidth>0 và all-images assertion; chạy lại đủ desktop/mobile. [Resolved check](../verification/phase06/browser_lazy_loading_check.json) giữ failed-run stats và cách giải quyết; đây là test assumption đã sửa, không bỏ preview assertion. Warnings SDK Qdrant về HTTP private network và NO_COLOR/FORCE_COLOR là nonfatal; public TLS chưa thuộc local MVP.

Lệnh tái chạy từ root:

```bash
bash scripts/verify_advanced_search.sh --requests 100
bash scripts/benchmark_search.sh multi_intent --requests 100 --rerank
bash scripts/benchmark_search.sh multimodal --requests 100 --fusion weighted_score --rerank
```

Prerequisites host backend venv/HTTPX, Docker access, Node/npm/Playwright Chromium theo SETUP. Máy phát triển dùng sg docker -c khi shell chưa refresh groups. Verifier đọc .env vào child environment và redact logs, không truyền token qua CLI args hoặc lưu raw Authorization headers. Kiểm tra cuối lint/format/type/build, shell syntax, JSON/docs links, source fingerprints và private secret ignores ghi tại [final checks](../verification/phase06/final_checks.json).

## L. Vấn đề và giới hạn còn mở

- Chưa có human judgments/quality gates, parser accuracy hoặc multilingual encoder evaluation; corpus10 không đại diện nhu cầu thực tế.
- Pattern parser có thể không hiểu idioms/ambiguous scope/negation hoặc relational paraphrase ngoài allowlisted patterns. Supported grammar có caps và warnings; high similarity không verify visual conjunction/color/spatial/absence.
- Best-effort UNKNOWN có thể trả incomplete matches; strict semantic verifier chưa có. Metadata source/city/dimension matching chỉ chứng minh predicate metadata, không tự chứng minh nội dung ảnh.
- Candidate/branch/rerank limits có thể làm thiếu relevant items, missing metadata giảm strict coverage. Không calibrated score threshold hoặc claim fusion/rerank tốt nhất.
- Preview chưa có thumbnails riêng trong fixture, fallback original; chưa đánh giá public auth/TLS/multi-tenancy hoặc concurrent mixed load. CUDA/cold/large-corpus chưa đo.
- Core/request evidence chưa persist thành research database; metrics ring có giới hạn10.000/process, không durable observability backend. RAG/explanation/Agent/multi-hop vẫn tắt.

Các hạn chế trên được công bố, không thay bằng số liệu hoặc metadata giả. Mọi test failure còn tồn tại phải được giải quyết trước final acceptance; xem counts/status ở mụcK và verifier summary.

## M. Sẵn sàng cho Phase 07

Đã có paired encoders/index manifest, whole-query/multi-query/fusion/rerank configurations E1–E5, metrics với abstention, human-label schema, raw full-server/client samples, stable IDs và source/model/environment artifacts. Có thể mở rộng benchmark corpus/query groups, so multilingual encoder/model variants, statistical repeated runs và quality-versus-latency/ablation sau khi freeze actual labels/corpus/dev-test split và hardware/load.

Những nghiên cứu đó chưa được thực hiện trong Phase 06. Không tự tải/chọn model khác, gán qrels hoặc bắt đầu Phase 07. Bàn giao advanced retrieval hoạt động và các giới hạn chất lượng/hiệu năng được ghi rõ.
