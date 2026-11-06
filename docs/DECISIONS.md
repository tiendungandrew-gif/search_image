# Architecture Decisions, Assumptions, and Open Questions

Baseline: 1.0.0, 2026-11-03. This is a decision register, not an implementation-status report. No runtime selection below has been benchmarked in this workspace.

## 1. Status meanings

- **Adopted:** Architectural constraint established by the supplied specification or this normalized baseline; change requires recorded rationale and affected-document updates.
- **Provisional:** Proposed implementation default; confirm against constraints and evidence in its assigned phase.
- **Open:** Missing information or a choice that has not been made. A deadline identifies when it becomes a blocker.
- **Deferred:** Outside the current phase or conditional scope; not silently counted as implemented.

Changes record date, decision owner/reviewer, rationale/evidence, alternatives, affected requirements, and migration/reversal implications. Engineering proposes choices; the project owner confirms product, dataset rights, deployment exposure, and research acceptance thresholds. Detailed ADR files may be added in later phases when complexity warrants them.

## 2. Quyết định baseline Prompt 01 — namespace P01-ADR

| ID | Decision | Rationale, alternatives, consequences |
| --- | --- | --- |
| P01-ADR-001 | Modular monolith with a same-codebase background worker | Maintains clear boundaries without premature microservices. A worker process isolates ingestion from request execution; service extraction requires evidence of need. Affects FR-07, NF-06. |
| P01-ADR-002 | Semantic retrieval is independent of agents and generation | P0 remains operational without an LLM. Agents depend on retrieval interfaces, never the reverse. Reject an LLM planner on every request. Affects NF-09, FR-14/20/21. |
| P01-ADR-003 | Paired image/text encoder with immutable embedding-space manifests and isolated index versions | Matching dimensions alone do not guarantee a shared space. Reindexing is required for incompatible model/preprocessing changes. Reject cross-model queries against old vectors. Affects FR-01/02/08. |
| P01-ADR-004 | PostgreSQL is authoritative for identity, lifecycle, metadata, jobs, and initial entity relations | Transactions/uniqueness protect local invariants; Qdrant payloads are retrieval projections. A graph database is deferred. Stale payloads require authoritative eligibility checks. Affects FR-05–08/16/22. |
| P01-ADR-005 | Cross-store consistency uses durable progress, idempotency, retries, and reconciliation | No distributed transaction is assumed across PostgreSQL, Qdrant, and MinIO. Only verified ready active-version images are returned. Reject optimistic success after partial writes. Affects NF-05. |
| P01-ADR-006 | Exact duplicate identity uses original-byte SHA-256 and database uniqueness | Handles repeated files and concurrency. Per-image/model/index uniqueness supports reindexing. Perceptual/near-duplicate detection remains optional and must not be implied by exact hashing. Affects FR-05/08. |
| P01-ADR-007 | Stable UUID links metadata, vector point, and owned object keys | Avoids unrelated IDs and unsafe user filenames. Object/version derivatives retain the parent identity. Detailed schema in Prompt 02. Affects FR-06, SEC-02. |
| P01-ADR-008 | Cosine baseline with explicit normalization/validation and versioned Qdrant configuration | Provides an explicit similarity contract. HNSW/search parameters require empirical selection; similarity is not a relevance probability. Affects NF-11. |
| P01-ADR-009 | Multi-intent differs from multi-hop | Several visual conditions do not require an agent. Structured predicates can be hard filters; semantic conditions may be unknown. Relational queries need evidence and bounded execution. Affects FR-14–16/21. |
| P01-ADR-010 | Separate candidate retrieval, filtering/fusion/reranking, and final Top-K | Allows ablations and replacement without conflating scores. C ≥ K, with bounded configuration; no automatic weakening of mandatory filters. Affects FR-03/13/16/17. |
| P01-ADR-011 | API latency is the full ASGI application request/response interval | Includes body parsing and final serialization/send, excludes browser/external transit. Endpoint-internal timers are insufficient; proxy/socket backlog is a separately documented boundary. Affects FR-12, NF-01/02. |
| P01-ADR-012 | Evaluate with fixed actual judgments and versioned experiments; keep facts separate from targets | No numeric quality threshold, dataset capacity, or measured latency is invented. Use dev/test separation, group breakdown, and retained raw evidence. Affects FR-11, NF-07/08. |
| P01-ADR-013 | Private object storage and content-validated bounded uploads | Reduces unsafe naming/access and resource abuse. Public buckets and extension-only validation are rejected. Auth/exposure and exact limits must be designed before real deployment. Affects SEC-01–06. |
| P01-ADR-014 | Optional agents use typed allowlisted tools and a shared total request deadline | Bound hops/calls/tokens and remaining-time fallback; trace evidence and unknown relations. Reject unbounded reasoning loops and unrestricted shell/network tools. Affects FR-21/22, SEC-07. |
| P01-ADR-015 | Explanations cannot substitute for retrieval evidence | Cite specific retrieved image IDs; distinguish metadata evidence from confirmed visual facts. No required automatic captioning, generation, or agent for baseline search. Affects FR-19/20. |

Technical reference for P01-ADR-008: [Qdrant collection configuration](https://qdrant.tech/documentation/manage-data/collections/). Technical reference for P01-ADR-003: [Transformers CLIP](https://huggingface.co/docs/transformers/model_doc/clip) and [Transformers SigLIP 2](https://huggingface.co/docs/transformers/model_doc/siglip2). These references inform compatibility constraints; they do not establish performance or package pins for this project.

## 3. Provisional implementation choices

| ID | Proposed choice | Justification / confirmation needed | Confirm by |
| --- | --- | --- | --- |
| P-01 | Recommended stack from the master spec: React/TypeScript/Vite/Tailwind, Python/FastAPI/Pydantic, SQLAlchemy/Alembic, PostgreSQL/Qdrant/MinIO, PyTorch/Transformers | Follows requested ecosystem. Exact versions, local compatibility, licenses, and resource fit require validation; no floating production versions | 03 |
| P-02 | PostgreSQL-backed durable job records and worker claiming/leases; no extra broker initially | Keeps infrastructure small; robust claiming, recovery, backoff, and reconciliation still need implementation. Adopt another queue only if workload/operational evidence warrants it | 02 design, 04 validation |
| P-03 | CLIP baseline checkpoint selected for E1; SigLIP 2 candidate for E2 | No exact checkpoint/dimension has been chosen. Confirm target language/domain, model revision/license, preprocessing and compute budget before indexing | 04 baseline; 07 comparison |
| P-04 | Reciprocal rank fusion as first combined-input candidate; compare late and normalized-score fusion | Avoids assuming raw score calibration or embedding addition semantics. Weights, constants, candidate depth and method chosen using development evidence | 06 |
| P-05 | JPEG, PNG, WebP initial format allowlist; reject unsupported/multiframe inputs unless explicitly supported | Small predictable initial surface; validate decoder/resource handling and determine metadata stripping/frame policy | 02–04 |
| P-06 | Lightweight custom orchestration before LangGraph | Bounded tools and state machine may suffice. Adopt framework only if it improves traceability/reliability without unnecessary runtime overhead | 09 |
| P-07 | Nearest-rank quantile estimator for saved latency samples | Reproducible simple reporting; align load-tool outputs or explicitly document estimator differences | 07 |

Top-K default 10 giữ nguyên yêu cầu. Prompt 02 đã đề xuất dev defaults cho K/C, uploads và timeouts tại PERFORMANCE_DESIGN.md; các giá trị chưa benchmark. Dimension theo checkpoint manifest; HNSW vẫn cần pin/tune ở phase triển khai.

## 4. Unclear assumptions and unresolved decisions

The project owner supplies product/research constraints; engineering records a concrete choice and verifies feasibility. “Open” does not block documentation, but dependent implementation/evaluation cannot silently assume an answer.

| ID | Question / information needed | Current treatment and impact | Resolution deadline |
| --- | --- | --- | --- |
| O-01 | Which dataset(s), domains, image count, growth, licensing, and redistribution rights? | No scale or rights assumed. Use licensed/generated local fixtures only until approved; define corpus manifest and provenance | Dataset plan in 02; before nonfixture ingestion in 04 |
| O-02 | CPU/GPU/VRAM/RAM/disk, deployment topology, and available resources? | No hardware or capacity claim. Model fit, latency, batch sizes, and service placement remain unverified | Environment in 03; fixed benchmark environment before 07 |
| O-03 | Supported query languages, especially English/Vietnamese, domain vocabulary, and multilingual expectations? | Vietnamese support is not inferred from the example location or local timezone. Language-specific quality must be measured; may affect E2 candidate | Product scope in 02; checkpoint choice before 04 |
| O-04 | Expected concurrency, request rate, modality mix, K distribution, uptime and growth? | No arbitrary throughput SLO. Define an initial workload plus stress range; report saturation and tail behavior | Provisional envelope in 02; workload frozen before 07 |
| O-05 | Authentication, users/roles, tenancy, and local versus public deployment exposure? | No implicit public anonymous write access. Define endpoint/media access matrix and quotas; tenancy affects duplicate scope and authorization | 02; enforce before exposure |
| O-06 | Exact upload bytes/pixels/frames, text length/token policy, inference queue/concurrency, batch size, K/C and timeout/retry limits? | Values pending resource review. Bounds must be explicit and tests must cover them; targets are not request timeouts | Design in 02, configure in 03/04; retrieval bounds in 05 |
| O-07 | Relevance grading, annotators, eligible corpus, judgment completeness, splits, and numeric quality gates? | Define annotation guide, binary threshold, disagreements, incomplete-label policy, query-group sizes, dev/test leakage controls. No fabricated quality target | Plan in 02; frozen judgments/gates before 07 tuning/test |
| O-08 | Mandatory semantic constraint vocabulary, decomposition patterns, negation, and conflicting constraint behavior? | Lightweight supported patterns first; classify unknown rather than guarantee visual satisfaction. Define no-match behavior and per-condition labels | 02 contracts; 06 implementation |
| O-09 | Query-image retention, indexed-image deletion, EXIF/privacy policy, and data ownership? | Query input is not automatically added to corpus. Define retention/cleanup for originals, previews, vectors, logs, jobs, and backups | 02; before real user data in 04/05 |
| O-10 | Search media transport: multipart, uploaded reference ID, or both? | Preserve image-only P0 and combined P1 either way. Detail JSON fields, image lifetime, upload cost, and error semantics; do not fetch arbitrary user URLs | 02 contracts |
| O-11 | Authenticated media proxy versus expiring signed object access? | Both must preserve private storage and authorization; choose expiry, caching, browser access, and stale-link handling | 02; integrate in 10 |
| O-12 | Metadata schema, required fields, trusted source, filter semantics, and missing values? | Dimensions/hash/format/provenance/lifecycle needed; tags/captions may be absent. Define structured predicates versus semantic preferences | 02; extend in 06 |
| O-13 | Model artifacts and license pins, image resolution/truncation, precision, dimension, index/HNSW/search parameters? | Derive from chosen checkpoint and verify at runtime. Different revisions must not share an incompatible index. Tune parameters on development data | Baseline manifest in 04; comparison/tuning in 07 |
| O-14 | Which captions/visual-analysis source and evidence quality are available for RAG? | Optional metadata-based explanations can be limited; do not invent captions or visible properties | Before 08 |
| O-15 | Which generation/planning model/provider, local/network access, streaming support, output budget and data egress policy? | RAG/agent remain optional and off for core operation. TTLast feasibility unknown until model/hardware/budget fixed | Before 08/09 |
| O-16 | Entity relation coverage, sources, ambiguity handling, and evaluation task success criteria? | Curated PostgreSQL facts with provenance first; unknown entities/relations are explicit; no assumed unrestricted web tool | Before 09 |
| O-17 | Agent hop/call/token/time budgets and direct fallback consent/default? | Must bound one shared end-to-end deadline and disclose executed mode. Fallback may omit relational reasoning and cannot claim grounded task success | Contracts in 02; values and tests before 09 |
| O-18 | Backup/restore targets, retention, deployment target, certificates, storage durability, and operating budget? | Local Compose is a development baseline, not proof of production readiness. Recovery and release scope depend on chosen environment | Initial deployment assumptions in 02; finalize before 12 |
| O-19 | Browser/accessibility support matrix and basic UI acceptance expectations? | Responsive desktop/mobile web required; choose versions and test matrix without adding native apps | Product design in 02; finalize before 10 |
| O-20 | Writable project Git location and remote/CI availability? | Observed workspace has no valid Git repository; managed `.git` is read-only. Prompt 01 files are reviewable but uncommitted; no remote access assumed | Before repository initialization in 03 |

## 5. Deferred or conditional additions

Graph databases, broker/cache infrastructure, custom model training, automatic captioning, cross-encoder reranking, hybrid lexical search, native apps, and external entity lookup are not required to establish Prompt 01 or the basic P0 engine. Some are optional later candidates. Adding one requires a requirement/experiment mapping, resource cost, license/data review where relevant, and evidence that simpler choices are inadequate.

No decision in this register silently removes a mandatory P0 feature. Deferring P2 is permitted if disclosed; image-only retrieval, ingestion durability, evaluation, metadata, and a usable web interface remain required.

## 6. Current evidence and readiness

Observed on 2026-11-03: the user supplied the master specification; the workspace contained no project files or applicable `AGENTS.md` content; Git reported that the directory is not a repository. Prompt 01 adds only the five requested documentation files. No installed-service, package, model, data, or benchmark capability has been asserted.

Snapshot trên mô tả kết thúc Prompt 01. Prompt 02 đã được yêu cầu và tạo bộ thiết kế, ADRs và review report; Prompt 03 chưa bắt đầu. Dataset/hardware và quality thresholds vẫn chưa có dữ liệu xác nhận.


## 7. ADR chính thức Prompt 02

Ngày cập nhật: 2026-11-03. Tám ADR dưới dùng numbering người dùng yêu cầu. Mười lăm quyết định gốc được giữ nguyên nội dung với prefix `P01-ADR-` để tránh tái sử dụng cùng ID cho hai quyết định khác nhau; tham chiếu cũ ADR-nnn của Prompt 01 được hiểu là P01-ADR-nnn.

| ADR | Nội dung | Liên kết | Quyết định baseline liên quan |
| --- | --- | --- | --- |
| ADR-001 | Modular Monolith vs Microservices | [ADR-001](adr/ADR-001.md) | P01-ADR-001 |
| ADR-002 | Qdrant Vector Database | [ADR-002](adr/ADR-002.md) | P01-ADR-003/008/010 |
| ADR-003 | CLIP initial baseline | [ADR-003](adr/ADR-003.md) | P01-ADR-003, P-03 |
| ADR-004 | Offline indexing riêng online search | [ADR-004](adr/ADR-004.md) | P01-ADR-001/005/006, P-02 |
| ADR-005 | Fast vs Agentic Search | [ADR-005](adr/ADR-005.md) | P01-ADR-002/009/014/015 |
| ADR-006 | PostgreSQL + Qdrant + MinIO | [ADR-006](adr/ADR-006.md) | P01-ADR-004/005/006/007/013 |
| ADR-007 | Multimodal fusion | [ADR-007](adr/ADR-007.md) | P01-ADR-009/010, P-04 |
| ADR-008 | Latency measurement | [ADR-008](adr/ADR-008.md) | P01-ADR-011/012 |

## 8. Các lựa chọn đã làm rõ ở Prompt 02

Các dòng Open ở phần baseline là lịch sử. Bảng này ghi resolution mới; những phần chưa được xác nhận vẫn là assumptions, không được suy diễn thành sự thật môi trường.

| Câu hỏi | Resolution thiết kế / phần còn mở |
| --- | --- |
| O-01 | Dataset registry + rights manifest + frozen evaluation membership đã thiết kế; tên/quy mô/quyền dataset thật còn mở trước nonfixture ingestion |
| O-02/O-04 | Linux local private topology và workload matrix đã thiết kế; chưa biết hardware/load/corpus; pin môi trường trước benchmark |
| O-03 | Tài liệu mới bằng tiếng Việt; chưa claim model hỗ trợ tiếng Việt. Chốt query languages trước checkpoint selection |
| O-05 | Single-tenant local MVP, opaque Bearer scopes cấu hình; public auth/user management/multi-tenancy ngoài MVP, phải chốt trước exposure |
| O-06 | PERFORMANCE_DESIGN định nghĩa dev caps/deadlines/retries khởi đầu và override policy; xác nhận hardware/resource fit ở Prompt 03–07 |
| O-07 | Grading0…3, binary threshold2, unjudged/zero-relevant policy và splits/annotation workflow đã đề xuất; dataset/annotators/numeric quality gates còn mở trước tuning |
| O-08 | AND/OR tri-state, required/optional, strict vs best-effort, grammar caps và missing-field policy đã thiết kế; verifier coverage cần implementation/evaluation |
| O-09 | Query file không tự index, cleanup ngay request end; history off mặc định; deletion tombstone và multi-store cleanup đã thiết kế. Rights/privacy/backup retention phải được owner chốt trước dữ liệu thật |
| O-10 | JSON cho text/existing image_id; multipart options JSON + image cho file. Không arbitrary URL/base64/path |
| O-11 | Chọn authenticated content proxy, private/no-store, browser fetch Authorization rồi blob URL; thêm GET content supporting endpoint |
| O-12 | Typed metadata/tag/entity tables và filter allowlist/missing-value semantics tại DATABASE_DESIGN/API_SPECIFICATION |
| O-13 | CLIP family E1, d từ pinned runtime manifest; exact checkpoint/revisions/precision/HNSW pending theo phase |
| O-14/O-15 | RAG/provider off mặc định; synchronous JSON, token hooks nếu có; source evidence/provider/data egress phải chốt trước Prompt 08 |
| O-16 | PostgreSQL facts/provenance, typed tools và unknown/ambiguous relation policy; chưa có entity dataset thật |
| O-17 | Agent caps3 hops/6 calls/512 tokens/5s total đề xuất; fallback false mặc định, explicit disclosure, cùng deadline; seed lookup không tính relation hop |
| O-18 | Compose local design, private ports và persistent volumes; public TLS/cost/RTO/RPO/backup retention vẫn mở trước deployment |
| O-19 | Web desktop/mobile, keyboard flow và capability states; browser version matrix chốt ở Prompt 10, không native apps |
| O-20 | Git ở workspace vẫn không hợp lệ; không sửa managed .git. Prompt 03 cần writable project location hoặc dùng source snapshot hashes đến khi có Git |

P-02 được chọn cho MVP; P-04 là implementation candidate có dev constants; P-05 chọn JPEG/PNG/WebP một frame; P-06 lightweight workflow; P-07 nearest-rank cho raw sample reports. Chúng không xác nhận service/package đã chạy.

## 9. Dependencies và readiness

[DESIGN_REVIEW](DESIGN_REVIEW.md) ghi traceability, validation thực tế, giới hạn và readiness Prompt 03. Tài liệu Prompt 01 được giữ bản gốc, chỉ cập nhật phần cần cho consistency. Các tài liệu mới Prompt 02 viết tiếng Việt; English technical identifiers được giữ để triển khai. Không có app code, model download, containers hoặc benchmark. Không tự chuyển phase.

## 10. Quyết định implementation Prompt 03

Ngày2026-11-03, trạng thái source foundation, chưa có semantic engine. [PHASE03_REPORT](PHASE03_REPORT.md) ghi execution evidence.

| ID | Quyết định / rationale / hệ quả |
| --- | --- |
| P03-001 | Root hiện tại là project root, không chuyển baseline docs sang nested project hoặc sửa managed .git. Không có Git history hợp lệ để commit; dùng source snapshot hash cho evidence và chờ writable checkout |
| P03-002 | Dùng FastAPI application factory + lifespan, async SQLAlchemy/psycopg và AsyncQdrantClient; MinIO SDK sync chạy trong executor có bounded slots/HTTP timeouts. Không in cấu hình hoặc SDK exceptions raw |
| P03-003 | Migration đầu tạo sáu bảng, gồm bốn priority tables và search_indexes/dataset_sources để giữ approved FK. Bảng còn lại theo phase, không seed models/vectors. Migration là snapshot độc lập, có downgrade và real PG metadata comparison test |
| P03-004 | Thêm /health/live, /health/ready và /system/info theo Prompt03; giữ /health?check cũ. Infrastructure ready không đồng nghĩa search-ready. Không đăng ký unimplemented search/image/job endpoints; standardized404 tới khi phase tương ứng có handler |
| P03-005 | Local operator API_TOKEN bảo vệ read diagnostics; chưa có writes/users/tenant management. Private data network, generated secrets, restricted CORS; dev bootstrap credentials chưa tách least-privilege application accounts, public hardening còn mở |
| P03-006 | Official MinIO registry manifest trả401 sau public auth và archive binary trả410. Giữ MinIO bằng source build tại commit07c3a429bfed433e49018cb0f78a52145d4bedeb, tar SHA-256 pinned, Go1.25.3 và license đi kèm. Không tự thay stack hoặc trỏ image không tải được |
| P03-007 | Dùng HTTPX AsyncClient/ASGITransport với lifespan trực tiếp cho API tests. TestClient thread portal bị treo trong môi trường kiểm chứng; không khẳng định nguyên nhân. Real HTTP smoke được chạy riêng qua Uvicorn/Vite |
| P03-008 | uv.lock và package-lock.json khóa dependency tree; Node22.23.4/npm11.21.1. npm10 resolver lỗi edgesOut, npm11 resolve được. ESLint đã nâng10.14.0; audit vẫn có12 moderate dev-toolchain findings bắt nguồn minimatch, runtime audit không có finding; không force downgrade/breaking overrides chưa chứng minh tương thích |
| P03-009 | Không thêm Router/TanStack Query khi chỉ một page và health requests: typed fetch client + abort/deadline/runtime decoders, explicit status states; search submit disabled và query-image preview local không upload |
| P03-010 | Đã chạy ba data services và HTTP/integration bằng native binaries/source build trong /tmp vì Docker daemon không có. Compose config validation pass; actual container build/start vẫn chưa được kiểm chứng, không coi native tests là bằng chứng Docker volumes/network hoạt động |

Các quyết định P03-001/008/010 ghi trạng thái lượt triển khai đầu; phần bổ sung dưới đây cập nhật các blocker đã xử lý. O-02 được inspect sơ bộ nhưng chưa có benchmark hardware/load envelope; O-13 library/toolchain versions đã lock, exact AI checkpoint/processor vẫn mở. Rights/privacy/quality gates/agent provider vẫn mở theo deadline cũ. Prompt04 chưa được khởi động.

## 11. Bổ sung nghiệm thu Prompt 03

Ngày2026-11-03, sau khi người dùng cấu hình Docker Snap:

| ID | Quyết định / evidence |
| --- | --- |
| P03-011 | Docker Snap cần disable/enable sau khi thêm nhóm docker; restart đơn thuần chưa đổi socket root:root. Dùng quyền nhóm trong phiên mới/sg docker, không chmod666. Engine29.8.0/Compose5.5.1 build/start đủ năm services healthy; xác minh persistence và outage/recovery bằng scripts/verify_containers.py, report JSON lưu trong docs/verification |
| P03-012 | Backend image phải COPY cả scripts/, .env.example và ruff.toml để script-safety tests/static checks chạy được bên trong container. Chạy32 backend unit,3 integration thật,8 frontend unit và static/build checks thành công |
| P03-013 | Override minimatch11.0.1 thay10.2.6 cho dev consumers dùng functional/class API hiện đại. So7 glob patterns ×9 paths qua hai APIs, rồi typecheck/lint/unit/build đều qua; audit toàn tree hiện0 findings. Theo dõi upstream để gỡ override khi phù hợp; không suy ra tương thích mọi use case |
| P03-014 | Playwright1.64.1/Chromium thật kiểm tra desktop1440×1000/mobile390×844 qua Docker UI/API,6 tests pass không skip. Tắt trace để không lưu auth headers; ảnh preview chỉ local. Sửa mobile form thành cột để selector hiển thị đầy đủ. Render11 Mermaid sources bằng CLI11.17.1; thay semicolon trong ingestion note bằng xuống dòng Mermaid hợp lệ |
| P03-015 | Host .git thực tế rỗng và writable sau khi kiểm tra ngoài sandbox; init nhánh main tại project root không ghi đè history. O-20 phần local repository đã giải quyết; chưa tạo commit/remote/CI. Secrets, dependencies và raw browser outputs được ignore |

Evidence hiện tại tại [PHASE03_REPORT](PHASE03_REPORT.md), thay các giới hạn lịch sử về Docker/Git/audit/browser ở lượt trước. Đây là nghiệm thu local development; không phải benchmark retrieval hoặc production hardening.

## 12. Quyết định implementation Prompt 04

| ID | Quyết định / hệ quả |
| --- | --- |
| P04-001 | Giữ PostgreSQL durable queue, worker process dùng cùng backend package; không BackgroundTasks/Celery/Kafka. Compose indexing profile thêm worker, API image không cài/load Torch |
| P04-002 | Chọn openai/clip-vit-base-patch32 revision3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268, official processor, runtime dimension512, L2/cosine float32. Download explicit; conversion weights_only sang safetensors, runtime local-only; source/config/weights hashes trong immutable manifest |
| P04-003 | CPU baseline, auto CUDA nếu runtime hỗ trợ; lockfile hiện dùng CPU PyTorch. Không silent device/precision fallback; CUDA OOM chia batch cùng device, chưa CUDA benchmark. CPU 4 threads/batch4 là dev defaults, không optimum claim |
| P04-004 | 10 sample images từ scikit-image v0.25.2 có CC0/public-domain notes và upstream SHA checks, không captions/tags giả. Đây là fixture corpus, không relevance/qrels benchmark hoặc approval cho dữ liệu người dùng |
| P04-005 | Upload reserve awaiting_input trước immutable final original PUT/GET/hash rồi transaction receipt+queued; bỏ staging copy dư thừa cho bytes đã validate. Idempotency lưu reserved response, lease/in-progress409, crash-resume giữ identities; deadline upload30s tách core2s |
| P04-006 | Migration thêm7 bảng cần cho tags/objects/embeddings/items/attempts/idempotency/active pointer; giữ revision0001 và dữ liệu. SKIP LOCKED/partial unique/claim nonce/lease heartbeat, bounded retries, source digest/revision checks trước ready |
| P04-007 | Collection name theo version/config hash; validate metadata/dimension/cosine, applied write + retrieval + exact queryability trước ready. Reindex collection mới, không auto active pointer switch. Worker source model fingerprint khác phải dùng registry tương ứng |
| P04-008 | Read/write operator tokens riêng, private authenticated content proxy; thumbnail optional fallback original. Delete workflow/automatic cleanup/scheduler/activation chưa triển khai, trả feature disabled thay vì giả thành công |
| P04-009 | Host override bổ sung host_access bridge cho loopback ports vì Docker Engine hiện không publish internal-only network ports. Default Compose tiếp tục private data network. Dockerfile tách dependency layer và cache uv; bootstrap hatchling cần network lần đầu, không dùng offline trước khi build backend package |
| P04-010 | Reconcile verify receipts/vector hashes/count/IDs, repair enqueue đúng record; orphan objects/vectors report-only. Không xóa collection/original ứng dụng để làm sạch report. Tests chỉ cleanup UUID namespace do chính lượt test tạo |

O-13 đã chốt CLIP baseline artifact và library locks cho E1, SigLIP/provider chưa triển khai. O-02 có CPU fixture profile, chưa online load envelope. Data quyền riêng tư/nonfixture corpus, quality gates, CUDA verification, public auth/TLS/least-privilege/backup vẫn cần chốt theo phase liên quan. [INDEXING_TEST_REPORT](INDEXING_TEST_REPORT.md) là evidence hiện hành; các trạng thái Prompt01–03 là lịch sử.

## 13. Quyết định implementation Prompt05

| ID | Quyết định / rationale |
| --- | --- |
| P05-001 | ClipQueryEncoder bọc ClipEncoder Prompt04, load cùng pinned checkpoint/tokenizer và verify manifest; không sửa image fingerprint/reindex. API process preload once/lifespan, indexing vẫn process riêng |
| P05-002 | Giữ canonical text/mode/response contracts; thêm query/search_mode aliases và image-only /search/multimodal compatibility theo Prompt05. Không trộn text+image hoặc activate advanced modes chưa có |
| P05-003 | Explicit admin activation: verify receipts/count/IDs, preload paired model, lock ready index/pointer và publish generation. Runtime pin model/index; generation đổi trả INDEX_SWITCHING tới reload, không chọn model khác âm thầm |
| P05-004 | DefaultK10/max50/config≤100, C50/cap1000, actual cosine scores, deterministic score/UUID tie/dedup. Basic payload filters + PG recheck/available+ready+hash+revision+object receipts; không trả storage keys/caption/filename giả |
| P05-005 | Single inference slot và bounded queue/50ms wait; cancel giữ slot đến actual thread finish. Private result image fetch→blob; read token chỉ memory, không VITE/storage/URL. Missing objects omit+warning, service outage làerror |
| P05-006 | Full server timing ở final ASGI send, response processing field giữ boundary riêng. Bounded private diagnostic samples10k/process, join request IDs cho benchmark; no user-query persistence/logging |
| P05-007 | Corpus10 fixture và smoke query groups chưa có human-verified qrels: metrics formulas/test fixtures có thật nhưng actual Recall/MRR/nDCG not_measured. Evaluator require exhaustive verified judgments/universe và actual availability/index eligibility |
| P05-008 | Baseline đo image preprocessing median~430ms; profiling chỉ ra Pillow startup và PNG serialization. Preloaded decoder process dùng đúng hàm decode Prompt04, framed JSON/RGB IPC không pickle, resource/deadline bounds, restart/terminate và pixel-equivalence tests. Benchmark before/after giữ nguyên model/corpus/concurrency; không query-image cache |

Quality/language/corpus generalization, CUDA và mixed-load/large corpus vẫn mở cho Prompt07. Actual baseline và failures/limits tại [SEARCH_TEST_REPORT](SEARCH_TEST_REPORT.md). Không tự chuyển sang Prompt06.

## 10. Quyết định triển khai Prompt06

| ID | Quyết định / đánh đổi |
| --- | --- |
| P06-001 | Rules/parser hữu hạn tiếng Việt/Anh, AND ưu tiên OR, grouping/depth2/leaves8; original whole-query giữ nguyên. Ambiguous patterns fallback có warning, không claim general language understanding. |
| P06-002 | Separate compatible text/image retrieval rồi weighted RRF baseline; thêm cosine affine weighted-score để so sánh. Missing branch contribution0, không đổi missing cosine thành actual score hoặc probability. Weights/k chưa tune bằng labels. |
| P06-003 | Bounded fan-out≤4, total requested candidates≤1.000, union default100; batch text encoding, shared preload/queue/decoder Prompt05. Không microservice/model download/schema change. |
| P06-004 | Required Boolean gate tri-state độc lập rerank, optional projection không bypass mandatory OR. Missing metadata/visual evidence UNKNOWN. Strict required semantic constraint409 khi verifier unavailable. |
| P06-005 | Transparent rerank dùng stored-vector digest checks, whole/per-clause normalized cosine, verified metadata, configurable unknown/mismatch penalties; score_type/version riêng. Negation similarity chỉ soft signal. Không heavyweight model thiếu evidence. |
| P06-006 | Rerank off/request default; candidate/time budgets; error hoặc explicit skip+warning, không partial mutation/weakening required constraints. Model/vector mismatch không fallback. Fast search không gọi reranker. |
| P06-007 | E1–E5 harness/latency và abstention-aware metric code; human qrels chưa có nên không claim Recall/nDCG/constraint success hoặc quality improvement. Corpus10 chỉ functional/performance baseline. |
| P06-008 | Mở rộng v1 tương thích: image-only giữ, paired/text-only trên multimodal; boolean/flat aliases validate trước normalization; canonical AST/evidence giữ. Core paired input vẫn422. Agent/RAG/multi-hop vẫn tắt. |

Actual tests, số đo và các rủi ro chưa đóng tại [ADVANCED_SEARCH_TEST_REPORT](ADVANCED_SEARCH_TEST_REPORT.md). Các defaults là provisional cho nghiên cứu Prompt07, không là best settings đã xác minh.

## Quyết định triển khai Prompt07

| ID | Quyết định và bằng chứng |
| --- | --- |
| P07-001 | Người dùng chưa có qrels, yêu cầu công cụ gán nhãn trước. Tạo HTML offline, exhaustive0/1/2/unknown, draft luôn chưa verified; không tự tạo semantic ground truth. |
| P07-002 | Freeze10 ảnh/28 cases và family split;24 semantic cases chờ đánh giá,4 exact identity dùng UUID/hash độc lập, không đổi identity thành semantic-quality claim. |
| P07-003 | CLI và HTTPX load runner trong cùng codebase, nearest-rank/full ASGI/request-ID joins, ghi mọi failure/warmup/timeouts; immutable UTC/UUID outputs và source archives khi Git chưa có commit. |
| P07-004 | SigLIP2-base-patch16-224 pinned75de2d55ec2d0b4efc50b3e9ad70dba96a7b2fa2 dùng official paired processor/768 dimensions và durable reindex riêng; không activate hoặc trộn embedding space. |
| P07-005 | Controlled ABBA600 mẫu mỗi width: HEAD2 giảm object-stage mean nhưng full mean/P90 không tốt hơn. Giữ default1, width2 chỉ là lựa chọn thực nghiệm; ranking của12 queries giống nhau trong1.200 samples. |
| P07-006 | Benchmark fast cuối500/0 errors/P90145,80ms đạt mục tiêu trong điều kiện đã đo. Lỗi tải5/10/20 clients là4,4%/56,6%/86,4%; không suy production capacity từ successful-only latency. |
| P07-007 | Không có human labels nên chưa chọn model/fusion/ANN/rerank winner hoặc quality–latency Pareto; CPU-only, không giả GPU/cache-cold/large-corpus results. Prompt08 chưa bắt đầu. |

[EXPERIMENT_RESULTS](EXPERIMENT_RESULTS.md) và [PHASE07_TEST_REPORT](PHASE07_TEST_REPORT.md) là evidence hiện hành; giữ quyết định/snapshot lịch sử các phase trước.

## Cập nhật triển khai Prompt08

Đã có RAG metadata tùy chọn, tái sử dụng SearchService/active CLIP, batch evidence validation/current IDs, bounded context/prompts, Gemini/OpenAI-compatible adapter, citation validation, JSON/SSE và React explanation panel. Không gửi ảnh sang provider hoặc thay Fast Search/ranking. Gemini key ở backend; generator tắt/lỗi giữ ảnh. Với corpus10 ảnh không caption/tags, chưa thể xác minh nội dung thị giác. [Kiến trúc](RAG_ARCHITECTURE.md), [API hiện hành](RAG_API.md), [cấu hình](RAG_IMPLEMENTATION.md), [đánh giá](RAG_EVALUATION.md), [nghiệm thu A–L](PHASE08_TEST_REPORT.md). Không triển khai Prompt09.
