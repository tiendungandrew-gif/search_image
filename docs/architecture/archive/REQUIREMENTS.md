# Requirements and Measurement Plan

Baseline: 1.0.0, 2026-11-03. Source of scope: [MASTER_SPEC.md](MASTER_SPEC.md). `MUST` denotes a phase acceptance requirement; `SHOULD` requires a documented rationale if omitted. P2 requirements apply when that optional feature is enabled. A target is not an observed result.

## Bổ sung thiết kế Phase 02

Danh mục yêu cầu gốc được giữ nguyên. [PRD](../PRD.md) mở rộng inputs/processing/outputs/dependencies/acceptance cho từng requirement, dùng ID chuẩn `FR-001…023` tương ứng trực tiếp `FR-01…23`, `NFR-001…012` tương ứng `NF-01…12`; SEC-01…08 không đổi. FR-024 làm rõ generation/validation compatible embeddings vốn thuộc FR-01/02/08, không thay requirement cũ. [DESIGN_REVIEW](../DESIGN_REVIEW.md) có traceability tới component, schema, API, test thiết kế và phase thực hiện. Tại Phase 02 chưa chạy runtime tests hoặc benchmark. Giá trị giới hạn khởi đầu trước đây để mở nay được đề xuất ở [PERFORMANCE_DESIGN](../../research/PERFORMANCE_DESIGN.md); chúng chưa được chứng minh phù hợp hardware/corpus thật.

## 1. Functional requirements

| ID | Priority | Requirement and acceptance evidence | Primary phase |
| --- | --- | --- | --- |
| FR-01 | P0 | MUST retrieve real indexed images from nonempty text using compatible multimodal encoders; integration fixture demonstrates relevance ordering and valid IDs | 05 |
| FR-02 | P0 | MUST retrieve from a validated reference image without requiring text; image-query integration case succeeds | 05 |
| FR-03 | P0 | MUST support K, default 10, with configured upper bound; return at most K unique eligible IDs and allow fewer/zero results | 05 |
| FR-04 | P0 | MUST accept approved upload/dataset inputs, validate, hash, preprocess, embed, store, and track indexing; an end-to-end item becomes searchable | 04 |
| FR-05 | P0 | MUST prevent byte-identical duplicate assets and duplicate image/model/index records, including concurrent submissions; uniqueness and retry tests verify behavior | 04 |
| FR-06 | P0 | MUST expose image metadata, provenance, lifecycle, storage identity, and version linkage; metadata/image/vector IDs remain consistent | 04 |
| FR-07 | P0 | MUST run indexing outside request-critical search execution, support batches, persisted progress, bounded retries, per-item failures, crash recovery, and reconciliation | 04 |
| FR-08 | P0 | MUST version embeddings/indexes and support reindexing with compatibility checks and controlled activation/rollback; mismatch is rejected | 04–05 |
| FR-09 | P0 | MUST implement the versioned endpoint inventory in the master spec as features arrive; document request/response schemas, validation, errors, auth, and applicable pagination | 02–05 |
| FR-10 | P0 | MUST provide responsive text/image search, preview, mode/K controls, grid, details/metadata, loading/empty/error states; desktop/mobile browser flows verified | 10 |
| FR-11 | P0 | MUST evaluate retrieval quality using actual relevance judgments and fixed versioned inputs; report metrics without fabricated outputs | 07 |
| FR-12 | P0 | MUST instrument server-response timing and run controlled load measurements with reproducible manifests | 05, 07 |
| FR-13 | P1 | MUST support combined image/text inputs through explicit, versioned fusion; compare methods and expose score semantics | 06 |
| FR-14 | P1 | MUST distinguish single-intent, multi-intent, and multi-hop requests using a lightweight documented router; multi-intent alone must not invoke an agent | 06 |
| FR-15 | P1 | MUST decompose supported multi-intent queries into required/optional constraints; preserve unknown evidence and evaluate constraint satisfaction | 06 |
| FR-16 | P1 | MUST support validated metadata filters with authoritative eligibility checks; unavailable/missing mandatory fields cannot silently pass | 06 |
| FR-17 | P1 | MUST support optional versioned reranking and configurable candidate count; compare quality and added latency against no-reranker baseline | 06–07 |
| FR-18 | P1 | SHOULD introduce lexical/semantic hybrid retrieval only if an experiment justifies the extra complexity; a decision records adoption or deferral | 06–07 |
| FR-19 | P2 | MUST generate explanations only from supplied retrieved evidence with specific supporting image IDs; unsupported visual claims must be omitted/qualified | 08 |
| FR-20 | P2 | MUST separate retrieval and generation; disabling the generator preserves core API behavior | 08 |
| FR-21 | P2 | MUST support bounded relational multi-hop execution, intermediate state, tool traces, evidence validation, and explicit fallback; no infinite loops | 09 |
| FR-22 | P2 | MUST use PostgreSQL relations initially for entity lookup and expose typed tools for search, metadata, filtering, reranking, and related entities as needed | 09 |
| FR-23 | P1/P2 | MUST show filters and optional explanation/evidence panels only when supported; return clear capability errors for disabled modes | 06, 08–10 |

Image-only retrieval is P0 even if its core API uses multipart transport or an uploaded image reference; transport choice cannot defer the feature. Optional captioning is not necessary for FR-01/02.

## 2. Non-functional requirements

| ID | Requirement | Verification/gate |
| --- | --- | --- |
| NF-01 | Core search objective P90 ≤ 300 ms; proposed P95 ≤ 500 ms under a named workload/environment | Phase 07 and final report; report measured attainment or deviation |
| NF-02 | Optional Agent/RAG objective TTLast ≤ 3 s; record TTFirst, TTLast, complete response latency, and each tool duration | Prompts 08–09; provider/hardware/output budget recorded |
| NF-03 | Invalid queries, corrupt/unsupported images, unavailable dependencies, inference errors, timeouts, and overload MUST produce safe structured errors | Unit/integration and failure-injection tests, Phase 11 |
| NF-04 | Requests, inference concurrency, candidate counts, uploads, retries, and agents MUST have finite configured limits | Config review and boundary/timeout tests |
| NF-05 | Cross-store writes MUST be recoverable and idempotent; only ready assets in a compatible active index can appear | Worker-crash/partial-failure/reconciliation tests |
| NF-06 | APIs/models MUST be typed; modules have explicit interfaces; logs structured and correlated; configuration validated at startup | Lint/type/static checks and startup/integration tests |
| NF-07 | Environments, datasets, model artifacts, indexes, experiments, and migrations MUST be reproducible and versioned | Clean-environment reproduction, Phase 12 |
| NF-08 | Capacity claims MUST name corpus size, modality mix, concurrency, QPS, hardware, and index settings | Benchmark manifest; scale remains unspecified until approved |
| NF-09 | Fast search MUST work with agent/generation features disabled or unavailable | Regression tests at Prompts 08–11 |
| NF-10 | Health/readiness MUST reflect required services, active compatible index, and loaded model; optional agent failure must not mark core unready | Dependency and feature-flag tests |
| NF-11 | Search ranking MUST be deduplicated and stable under ties; scores MUST be labeled and never described as probabilities without calibration evidence | Retrieval contract tests |
| NF-12 | Secrets and image/query content MUST NOT appear in source control or routine logs; debug evidence requires explicit controls | Secret/config/log review |

No throughput, availability, recovery-time, or numeric quality SLO is invented here. Their workload-dependent acceptance thresholds must be agreed and versioned before tuning and held-out evaluation, with amendments rather than retroactive target changes.

## 3. Security requirements

| ID | Requirement | Acceptance evidence |
| --- | --- | --- |
| SEC-01 | MUST enforce upload byte, decoded pixel, frame, and processing limits; validate decoder output against an allowlist, independent of extension/MIME claims | Oversized, decompression-bomb, invalid-format, and corrupt-file cases |
| SEC-02 | MUST generate safe IDs/object keys; never trust submitted paths or execute filenames; batch inputs restricted to approved sources | Traversal/unsafe-key and unauthorized-source tests |
| SEC-03 | MUST keep buckets private and credentials outside source control; scope object access to authorized proxy or expiring signed access | Unauthorized access/configuration tests |
| SEC-04 | MUST restrict CORS to configured origins and define endpoint-level authorization, upload/index privileges, and resource quotas before nonlocal exposure | Phase 02 auth matrix; Phase 11 access/limit tests |
| SEC-05 | MUST validate all API fields, filter operators, lengths, and numeric ranges; parameterize database access and sanitize public errors | API boundary and error-leakage tests |
| SEC-06 | MUST bound request and tool execution; rate/concurrency limits must prevent uncontrolled inference and upload resource use | Saturation, cancellation, and timeout tests |
| SEC-07 | MUST treat retrieved text and metadata as untrusted evidence; optional agents use allowlisted typed tools and may not turn evidence into instructions or unrestricted network/file access | Adversarial evidence/tool-boundary tests |
| SEC-08 | MUST define dataset rights/provenance, query-image retention/deletion, and derived artifact cleanup before ingesting nonfixture user data | Recorded decisions and documented lifecycle procedure |

Proposed JPEG/PNG/WebP support is provisional. Upload sizes, pixel/frame bounds, quotas, timeout values, and authentication mode are unresolved until reviewed against environment and exposure in Phase 02/03. Local-only development must not silently become unauthenticated public deployment.

## 4. Latency and load measurement protocol

### Core search

Use a monotonic clock at the ASGI server boundary. Start when the application receives the HTTP request scope, before body reading, validation, and upload parsing. End when the final HTTP response-body send completes. Include application queuing after receipt, decode/preprocessing, embedding, internal network calls, vector lookup, filtering, metadata hydration, serialization, and streaming completion where applicable. Exclude browser rendering, external client/server transit, and queues before the application receives the request.

This operational boundary is the project definition of server request receipt. Proxy/socket backlog, if present, needs separate instrumentation. Record its limitation in reports. Returning a timer captured inside the endpoint before serialization is not sufficient to meet NF-01; final response latency belongs in middleware logs/metrics. Name any partial response timing field accordingly.

Report text-only, image-only, and combined modes separately; aggregate only with a declared workload mix. Reference upload bytes and K/C/filter distributions must be recorded. Record cold-start and warmed steady-state measurements separately, and identify model-loading, caching, and connection warmup. Do not discard slow successful samples or hide timeout/error counts.

Client-perceived latency uses a separate client clock: request initiation through complete response receipt; include upload and network transit. Browser rendering is a separately named UI measure. Do not subtract unrelated client/server clocks to infer transit latency.

### Agent and RAG timing

For streaming output, measure request receipt to first generated token (TTFirst), request receipt to last generated token (TTLast), and request receipt to complete final response. Heartbeats, empty chunks, and tool-status events are not generated tokens. Record planner, each tool, retrieval, and generation spans with outcomes, parallelism, and deadlines. Use the same boundary on the client for separately named client token timings.

For nonstreaming responses without internal token instrumentation, report complete response latency and mark token timings unavailable; do not equate them without evidence. Failed or fallback requests are counted and labeled. The ≤ 3 s TTLast objective is scoped to a declared model/provider, hardware, output-token budget, and hop/tool budget; it is not a universal guarantee.

### Load report

Every run records: run ID/time, commit or source snapshot hash, config/seed, query and judgment versions, dataset checksum/split/size, active image count, model/processor revisions, precision/device, CPU/GPU/RAM/VRAM, OS/runtime/package versions, index metric/HNSW/search settings, filters/K/C, service topology, concurrency/offered load, warmup, duration, sample count, cache state, and resource samples.

Report P50/P90/P95 using a declared quantile method (initial proposal: nearest-rank), successful requests/second, total completed requests/second, attempted and completed counts, timeouts, error classes, and error rate. Define error rate as unsuccessful attempted requests divided by all attempted requests in the measurement window, including client-observed timeouts and disconnects; reconcile outstanding requests after a drain period. Report successful-request latency and failed-request duration separately. Preserve raw samples; quantify uncertainty/sample limitations and never claim stable tail percentiles from inadequate data.

## 5. Retrieval metric definitions

The required relevance metrics are Recall@1, Recall@5, Recall@10, Precision@10, MRR (with evaluated depth disclosed), and nDCG@10.

For query q, let Rq be the set of all judged relevant eligible corpus images and Lq the ordered, unique returned image IDs. Binary relevance is a declared threshold over graded judgments. Fixed denominator metrics pad missing returned positions with nonrelevant entries. Duplicate IDs are counted only at their first rank and flagged as a system defect.

- **Recall@K** = |Rq ∩ first K of Lq| / |Rq| for |Rq| > 0. Compute at K = 1, 5, 10. Recall@10 measures the fraction of relevant images recovered among ten results; it does not mean a 10% recall target. Example: three of twenty relevant images in the top ten gives 0.15.
- **Precision@10** = number of relevant images in the first ten positions / 10, even if fewer than ten results are returned.
- **Reciprocal rank** = 1 / rank of the first relevant result; zero if no relevant result occurs within the declared evaluated retrieval depth. MRR is its mean. Report the depth and label truncated evaluation as MRR@D; never imply unlimited-depth MRR from a Top-10 run.
- **DCG@10** = sum over ranks i = 1…10 of (2^grade_i − 1) / log2(i + 1). **nDCG@10** = DCG@10 / IDCG@10, with the ideal order derived from all eligible judgments for that query.

Report macro means per query group and overall with declared weighting. Queries with no relevant eligible images have undefined recall/IDCG; exclude them from recall/nDCG aggregation with explicit counts, and report empty-result behavior separately. Specify their treatment for precision and MRR; initial protocol excludes them from relevance aggregates and evaluates them in a separate no-answer group.

Ground truth must be available. Exhaustive judgments support corpus recall; pooled/incomplete judgments only support recall relative to the judged pool and must be labeled. Never silently treat unjudged images as established negatives. Record judgment coverage and a consistent unjudged-result policy; complete judgments for evaluated candidates where feasible. Checksum labels, annotator guidance, disagreement resolution, relevance grades, eligible corpus/filter context, and split membership.

## 6. Query groups and experiments

| Group | Required inputs/judgments | Additional measure |
| --- | --- | --- |
| G1: single-intent text | Fixed text queries, eligible image IDs and relevance grades | Language/domain breakdown |
| G2: multi-intent text | Required/optional conditions, image grades, per-condition labels | Mandatory-condition satisfaction, all-required success, unknown coverage |
| G3: image-to-image | Versioned reference bytes, relevance labels, identity policy | Report inclusion/exclusion of exact reference matches |
| G4: text + image | Reference bytes, edit/constraint text, joint relevance grades | Joint constraint satisfaction and modality ablations |
| G5: multi-hop | Relation evidence, expected intermediate entities, final relevant images | Grounded task success, hop/tool counts, fallback and unsupported-claim rates |

Constraint satisfaction uses annotated supported/violated/unknown conditions, not raw embedding scores. Report the fraction of returned images with all mandatory conditions confirmed and separately the fraction of queries with at least one such image; document denominators and unknown coverage. Multi-hop success requires correct evidence-supported relation resolution and an eligible relevant final result. A relevant result reached through a wrong or unsupported relation is not full task success.

| Experiment | Configuration | Required comparison |
| --- | --- | --- |
| E1 | CLIP + Qdrant, direct semantic search, no generation | P0 baseline, quality and latency per supported group |
| E2 | SigLIP 2 or justified replacement with its own compatible index/processor | Same corpus, splits, judgments and load; quality, language coverage, resources, latency |
| E3 | Best justified baseline + filtering/reranking/multi-intent/fusion | Ablations for each addition; quality gain versus cost; constraint satisfaction |
| E4 | E3 + optional agents/multi-hop/RAG | Same applicable queries plus G5; grounded success, tool/token timing, generation evidence, resources |

Use development data for method/parameter selection and a held-out test set for final evaluation. Prevent train/dev/test image or near-duplicate leakage where applicable. Declare nondeterminism, seeds, repeats, and confidence interval procedure. Compare applicable modalities; mark unsupported combinations as unavailable rather than inventing results. Keep end-to-end relevance distinct from ANN neighbor recall, which may be diagnosed against exact vector search.

## 7. Evidence status

At Phase 01 no dataset, labels, model execution, throughput, latency, quality scores, or resource measurements exist. All requirements are specified, not implemented. Phase 07 produces first controlled benchmark evidence; later phases must retain the P0 regression baseline.
