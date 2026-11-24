# Thiết kế hiệu năng và đánh giá retrieval

Cập nhật Phase 06: advanced latency đo tách single-intent baseline; [ADVANCED_SEARCH_TEST_REPORT](../archive/ADVANCED_SEARCH_TEST_REPORT.md) là evidence hiện hành cho E1–E5, before/after và quality chưa đo. Các số đo Phase 05 dưới đây giữ làm historical baseline.

Phiên bản 1.1.0 · 2026-11-03 · Baseline thiết kế Phase 02: budgets/cấu hình dưới là giả định, không là benchmark. Đầu vào đã đối chiếu PRD, SAD, storage và [API_SPECIFICATION](../architecture/API_SPECIFICATION.md). Chưa có model/corpus/hardware thực được chạy tại thời điểm lập baseline này.

Cập nhật Phase 05: đã chạy CLIP/Qdrant thật, benchmark warm CPU/concurrency1/corpus10 với100 requests mỗi modality. Full server P90 text134.70ms, image205.89ms; P95 text140.78ms, image222.70ms; 0 lỗi. Các target được quan sát trong workload giới hạn này, chưa là SLA. [SEARCH_TEST_REPORT](../archive/SEARCH_TEST_REPORT.md) có raw samples, before/after optimization, hardware và test evidence; [SEARCH_PERFORMANCE](SEARCH_PERFORMANCE.md) là hướng dẫn đo hiện hành. Quality metrics thực vẫn chưa đo do thiếu human judgments. Giữ các mục sau làm thiết kế nghiên cứu và kế hoạch mở rộng, không suy diễn các budgets thành số đo.

## 1. Objectives và biên đo

| Chỉ số | Mục tiêu / cách sử dụng |
| --- | --- |
| Fast Semantic Search P90 | ≤ 300 ms; giả thuyết cần kiểm chứng theo mode và môi trường |
| Fast Semantic Search P95 | Đề xuất ≤ 500 ms; không suy ra từ P90 |
| Optional Agent/RAG TTLast | Mục tiêu ≤ 3.000 ms; phụ thuộc model/provider/hops/output budget |
| Default K | 10; quality report vẫn tính Recall@1, Recall@5, Recall@10 |
| Recall@10 / nDCG@10 | Đo và tối ưu bằng judgments thật; numeric quality gates chưa được xác nhận |

Full server-response duration dùng monotonic clock từ lúc app nhận ASGI request scope trước body reading, tới khi final response-body send hoàn tất. Gồm app queue, decode/upload parse, inference, dependency transit nội bộ, hydrate và serialization/send. Không gồm external transit, browser render hoặc proxy/socket queue trước ASGI; các queue đó cần metric riêng. Search API có image upload phải tính parsing/decode, không bắt đầu timer sau khi đã nhận ảnh.

Client latency đo từ initiate request tới nhận hết body bằng clock của client; render là metric riêng. Không trừ hai clock khác nhau. Timer trong endpoint trước serialize là `processing_ms`, full response lưu metrics theo request_id, không thể biết chính xác trong chính JSON đang serialize. Content proxy download có timer riêng. Request opt-in explain/agent là augmented; vẫn đo full server latency nhưng báo nhóm riêng cùng retrieval-only span, không giấu generation bằng nhãn fast.

Warm run: model/processors và connection pools sẵn sàng, warmup workload tách sample. Cold run: process/model load, container/image availability và OS/model/query cache state ghi riêng. Model load xảy ra trước search-ready; báo startup-to-ready và first request ready riêng, không quảng bá first ready request như đã bao gồm model load. Cache-disabled và cache-enabled đều phải có nhãn; cold vector page cache không được giả bằng chỉ tắt query cache.

## 2. Latency budget dự kiến

Giả định warm fast path trên corpus/hardware sẽ được xác định; không phải p90 từng component. Image decode nằm preprocessing; fallback/rerank không được vượt total deadline. Chỉ là envelope ban đầu để tìm bottleneck:

| Component | Budget tham khảo (ms) | Ghi chú |
| --- | --- | --- |
| API/auth/body overhead | 15 | Upload body nhận chậm có thể vượt, vẫn phải đo |
| Query processing/decode | 20 | Text và ảnh đo riêng |
| Embedding inference/slot | 100 | Model/device chưa chọn; chưa biết đạt được |
| Vector search | 35 | C/HNSW/filter/working-set phụ thuộc corpus |
| Eligibility/filter | 10 | Authoritative predicates, unknown evidence |
| Optional rerank | 40 | Off mặc định; có thể không phù hợp budget |
| Metadata retrieval | 20 | Batch fetch, connection pooling |
| Serialization/final send | 10 | Field allowlist, response size bounded |
| Dự phòng app queue/dao động | 50 | Không phải quota để che các span không đo |
| Tổng envelope | 300 | 250 execution + 50 dự phòng |

**Không cộng P90 các component để kết luận end-to-end P90.** Các phân phối có tương quan, stage có thể overlap, và percentile của tổng khác tổng percentile. Full traces/raw request samples là nguồn kết luận. P95 cần đủ samples và đo trực tiếp; budget này có thể bị bác bỏ sau profile.

## 3. Dev defaults và timeout policy

Đây là lựa chọn triển khai khởi đầu, không suy diễn workload người dùng. Override phải typed, có bounds, document trong run và không âm thầm đổi API semantics.

| Cấu hình | Default đề xuất | Ý nghĩa |
| --- | --- | --- |
| Upload file/body | 20 MiB / 21 MiB | JSON/options tối đa 64 KiB; reject quá byte cap sớm |
| Decode | JPEG/PNG/WebP static, 25 triệu pixels, cạnh ≤10.000, 1 frame; deadline 2 s | Reject GIF/SVG/multiframe; resource-limited decoder process |
| Text | 2.000 chars và model token cap | Token overflow trả422, không truncate âm thầm |
| K/C | K=10, K≤100; C=max(100,K), C≤1.000 | Candidate entries toàn channels ≤1.000, channels ≤4; effective C giảm đều nếu tổng vượt cap |
| Constraints | ≤8 leaves, depth≤2 | AST và retrieval fan-out có giới hạn độc lập |
| Inference | API slots/device=1, queue≤8, queue wait≤50 ms | Mixed indexing không được chiếm search slot vô hạn; tuning sau hardware profile |
| Core request deadline | 2.000 ms full ASGI | Không phải SLO 300 ms; upload/body parse tính trong deadline |
| Explain/agent request deadline | 5.000 ms | TTLast 3.000 ms là objective, không phải guaranteed timeout |
| Dependency calls | PG/Qdrant online ≤250 ms/call và remaining deadline; content/object call ≤1.000 ms | Tránh reset timeout mỗi layer; response serialization vẫn cần thời gian |
| Body/decode deadline | min(2.000 ms, remaining request deadline) | Client upload chậm có thể timeout; client/body transit báo riêng |
| Worker | 1 item đồng thời ban đầu, batch≤1.000; embedding microbatch=1 đến khi profile | Offline batch tuning không tăng search contention không kiểm soát |
| Job attempts/lease | 5 attempts, lease60 s, heartbeat10 s, item deadline120 s | Full-jitter backoff: random(0,min(60 s,2^(attempt−1) s)); invalid permanent không retry |
| Agent | 3 hops, 6 calls, 512 output tokens | Client chỉ giảm caps; retry tính vào call budget; deadline bao gồm fallback |
| Telemetry/retention | Query temp cleanup ngay request end; crash temp≤1h; safe telemetry/jobs30d | Không lưu raw query mặc định; owner chốt trước nonfixture data |
| Rate limit | 60 search/phút/principal; 10 mutations/phút/principal ở một API process | Dev protection đề xuất; admission quan trọng hơn số rate; multi-replica cần shared enforcement trước exposure |
| Reconciliation/staging | 15 phút scan increment; orphan grace24h | Không xóa khi còn reference/active writer; không coi là SLA/RPO |

Fast path không retry online dependency tự động ban đầu; client có thể retry search nếu retryable. Worker retries riêng, agent retries chỉ khi còn budget. 429 là rate cap, 503 INFERENCE_BUSY là queue/admission saturation, 504 là exhausted deadline. DB pool/statement/lock timeouts và SDK cancellation phải được cấu hình thực ở Phase 03–05. Cancel thread/future không đảm bảo đã dừng GPU/decoder: worker isolation, slot giữ tới compute thật kết thúc hoặc process bị terminate; không release capacity giả.

## 4. Chiến lược tối ưu và điều kiện adoption

| Chiến lược | Đề xuất / rủi ro / bằng chứng cần |
| --- | --- |
| Model preloading | Load paired encoder/processor một lần; startup assertions trước readiness; ghi memory và startup time |
| Inference optimization | Eval/inference mode, warmup và preprocessing đúng model; mixed precision/compile/export chỉ sau equivalence/relevance check và hardware measurement |
| Cache | Chưa thêm Redis. Bounded in-process cache tùy chọn, off trong baseline uncached; key gồm manifest/index generation/filter/reranker version/auth scope; invalidation khi metadata/deletion đổi |
| Query image cache | Off mặc định do privacy và retention; không persist user image/hash để cache vô thời hạn |
| Vector index | Payload indexes đúng fields; tune C/ef/HNSW/memory theo dataset; exact neighbor diagnostic không thay relevance judgments |
| Offline batching | Tăng microbatch khi VRAM/RAM cho phép, backpressure và ưu tiên online; report mixed ingest/search workloads |
| Database calls | Batch get_many, joined eligibility, index FK/filter fields; không N+1 hydrate hoặc HEAD từng object trong search |
| Reranking | Off default, candidate cap, only supported models; E3 ablation so latency/quality, no silent mandatory-constraint relaxation |
| Routing | Deterministic, no LLM fast path; multi-intent bounded channels, agent explicit |
| Observability | Histogram/raw samples full response và stage spans; bounded nonblocking telemetry, drop counter; không để metrics sink outage chặn search |

Không tối ưu bằng thay đổi preprocessing/normalization mà không tạo manifest/index version mới khi làm đổi vector space. Quyết định model tốt nhất dựa quality/resource constraints đã chốt, không chỉ một metric thuận lợi.

## 5. Dataset, queries và ground truth

Corpus manifest ghi image UUID/digest/provenance/license, metadata snapshot và eligible universe. Chọn corpus hợp pháp trước, chưa tự ấn định số ảnh hoặc throughput. Đề xuất pilot query cân bằng G1…G5 để kiểm tra annotation guide; G5 chỉ evaluate khi entity facts có thật. Tách dev/test theo image/near-duplicate groups, seed và split manifest cố định; không tune trên held-out labels. Có thể stratify language/domain/constraint complexity, nhưng chưa claim tiếng Việt đạt chất lượng.

Grades đề xuất: 0 không liên quan, 1 liên quan yếu, 2 liên quan rõ nhưng chưa đủ mọi chi tiết, 3 khớp mục tiêu và điều kiện bắt buộc có evidence. Binary relevant threshold=2 cho relevance chung; G2/G4 còn báo all-required satisfaction riêng để grade2 không bị diễn giải là thỏa mọi điều kiện. Hai annotators độc lập cho pilot và các mẫu đánh giá chính trong phạm vi nguồn lực; bất đồng adjudication, guide/version/rater refs được lưu. Nếu thiếu nhân lực, báo single-annotator limitation thay vì giả inter-rater agreement.

Label absence = unjudged. Với corpus nhỏ dùng exhaustive judgments cho toàn eligible universe. Nếu dùng pooled candidates từ nhiều systems + random controls, phải ghi coverage và gọi recall là recall trên judged pool; không claim corpus recall. Trước final evaluation bổ sung judgments cho top-D outputs của mọi hệ thống được so sánh, không dùng labels đó để retune. Top-D chưa được judge làm run incomplete hoặc báo riêng, không tự chuyển thành negatives. Không có relevant images thì đưa no-answer group riêng.

| Group | Query/labels và điều kiện |
| --- | --- |
| G1 | Single-intent text, graded relevance, locale/domain |
| G2 | Multi-intent text, required/optional leaf labels satisfied/violated/unknown và AND/OR truth |
| G3 | Image reference bytes/hash và relevance; mặc định loại exact reference identity khỏi candidate universe để tránh self-match inflation; report policy |
| G4 | Text + image, joint relevance/constraint labels; ablation text-only và image-only cùng universe |
| G5 | Relation evidence, expected intermediate bindings, eligible final images; grounded task success không chỉ top result relevant |

## 6. Metric formulas

Với query q, Rq là tập ảnh relevant (grade≥2) trong eligible universe, Lq là ranking unique có thứ tự. Missing positions được pad nonrelevant cho fixed-denominator metrics; duplicate chỉ tính lần xuất hiện đầu và flag defect, không compact để nâng metric.

- **Recall@1:** `|Rq ∩ Lq[:1]| / |Rq|`; **Recall@5:** `|Rq ∩ Lq[:5]| / |Rq|`; **Recall@10:** `|Rq ∩ Lq[:10]| / |Rq|`, khi |Rq|>0.
- **Precision@10:** `relevant_count_in_first_10 / 10`, kể cả trả ít hơn 10.
- **RR@D:** `1 / first_relevant_rank` trong evaluated depth D, hoặc0 nếu không có. **MRR@D:** mean RR@D. Không gọi unrestricted MRR khi chỉ lấy D=10; final report ghi depth.
- **DCG@10:** `Σ(i=1..10) (2^grade_i − 1) / log2(i+1)`; **nDCG@10:** `DCG@10 / IDCG@10`, ideal order từ eligible judgments.

Recall@10 không phải mục tiêu recall10%. Ví dụ lấy đúng 3 trong 20 relevant vào top10 thì recall=0,15. Macro average per-query trong mỗi group, tổng hợp có explicit weighting và sample counts. |Rq|=0/IDCG=0 thì loại khỏi relevance aggregates (kể cả precision/MRR theo policy baseline), báo số lượng và no-answer behavior riêng. Corpus nhỏ hơn10 vẫn Precision@10 chia10; tránh đổi denominator giữa runs.

Constraint metrics: tỷ lệ returned images có mọi required clause confirmed; tỷ lệ queries có ít nhất một ảnh như vậy; báo unknown/violated coverage và zero-result queries. Grounded multi-hop success yêu cầu đúng relation bindings có evidence **và** final eligible relevant result; fallback hoặc unsupported relation không đạt full success. RAG đo valid citation coverage/unsupported claims bằng annotation/review, không dùng cosine làm grounding score.

## 7. Benchmark matrix và phương pháp chạy

| Experiment | Biến độc lập | Controls | Outputs |
| --- | --- | --- | --- |
| E1 | CLIP baseline; C/ANN settings trong tuning dev | Corpus/query/qrels/splits, hardware, load, K, no LLM/rerank | Recall@1/5/10, Precision@10, MRR@D, nDCG@10, latency/resource |
| E2 | SigLIP 2 hoặc multilingual model được biện minh; own compatible collection | Cùng universe/labels/query/load/hardware; preprocessing riêng checkpoint đúng | Quality/language breakdown, CPU/GPU/RAM/VRAM, latency/startup |
| E3 | Model được chọn + filtering/decomposition/fusion/rerank; từng ablation on/off | Fixed dev-selected params, test set untouched, cùng applicable G1…G4 | Quality + constraint satisfaction + added latency/cost |
| E4 | E3 + bounded agent/multi-hop/RAG; hop/call/output budgets | Cùng corpus/G5 facts/evidence/provider version/hardware/load | Grounded success, TTFirst/TTLast/full latency, tools, fallbacks, unsupported claims |

Unsupported modality/model/optional phase ghi N/A, không điền số. Điều chỉnh parameter chỉ dùng dev; freeze config trước test. ANN neighbor recall có thể so exact cosine neighbors riêng để chẩn đoán index, không gọi đó relevance Recall@10.

| Trục workload | Thiết kế experiment, chưa phải dữ liệu quan sát |
| --- | --- |
| Warm/cold | Nhiều independent cold starts; warmup đề xuất30s rồi stable sample window; ghi lý do nếu chưa steady |
| Corpus size | Sau khi biết corpus N, dùng deterministic nested subsets 10%/50%/100% nếu đủ labels; mỗi subset có eligible qrels riêng |
| Concurrency | Sweep1/2/4/8 ban đầu nếu tài nguyên cho phép; thêm open-loop offered-load sweep để lộ queue/coordinated-omission, ghi generator saturation |
| Inputs | Text/image-only/multimodal tách; byte size và resolution strata cho upload; G1/G2/G5 riêng |
| Cache | Disabled baseline, optional enabled run, OS/vector/model warm state ghi rõ |
| Mixed load | Search-only và search + ingestion; workload mix chỉ freeze khi product/hardware xác định |
| Rerank/agents | On/off, candidate/hop/call caps, failure/deadline outcomes; augmented không trộn vào fast objective |

Đề xuất mỗi steady run≥5 phút và hướng tới≥1.000 completed successful samples để tail estimate có ích; nếu workload nhỏ không đạt thì công khai sample limitation, không tuyên bố percentile ổn định. Chạy≥3 repeats cho cấu hình final nếu resources cho phép; không xem repeat samples cùng query là independent relevance judgments. Bootstrap confidence intervals quality theo query; latency theo time blocks/run để tránh giả độc lập. Ghi seed/method/repeat counts thực tế.

## 8. Run manifest, latency/load và error accounting

Mỗi run có run ID, source commit hoặc snapshot hash, dataset/query/qrel checksums, model immutable revision/processor/dimension/dtype, index config/hash/active count, K/C/filter/router/reranker/fusion versions, seed/splits, CPU/GPU/VRAM/RAM/disk/OS/drivers/runtime/package pins, service placement, network topology, generator, concurrency/offered QPS, warmup/window/drain, modality/bytes mix, cache state và resource traces. Retain per-request duration/outcome, rankings, labels coverage, safe tool spans và artifact hashes.

Quantile ban đầu nearest-rank: sorted sample index ceil(p*n), p=.50/.90/.95; document khác biệt với histogram/tool estimator. Báo successful request latency P50/P90/P95, failed request duration riêng, attempts/completions, successful/sec và total completed/sec. **Error rate = unsuccessful attempted requests / all attempted requests** trong measurement window; gồm client timeout/disconnect, không chỉ HTTP5xx. Drain outstanding requests rồi reconcile request IDs, không double-count server complete sau client timeout. Timeouts có duration deadline riêng, không drop để đẹp tail.

Đối với generator synchronous, internal token hooks ghi request-receipt→first generated token/last generated token. Nếu không có hooks: token timing null và chỉ full response latency, không coi heartbeat/empty/status là token. Planner/tool spans có safe names, durations/outcomes; không giả tổng tools bằng elapsed khi parallel overlap. Complete response metric từ middleware join request ID sau send.

## 9. Gate và những gì chưa đo

Chưa có observed latency, quality, throughput hoặc memory. Trước Phase 07 phải chốt dataset/rights/language/hardware/load/annotation guide/quality acceptance thresholds và freeze dev/test. Metric implementation cần hand-computed fixtures; load harness cần kiểm tra timer/error accounting. Nếu mục tiêu300/500ms không đạt, báo actual distribution, bottleneck và deviation/action; không đổi definition sau khi xem kết quả. Phase 02 chỉ tạo kế hoạch này, không chạy benchmark hoặc download model.

## 12. Evidence offline indexing Phase 04

Đã có CPU fixture profile/actual CLIP indexing timings tại [INDEXING_TEST_REPORT](../archive/INDEXING_TEST_REPORT.md), raw artifacts trong verification/phase04. Những số này không thay search P90/P95/Recall@10 targets hoặc evaluation protocols ở trên. Chưa có online retrieval benchmark, relevance judgments hoặc CUDA measurements.
