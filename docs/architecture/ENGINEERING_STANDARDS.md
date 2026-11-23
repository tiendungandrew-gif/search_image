# Engineering Standards

Baseline: 1.0.0, 2026-11-03. Applies as implementation phases begin; it does not authorize implementation during Prompt 01.

## 1. Working process

- Inspect the repository, applicable instructions, current status, and affected documents before changes. Preserve unrelated work. If Git is unavailable, report that limitation rather than claiming a clean worktree or commit.
- Implement only the authorized phase. Maintain [MASTER_SPEC.md](MASTER_SPEC.md), requirement IDs, decisions, and phase status as behavior changes. Do not start the next prompt automatically.
- Prefer understandable modules and explicit contracts to premature abstraction or services. A separate worker process shares the backend codebase and typed interfaces.
- Label implemented, proposed, deferred, blocked, and measured status accurately. Do not insert hardcoded demonstration search outputs or fabricate experiment numbers.
- Pin exact dependencies, model artifacts, and deployable image versions during the appropriate phase. Document important tradeoffs in [DECISIONS.md](DECISIONS.md).

## 2. Source and module conventions

Proposed layout for Prompt 03 onward: `backend/`, `frontend/`, `infra/`, `evaluation/`, `tests/`, and `docs/`. Prompt 02 may refine names. Do not create empty implementation scaffolding solely for this documentation phase.

Python uses type hints for public interfaces, Pydantic for validated boundary models, and clear separation of API, application services, domain contracts, and infrastructure adapters. SQLAlchemy models do not become public API models by default. Use parameterized database operations and Alembic migrations; test migrations on a disposable database.

TypeScript uses strict mode, typed API responses, and explicit loading/error/empty states. UI code never obtains database, object-store admin, or generation-provider credentials. Shared schemas/OpenAPI-generated clients may be used when versioned and validated.

Linting, formatting, Python type-checking, TypeScript/build checks, and test commands are selected and documented in Prompt 03. Do not claim checks are configured or run before their configuration exists. Runtime/package versions and lockfiles must be reproducible; use local setup instructions and an environment example with placeholders only.

## 3. API conventions

- Version public routes under `/api/v1`; changes within v1 preserve compatibility or have an explicit migration/deprecation plan.
- Specify request/response bodies, transport/media types, required/optional fields, bounds, defaults, status codes, and examples in Prompt 02. Image-only and multimodal requests need content-validated transport; JSON cannot directly contain a raw binary upload.
- Proposed error envelope: `error: {code, message, request_id, retryable, details}`. Finalize it once in Prompt 02. Do not disclose stack traces, secrets, internal object paths, or unsafe decoder details.
- Distinguish invalid input, absent/unauthorized resources, incompatible indexes, disabled features, dependency unavailability, overload, timeout, and internal failures. Use consistent HTTP semantics; do not return successful empty results for a failed search.
- Successful Top-K results contain unique IDs and at most K eligible items. Search is rank ordered with an explicit K limit; cursor pagination belongs to large metadata/job-item lists. If future search pagination is introduced, document snapshot/ranking stability.
- Use generated request IDs and propagate them to dependency spans and jobs. API job acceptance means durable acceptance, not successful indexing; return a job reference and monitor progress separately.
- Authorization must be enforced in the backend and for object access. Define read/search versus ingest/reindex privileges before exposure. Do not rely on hidden UI controls.

## 4. Embeddings, indexing, and ranking

Every searchable vector has an immutable embedding-space manifest and index version. Include model revision, tokenizer/processor/preprocessing, dimension, precision, normalization, and similarity configuration. Reject version mismatch even when dimensions happen to match. Reject NaN, infinity, and zero-norm embeddings. Paired image/text encoders must come from the intended shared space.

Preserve raw originals privately where permitted; record transformations separately. Use generated object keys and stable UUIDs. Content-hash identity and image/version uniqueness must be enforced by database constraints as well as application checks. Document duplicate submission behavior and distinguish exact from perceptual duplicates.

Worker operations must survive retries and interruption: durable claims/leases, attempt history, deterministic/idempotent upserts, failure classification, bounded exponential backoff with jitter for transient errors, and terminal state for permanent invalid inputs. Avoid retrying invalid files indefinitely. PostgreSQL transactions cannot make object/vector writes atomic; persist progress and reconcile partial state.

Keep prior ready versions searchable until replacement activation is validated. New artifacts are isolated by index version; activation/rollback and cleanup must preserve referential consistency. Reconciliation must detect missing/stale objects, metadata, and vector points. Filter readiness at response construction even if the vector payload is stale.

Filtering cannot silently weaken mandatory constraints. Report unknown semantic evidence and score type. Fusion/reranking must have a version, declared candidate limits, and evaluation evidence; no probability language for uncalibrated scores.

## 5. Configuration, security, and resource management

Configuration is explicit, environment-specific, typed, and validated at startup. Define mandatory/optional dependencies and readiness. Reject unsafe public origins, missing required secrets, incompatible collections, and invalid limits early. Commit examples without real credentials; use deployment secrets/environment injection and least-privilege service users.

Before accepting uploads, enforce encoded-byte, decoded-pixel, frame-count, and decode-time/resource bounds. Use actual content decoding and a format allowlist, not filename or MIME trust. Define animation/multiframe handling and metadata stripping. Query-image retention is a separate lifecycle decision from indexed corpus retention.

Protect against unsafe filesystem paths, object-key traversal, arbitrary URL/server-side fetch, and unrestricted dataset paths. Restrict CORS to known origins. Define quotas and limits for uploads, batches, K, candidates, inference, text length, and agents. Threading an inference call does not necessarily cancel GPU computation: deadlines need bounded queues and execution capacity, with worker isolation if needed.

Private buckets are mandatory; choose authenticated proxy versus expiring signed access in Prompt 02. Avoid persistent bearer URLs in logs. No unrestricted agent shell/file/network tools. Treat captions, metadata, and relation evidence as untrusted input and validate image/entity IDs supplied to tools.

## 6. Observability

Structured logs include UTC timestamp, severity, event, request/job/run ID, component, duration, outcome/error code, and relevant model/index version. User-facing dates use the configured locale/timezone. Do not log raw queries, images, credentials, signed URLs, or sensitive metadata by default.

Measure complete server response duration with monotonic time at the ASGI boundary described in [REQUIREMENTS.md](REQUIREMENTS.md). Record stage durations and distinguish errors, cold starts, retries, and fallbacks. Use histograms or retained samples with explicit bucket/quantile choices; do not average percentiles from separate instances.

Track worker queue age, attempts, terminal failures, ready/failed item counts, vector/metadata reconciliation failures, model-load failures, inference utilization, memory, request throughput, and timeouts. Optional agent traces record tool names, safe inputs/outputs, evidence IDs, budget use, and per-step time without revealing private chain-of-thought.

## 7. Verification strategy

| Layer | Meaningful verification |
| --- | --- |
| Documentation | Required files/sections, relative links, consistent priorities/IDs/targets, no unsupported completion claims |
| Unit | Metric formulas, validation, normalization, routing, scoring/tie behavior, state transitions and retry classification |
| Integration | Actual PostgreSQL/Qdrant/MinIO adapters, image-ID consistency, filters, upserts, durable job recovery, version rejection |
| Model/retrieval | Small real-model smoke case and fixed labeled corpus; text/image encoder compatibility and relevant results; no reliance on fabricated embedding results |
| API | Valid and invalid text/image/multimodal inputs, authorization, errors, deadlines, health, unavailable dependencies |
| End-to-end | Browser search/upload/preview/detail flows, filters, mobile layout, failure/empty states, capability flags |
| Reliability/security | Concurrent duplicates, corrupt/decompression-bomb files, partial writes, worker death, dependency outage, overload, malicious evidence |
| Performance/research | Controlled workload and real labels, retained raw measurements/manifests, modality breakdown, resource and quality comparisons |

Use deterministic test doubles for isolated failure paths, and real services/models for integration evidence. Label the distinction. Tests must verify behavior rather than restate implementation. Reversible documentation changes do not need artificial application tests. Run appropriate checks for each phase and report exact commands, outcomes, skipped checks, and blockers; do not broaden repeated tests without a reason.

Research runs fix dataset/query/judgment versions, use development/test separation, record licenses/provenance, and preserve failures and seeds. Never tune on final held-out judgments. Report uncertainty and annotation limitations. Pin model artifacts without committing downloaded weights or private data to Git.

## 8. Definition of done and handoff

A phase is complete only when its required artifacts exist, relevant components are integrated, required verification has executed with outcomes reported, limitations are explicit, reproduction steps work, changes are reviewable/ready for version control, and the next phase's dependencies are satisfied. A document-only phase satisfies integration through coherent cross-references and consistent requirements; implementation phases require working code and execution evidence.

Record unmet targets and material check failures as outstanding work. A phase may deliver an honest benchmark showing an objective was missed, but may not claim that objective was achieved. Required functional or safety failures remain acceptance blockers; optional features can be explicitly deferred with rationale.

Each phase handoff includes scope, requirement IDs, changed artifacts, decisions, reproducible verification commands/results, remaining risks, and next-phase readiness. Prompt 01 does not create a commit: the supplied workspace's `.git` directory is not a valid repository and is read-only under the current environment. Do not modify it or assert Git status is clean.
