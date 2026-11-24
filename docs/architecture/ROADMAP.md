# Twelve-Phase Implementation Roadmap

## Hoàn thiện Phase 11 — 07/11/2026

Đã kiểm toán, sửa9 lỗi xác nhận, bổ sung QA riêng và CI quality gates. Backend244, frontend44 và66 browser cases được chọn pass;4 fault scenarios pass. Fast C1 đạt500/500 trên corpus513 ảnh; C4 có3% backpressure, Gemini RAG vượt3s/timeout được ghi rõ. [Báo cáo A–Q](../archive/PHASE11_TEST_REPORT.md), [chiến lược test](../testing/TEST_STRATEGY.md) và [các lỗi/bản sửa](../archive/BUG_FIX_REPORT.md) là trạng thái hiện hành. **READY_WITH_DOCUMENTED_LIMITATIONS; dừng sau Phase11, Phase12 chưa triển khai.** Human quality vẫn chờ. Các sections dưới là snapshot lịch sử.

## Snapshot hoàn thiện Phase 10 — 07/11/2026

Frontend Lens đã tích hợp các API Semantic/Image/Multimodal/Multi-intent/RAG/Agent; có private detail dialog, drag/drop, filters/fusion/rerank, cancellation/stale guards, dataset status và dashboard từ artifact thật. 40 frontend unit tests, 211 backend tests, 72 functional E2E và 2 performance E2E pass. Chromium/Firefox/WebKit, desktop/tablet/mobile emulation và empty backend tạm đã được kiểm chứng. [Báo cáo A–P](../archive/PHASE10_TEST_REPORT.md) ghi phạm vi và giới hạn; nhãn chất lượng do người đánh giá còn chờ. **Dừng ở Phase10; chưa triển khai Phase11 hoặc deployment Phase12.**

## Hoàn thiện Phase 09 — 06/11/2026

Đã bổ sung bộ địa danh NPS có nguồn:3 ảnh thật,4 entities,3 quan hệ và3 liên kết ảnh. Index phục vụ hiện513 ảnh, generation3; index510 ảnh cũ giữ nguyên. Workflow Anh/Việt/alias, Gemini planner và RAG thật đã được kiểm tra. Planner có trace từng attempt; prompt tools và RAG context đã rút gọn, citation provenance vẫn giữ đầy đủ trên server. Bộ kiểm tra mới đạt200 backend,21 frontend unit và24 browser full tests cùng6 ca browser nhánh cuối. Chất lượng do người đánh giá vẫn chờ; số đo latency và trạng thái target3s xem [báo cáo Phase 09](../archive/PHASE09_TEST_REPORT.md), dữ liệu/nguồn tại [PUBLIC_LANDMARK_DATASET](../research/PUBLIC_LANDMARK_DATASET.md).

## Snapshot lần triển khai Phase 09 ban đầu

Phase 09 đã có phần mềm và kiểm thử Agent optional với typed tools/plan/state, bounded execution, knowledge import, evidence aggregation, RAG tùy chọn, streaming và UI. Hạ tầng thật và retrieval trên510 ảnh đã chạy; knowledge thực chưa nhập nên quan hệ thật chỉ kiểm tra abstention. Fixture đa bước cô lập không chứng minh semantic accuracy. [Báo cáo Phase 09](../archive/PHASE09_TEST_REPORT.md) ghi số đo và gates. Phase08 human review tiếp tục chờ; Phase 10–12 chưa triển khai. Các trạng thái phase cũ ở phần sau là snapshot lịch sử.

## Lịch sử cập nhật trước Phase 09

Cập nhật06/11/2026: đã có corpus510 ảnh/500 captions; phần mềm đạt152 backend tests,13 frontend unit và16 browser cases. Human quality review chờ xác nhận theo lựa chọn của người dùng. [Báo cáo hiện hành](../archive/PHASE08_COMPLETION_REPORT.md); các số liệu05/11 bên dưới là lịch sử. Không tự chuyển Phase 09.


Cập nhật05/11/2026 — Phase 08: RAG metadata tùy chọn đã được triển khai trên SearchService hiện có, provider Gemini, typed evidence/citations và API/SSE/UI. [Nghiệm thu Phase08](../archive/PHASE08_TEST_REPORT.md) là báo cáo hiện hành; các trạng thái chưa triển khai RAG bên dưới là lịch sử. Agent/Phase 09 chưa triển khai.

Cập nhật triển khai Phase 06: multimodal late fusion, multi-intent/AND/OR và lightweight reranking đã được bổ sung trên core Phase 05. Fast path không gọi LLM hoặc tự fan-out query đơn giản. [Báo cáo Phase 06](../archive/ADVANCED_SEARCH_TEST_REPORT.md) ghi tests/số đo/giới hạn; [API hiện hành](../features/ADVANCED_SEARCH_API.md) bổ sung contracts. Các sections baseline/historical bên dưới giữ ngữ cảnh thiết kế, không phải bằng chứng triển khai mọi tính năng tương lai.

Cập nhật Phase 07: framework/annotation/benchmark/model comparison đã có; nghiệm thu chất lượng ngữ nghĩa vẫn chờ nhãn người đánh giá. Đã đo CPU/load/ablation thực và giữ nguyên CLIP đang phục vụ; chưa bắt đầu08–12. Xem [báo cáo A–M](../archive/PHASE07_TEST_REPORT.md).

Baseline: 1.1.0, 2026-11-03. Dự án được tổ chức thành 12 giai đoạn (Phase 01–12). Phase 01 đã hoàn thành; Phase 02 được yêu cầu riêng và tạo bộ thiết kế tiếng Việt. Không tự chuyển sang Phase 03. Nội dung roadmap gốc được giữ ngoài các cập nhật trạng thái/deliverables cần thiết.

## 1. Execution rules

P0 is the baseline throughout development. P1 and P2 changes require regression checks against the functioning core; they may not make a generator or agent mandatory. Each phase has a bounded scope, tangible artifacts, verification evidence, and limitations. Implementation phases cannot be completed by theoretical descriptions alone.

Snapshot trước Phase 09: foundation/indexing/core/advanced search đã có;10 ảnh mẫu indexed. Phase 07 có framework/benchmark/annotation, chưa có human qrels. Phase 08 đã triển khai RAG metadata tùy chọn với Gemini native, JSON/SSE/UI; còn mở một browser gate phụ thuộc provider, target3s và semantic quality. Phase 09–12 chưa triển khai. [Báo cáo Phase08](../archive/PHASE08_TEST_REPORT.md) ghi đúng các số đo và giới hạn. Các snapshot phase trước bên dưới giữ để đối chiếu lịch sử.

Dependency sequence: 01 → 02 → 03 → 04 → 05 → 06 → 07 → optional 08 → optional 09 → 10 → 11 → 12. Prompts 08/09 can be explicitly deferred; 10 must then integrate only supported capabilities. Evaluation design starts during 02; evaluation instrumentation begins in 05, with controlled experiments in 07. A minimal frontend scaffold arrives in 03; a usable end-to-end P0 interface is required by 10.

## 2. Phase definitions

### Phase 01 — Master Project Specification

- **Scope:** Normalize the supplied requirements and establish architecture, measurements, standards, assumptions, and phase boundaries. Documentation only.
- **Inputs/dependencies:** User's Master Project Specification; inspected workspace and applicable local instructions.
- **Tasks:** Separate P0/P1/P2; define module boundaries and fast/advanced paths; define metric protocols and traceability; record unresolved decisions and twelve gates.
- **Deliverables:** `docs/architecture/MASTER_SPEC.md`, `docs/architecture/REQUIREMENTS.md`, `docs/architecture/ROADMAP.md`, `docs/architecture/ENGINEERING_STANDARDS.md`, `docs/architecture/DECISIONS.md`.
- **Acceptance:** All five files exist, cross-reference consistently, preserve all requested capability areas, distinguish targets from observations, and state what remains unimplemented. No backend/frontend/infrastructure implementation is introduced.
- **Verification:** Inspect workspace; check document structure, required endpoints/priorities/metrics, relative links, and roadmap coverage; report Git limitations and exact checks honestly.
- **Known limitations:** No executable system, dataset, labels, resolved capacity, package compatibility evidence, or benchmark results. Open decisions are inputs to subsequent design.

### Phase 02 — PRD, SAD, Architecture and Database Design

- **Scope:** Turn the baseline into detailed product and system design without deploying infrastructure or implementing services.
- **Inputs/dependencies:** Accepted Phase 01 documents and decision register. Obtain deployment exposure, language/domain expectations, and provisional dataset/hardware information where available.
- **Tasks:** Define actors and use cases; design API payloads/media types/errors/auth/pagination; logical ER model and indexes; ingestion/job state transitions and reconciliation; module interfaces; threat/resource model; evaluation data/annotation plan; choose or mark decision deadlines.
- **Deliverables:** `docs/architecture/PRD.md`, `docs/architecture/SAD.md`, `docs/architecture/SYSTEM_ARCHITECTURE.md`, `docs/architecture/DATABASE_DESIGN.md`, `docs/architecture/API_SPECIFICATION.md`, `docs/research/PERFORMANCE_DESIGN.md`, `docs/architecture/DESIGN_REVIEW.md`, 11 Mermaid sources và 8 ADRs; cập nhật decision register và traceability. Hai tên từng đề xuất API_CONTRACTS/EVALUATION_PLAN được thay bởi tên yêu cầu chính thức API_SPECIFICATION/PERFORMANCE_DESIGN, không tạo hai nguồn contract trùng nhau.
- **Acceptance:** Every FR/NF/SEC ID maps to a design component and acceptance method. Contracts cover all eight endpoints, all input modes, disabled features, and failure states. Image/object/vector identity, uniqueness, job claiming/retries, active-index state, and repair rules are explicit. Security policies and unresolved blockers are visible.
- **Verification:** Walk through text/image/multimodal requests, concurrent duplicates, partial failures, stale vectors, unavailable services, and disabled agents on paper; review ER and contract consistency with requirements.
- **Known limitations:** A design does not validate runtime performance or model quality. Capacity-dependent choices may remain provisional with deadlines; exposure/authorization and artifact-consistency design must be clear before implementation.

### Phase 03 — Repository Setup, Docker Infrastructure, Backend and Frontend Initialization

- **Scope:** Establish reproducible development scaffolding and service connectivity; no complete ingestion or retrieval yet.
- **Inputs/dependencies:** Phase 02 architecture/contracts, chosen local versions, writable Git project location, credential templates, and environment/resource requirements.
- **Tasks:** Establish repository structure and dependency locks; initialize typed API and frontend; configure PostgreSQL/Qdrant/MinIO using Compose; set up migrations, health/readiness, configuration validation, restricted CORS, logs, lint/type/test commands, and developer instructions.
- **Deliverables:** Source scaffolds, lockfiles, container/build definitions, migrations baseline, environment example without secrets, documented start/check commands, CI configuration where available.
- **Acceptance:** Clean setup starts required services; frontend reaches backend; dependency failures are reflected in readiness; credentials are absent from tracked content; exact runtime and service versions are recorded. Git setup must use a writable project location, preserving managed metadata.
- **Verification:** Compose configuration check and service startup; backend health/connectivity and migration smoke checks; frontend strict type/build check; available baseline tests and secret/config review.
- **Known limitations:** Running services are not semantic search. Model loading, image indexing, retrieval quality, and capacity claims remain pending.

### Phase 04 — Image Ingestion and Vector Indexing Pipeline

- **Scope:** Implement durable real-image ingestion and the minimum versioned image-embedding adapter needed for indexing. Covers FR-04–08 and ingestion security.
- **Inputs/dependencies:** Running Phase 03 services; approved image fixtures/provenance; selected pinned CLIP checkpoint and processor; format/resource limits; Phase 02 lifecycle contracts.
- **Tasks:** Decode/validate images, hash bytes, enforce unique identity, preprocess/embed, store private objects/metadata/vector points, support batch jobs and per-item status, leases/retries/repair, and separate index versions. Captioning remains optional.
- **Deliverables:** Worker and adapters, schema migrations, upload/job endpoints, ingestion/batch commands, model manifest, job/repair documentation, automated ingestion tests.
- **Acceptance:** Valid images become ready with consistent IDs and correct finite vectors; invalid images cannot become searchable; concurrent duplicates converge; crash/partial-write recovery works; retries are bounded; replacement indexes remain isolated and inspectable.
- **Verification:** Integrate against actual storage services and a real pinned model; test corrupt/unsupported/oversized images, duplicate races, process interruption, dependency outages, model mismatch, and replay/reconciliation. Verify image/object/vector records directly.
- **Known limitations:** Ingestion proves indexing, not retrieval quality. Hash deduplication covers identical bytes only. Dataset licensing, query-image retention, and exact limits must already be settled for the data used.

### Phase 05 — Core Semantic Search Engine

- **Scope:** Deliver text-to-image and image-to-image P0 search with compatible encoders, Top-K, metadata hydration, deduplication, errors, and instrumentation. Covers FR-01–03, FR-09, FR-12.
- **Inputs/dependencies:** Phase 04 ready images/active index/model manifest; core API contracts; labeled smoke queries and reference images; resource/time limits.
- **Tasks:** Implement paired query encoders, version checks, Qdrant cosine candidates, stable ranking, eligibility checks, result schemas, request timing, and no-result/dependency-error handling. Keep agent modules absent from required dependencies.
- **Deliverables:** Search service and core endpoint, embedding/retrieval documentation, timing middleware, small real-model integration suite, runnable API examples.
- **Acceptance:** Text and image-only queries return at most K unique ready images, K defaults to 10, invalid/mismatched inputs fail explicitly, genuine empty results remain distinguishable from failures, and complete server latency is recorded. Core works with all P2 features disabled.
- **Verification:** Real-service/model search fixtures, known-neighbor and metadata identity checks, K/bounds/tie tests, incompatible-index and dependency failures, stage-versus-complete-response timing checks. Small labeled checks establish smoke correctness, not final quality claims.
- **Known limitations:** No promise of compositional edits, strict semantic constraints, production throughput, or target latency attainment. Initial observed timing may be exploratory until Phase 07.

### Phase 06 — Multimodal and Multi-intent Retrieval

- **Scope:** Add P1 combined search, lightweight intent processing, metadata filters, candidate configuration, fusion, and optional reranking. Covers FR-13–18 and filter UI contracts.
- **Inputs/dependencies:** Functioning Phase 05 baseline and regression fixtures; G2/G4 development queries and per-constraint judgments; chosen candidate/resource bounds.
- **Tasks:** Implement combined-input endpoint and deterministic routing/decomposition for supported query patterns; required/optional conditions; structured filter validation; late/normalized-score/rank-fusion experiments; versioned reranking; hybrid decision based on need/evidence.
- **Deliverables:** Multimodal and multi-intent modules, filter contracts, fusion/reranking manifests, ablation configurations, tests, documented constraint semantics and unsupported patterns.
- **Acceptance:** Combined inputs are both used; mandatory metadata filters are preserved; semantic unknowns are disclosed; multi-intent alone never invokes an agent; candidate and final counts obey bounds; P0 regression cases pass. Hybrid retrieval is either justified and tested or explicitly deferred.
- **Verification:** Real development-set runs and modality ablations; filter/no-match/missing-field cases; conflicting conditions; negation/edit limitations; deterministic router cases; added-latency measurement with and without reranking.
- **Known limitations:** Embeddings/fusion do not guarantee all visual constraints or negation. Lightweight decomposition covers documented patterns; complex relational reasoning remains P2. Held-out results are not used to select methods.

### Phase 07 — Evaluation, Benchmarking and Latency Optimization

- **Scope:** Produce reproducible E1–E3 evidence and improve measured bottlenecks without sacrificing quality. Covers FR-11–12, NF-01/NF-08, and the measurement plan.
- **Inputs/dependencies:** Phase 05/06 implementations; fixed eligible corpus/query/judgment versions; approved hardware, workload, concurrency, cache policy, sample plan, and quality gates; held-out split isolated from tuning.
- **Tasks:** Implement independently verified retrieval metrics, API load harness, resource collection, raw result retention, query-group reports, model comparison with separate compatible indexes, ANN diagnostics, and bottleneck-led tuning/ablations.
- **Deliverables:** `evaluation/` tooling/manifests, unit tests for metrics, E1/E2/E3 reports with actual outputs, latency/resource/load reports, reproduction commands, updated decisions for model/ranking/index selection.
- **Acceptance:** Required metrics have correct denominators, relevance coverage and limitations are disclosed, P50/P90/P95/throughput/error rates are reproducible, target attainment is reported truthfully, and model comparisons use controlled inputs. Any selected optimization preserves agreed quality gates; unmet objectives retain an action/deviation record.
- **Verification:** Hand-computed metric fixtures including missing results, graded relevance, zero-relevant queries and duplicates; replay saved rankings; controlled repeated load runs; cold/warm and modality breakdown; compare real baseline and tuned configurations.
- **Known limitations:** Findings apply only to the recorded environment/corpus/workload. Missing G5 agent capability is marked unavailable. An E2 model may be rejected for resources, license, or quality, with evidence rather than fabricated scores.

### Phase 08 — Retrieval-Augmented Generation

- **Scope:** Optional P2 evidence-grounded explanations, separated from ranking. Covers FR-19–20 and NF-02.
- **Inputs/dependencies:** Stable retrieved-image/evidence contracts and P0/P1 regression baseline; approved generation model/provider, data policy, output budget, and resource configuration. Explicitly defer if P0 reliability/resources are insufficient.
- **Tasks:** Build evidence assembly from captions/tags/metadata and validated visual analysis when available; generate cited explanations; validate cited IDs/claims; flag insufficient evidence; configure feature flags, deadlines, optional streaming, and failure fallback.
- **Deliverables:** RAG module and contract, evidence/citation schemas, prompt/model versions, grounding tests, token/complete timing instrumentation, explanation evaluation report.
- **Acceptance:** Explanations cite retrieved image IDs; no unsupported image properties are asserted; generation failure leaves retrieval usable; token timing is measured or explicitly unavailable; disabled mode is clear.
- **Verification:** Supported/unsupported claim fixtures, missing/contradictory evidence, fabricated citation attempts, malicious retrieved text, provider outages/timeouts, latency and P0 independence checks.
- **Known limitations:** Metadata/captions may be incomplete or incorrect. Explanations are not proof of visual truth, and the 3 s objective may be missed depending on model and output budget. No mandatory agent orchestration yet.

### Phase 09 — AI Agent and Multi-hop Search

- **Scope:** Optional bounded relational search and E4 evaluation. Covers FR-21–22, G5, and agent safety/timing requirements.
- **Inputs/dependencies:** Stable direct retrieval and optional RAG interface or explicit RAG deferral; curated PostgreSQL entity relations with provenance; annotated G5 tasks; total deadline and hop/tool/token limits.
- **Tasks:** Implement allowlisted typed tools, deterministic/optional planner routing, bounded state machine, evidence validation, trace collection, relation lookup, fallback policy, and task-success evaluation. Use PostgreSQL before considering graphs.
- **Deliverables:** Agent module and endpoint, entity schema/data provenance, tool contracts, traces, budgets, multi-hop tests, E4/G5 report and P0 regression evidence.
- **Acceptance:** Correct known relations lead to eligible final results with evidence; unknown relations remain unknown; loops and runaway calls are stopped; fallback is disclosed and fits the same total deadline; direct search remains independent. Multi-intent inputs do not automatically enter the agent path.
- **Verification:** Known/unknown/ambiguous relations, bad tool IDs, cyclic plans, tool outages, timeout/budget exhaustion, injected instructions, trace/evidence integrity, grounded task success and TTFirst/TTLast/tool timings.
- **Known limitations:** Success is bounded by curated relation coverage and evidence quality. Direct fallback is not multi-hop success. Generic web research and graph infrastructure are excluded unless separately justified.

### Phase 10 — Frontend and End-to-end Integration

- **Scope:** Deliver the responsive usable P0 interface and supported P1/P2 controls. Covers FR-10/23; optional phases may be deferred without blocking core UI.
- **Inputs/dependencies:** Versioned APIs, image-access/auth policy, capability states, working core services, accepted designs, real test images, supported browser targets.
- **Tasks:** Text/image inputs, preview, mode and K controls, filters, loading/empty/error states, results/details/metadata; optional cited explanation panel; cancellation/stale-response handling; client timing separate from server metrics.
- **Deliverables:** Integrated web app, typed client, accessible responsive views, browser/end-to-end tests and local-run instructions.
- **Acceptance:** Desktop/mobile text and image-only workflows operate on actual API data; previews and details work; clear failures/empty states; unsupported modes are not presented as usable; credentials stay server-side. Combined/filter/explanation flows operate only when supported.
- **Verification:** Type/build checks, browser tests across the declared matrix, keyboard and responsive layout checks, image preview cleanup, interrupted/stale request handling, unauthorized media access, API failure and disabled-feature scenarios.
- **Known limitations:** Native applications excluded. Browser rendering/client transit is reported separately from core server latency. Semantic ranking limitations remain visible.

### Phase 11 — Testing, Debugging and Reliability Improvement

- **Scope:** Close integration, reliability, security, and regression gaps across delivered capabilities.
- **Inputs/dependencies:** Integrated Phase 10 system, automated suites, benchmark manifests, issue/deviation register, expected deployment profile.
- **Tasks:** Resolve functional bugs; validate auth/resource boundaries; fault-inject dependency and worker failures; migration/recovery checks; verify duplicate races and stale indexes; run security and quality/performance regressions; update runbooks and docs.
- **Deliverables:** Fixes, meaningful expanded tests, final test matrix/results, failure/recovery evidence, updated operational instructions and known-risk register.
- **Acceptance:** Required P0 behavior and safety checks pass; cross-store inconsistencies are repairable; unsupported capabilities are explicit; no critical unresolved functional/security defects for the intended deployment. Missed performance/quality objectives are documented with approved scope/deviation decisions, never relabeled as passes.
- **Verification:** Clean-stack end-to-end tests, repeated job replay/crash scenarios, actual dependency outages, migration/rollback drills, resource-limit tests, controlled regression benchmarks, and secret/access review.
- **Known limitations:** Tests cannot establish unlimited scale or zero defects. Optional features failing their gates must be repaired, disabled, or explicitly deferred rather than compromise P0.

### Phase 12 — Deployment, Documentation and Final Research Evaluation

**Nghiệm thu08/11/2026:** artifacts triển khai và kiểm chứng local đã có; trạng thái `READY_WITH_LIMITATIONS`. Xem [FINAL_PROJECT_REPORT A–T](../FINAL_PROJECT_REPORT.md), [FINAL_HANDOVER](../FINAL_HANDOVER.md) và [TESTING_AND_VERIFICATION](../operations/TESTING_AND_VERIFICATION.md). Empty dataset và import tổng hợp/CLIP thật, persistent backup/restore/update/rollback được xác minh riêng; public environment và nghiên cứu có human labels vẫn là điều kiện chưa đủ. Không tự triển khai phase mới sau12.

- **Scope:** Reproducible final delivery for the agreed environment, operational documentation, and research report.
- **Inputs/dependencies:** Phase 11 acceptance evidence; approved deployment target, resource/cost/exposure policy, secret handling, dataset/model licenses, backup/retention decisions, and frozen final evaluation configuration.
- **Tasks:** Package pinned release artifacts; document deploy/upgrade/rollback/backup/restore and reindexing; run clean-environment reproduction; finalize applicable E1–E4 comparisons with ablations/limitations; record source/model/data/experiment versions.
- **Deliverables:** Deployment bundle/configuration, setup/operator/user guides, API documentation, research evaluation and artifact manifest, final known-limitations report and release checklist.
- **Acceptance:** Another operator can reproduce the functional system and evaluation using declared resources and authorized data; all reported results trace to retained evidence; deployment secrets are external; backup/restore and core health are verified; optional/deferred features and unmet targets are explicit.
- **Verification:** Clean-host/isolated-environment setup, service and browser smoke checks, representative evaluation replay, backup/restore/rollback drill, and complete artifact/license/config review. Execute external publication only within authorization for that phase.
- **Known limitations:** Conclusions remain scoped to evaluated data/hardware/workload; absence of suitable deployment resources or data rights must be reported as an unmet dependency, not hidden behind theoretical instructions.

## 3. Cross-phase acceptance record

At every handoff record: authorized scope and requirement IDs; artifacts created/modified; integration status; exact executed checks and outcomes; observed versus targeted metrics; open decisions and blockers; reproduction commands; version-control readiness; and next-phase inputs. Do not claim a phase is complete while its required implementation or verification remains undone.

Phase 03 đã được yêu cầu riêng và nghiệm thu foundation; xem [PHASE03_REPORT](../archive/PHASE03_REPORT.md) cho kết quả thực thi. Phase 04 đã được yêu cầu và triển khai với corpus fixture có rights/provenance, pinned CLIP và CPU profile; Phase 05 đã được yêu cầu và triển khai; không tự chuyển sang Phase 06.
