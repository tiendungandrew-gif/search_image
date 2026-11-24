# Review thiết kế và bàn giao Phase 02

Phiên bản 1.1.0 · Ngày: 2026-11-03 · Phạm vi: tài liệu thiết kế tiếng Việt; không application source, model download, container deployment hoặc benchmark. Các tài liệu Phase 01 giữ nguyên bản gốc ngoài phần cập nhật cần cho consistency.

Đây là snapshot nghiệm thu Phase 02. Phase 03 đã nghiệm thu foundation trên Docker; Phase 04 có ingestion/indexing thật với evidence tại [INDEXING_TEST_REPORT](../archive/INDEXING_TEST_REPORT.md); evidence mới và các giới hạn tại [PHASE03_REPORT](../archive/PHASE03_REPORT.md). Các mô tả chưa có runtime/renderer/Git bên dưới là trạng thái lịch sử Phase 02: hiện11 Mermaid sources đã render, Git main đã init, chưa commit/remote/CI. Checklist7/7 ở đây vẫn chỉ xác nhận design artifacts, không nghiệm thu implementation các phase sau.

## 1. Kết luận và mức sẵn sàng

Bộ thiết kế Phase 02 đủ để bắt đầu **scaffold local Phase 03 khi được yêu cầu riêng**. P0 semantic search độc lập LLM; indexing durable chạy worker process riêng; model/index manifests thay thế được; API/storage/diagrams dùng cùng identity và lifecycle. Còn dependency phải giải quyết tại đúng phase: writable Git location và package/runtime pins trước repository setup; actual hardware trước cấu hình inference; corpus rights/privacy/model checkpoint trước nonfixture ingestion; labels/quality gates/load trước benchmark; public auth/TLS/backup policy trước public exposure.

Không còn tài liệu bắt buộc chưa tạo. Chưa có runtime implementation, compiled OpenAPI, executed SQL/migrations, rendered Mermaid, retrieval metrics hoặc performance evidence; đó không phải deliverables đã hoàn thành ở phase này. Readiness cho scaffold không đồng nghĩa production readiness hoặc acceptance của accuracy/latency targets. Không bắt đầu Phase 03.

## 2. Checklist đầy đủ thiết kế

### Checklist nghiệm thu Phase 02 — 7/7

Checklist này xác nhận tài liệu thiết kế đã có và được đối chiếu; không xác nhận runtime hoạt động hoặc benchmark đạt mục tiêu.

- [x] **PRD có yêu cầu chức năng và tiêu chí nghiệm thu rõ ràng.** [PRD](PRD.md) mục 4 có 24 FR với inputs, processing, outputs, dependencies, acceptance và planned test cases; mục 5–7 nêu NFR và gate nghiệm thu.
- [x] **SAD phân tách Fast Semantic Search và Agentic Search.** [SAD](SAD.md) mục 2, 5–6 và 9 quy định dependency một chiều, router deterministic và core chạy khi LLM/Agent tắt; [SYSTEM_ARCHITECTURE](archive/SYSTEM_ARCHITECTURE.md) mục 2 và 7 mô tả hai đường thực thi.
- [x] **Có sơ đồ kiến trúc tổng thể và sequence diagrams.** Có 11 Mermaid sources, gồm context/container/component/deployment, ERD và 6 sequence diagrams; danh mục tại mục 3 bên dưới. Mermaid chưa được parse/render bằng engine, giới hạn kiểm chứng được ghi tại mục 7.
- [x] **PostgreSQL, Qdrant, MinIO có schema và chiến lược đồng bộ.** [DATABASE_DESIGN](DATABASE_DESIGN.md) mục 2–6 định nghĩa 24 bảng, collections/payload, private object keys, shared IDs, retry/idempotency, partial recovery, deletion, reindexing và reconciliation.
- [x] **API request/response được định nghĩa đầy đủ ở mức thiết kế.** [API_SPECIFICATION](API_SPECIFICATION.md) có 8 core endpoints và content proxy, schemas/validation/auth/errors, JSON/multipart, examples và job pagination; chưa kiểm chứng bằng generated OpenAPI hoặc runtime tests.
- [x] **Có thiết kế benchmark Recall@10, P90, P95.** [PERFORMANCE_DESIGN](../research/PERFORMANCE_DESIGN.md) mục 1–2 và 5–8 định nghĩa boundaries, ground truth, metric formulas, warm/cold/load/cache, E1–E4 và error accounting; không tuyên bố đạt targets.
- [x] **Có DESIGN_REVIEW.md và checklist vấn đề chưa giải quyết.** Tài liệu này có traceability, risks/open decisions, validation thực tế và readiness; checklist còn mở tại mục 6, register chi tiết tại [DECISIONS](DECISIONS.md).

### Đối chiếu chi tiết

| Hạng mục | Kết quả review tài liệu | Evidence |
| --- | --- | --- |
| P0/P1/P2 và không LLM fast path | Đạt ở mức thiết kế | PRD, SAD, ADR-005 |
| Product/personas/stories/12 nhóm requirements | Đủ, 24 FR và 12 NFR chuẩn mới; aliases giữ baseline | PRD, matrix mục 4 |
| Module responsibilities/I/O/dependencies/failure/deadline/observability | Đủ design ports; chưa code | SAD mục 4–5 |
| Context/container/component/deployment | Có 4 Mermaid flowcharts thống nhất process/data boundaries | diagrams index mục 3 |
| Ingestion và 6 kiểu online behavior | Có 6 sequence files + single-intent dùng text/image sequences | SYSTEM_ARCHITECTURE |
| Multi-intent AND/OR/required/optional/unknown | Phân biệt hard metadata và semantic evidence; strict có verifier gating | SYSTEM_ARCHITECTURE mục 5 |
| Multimodal fusion | Weighted RRF candidate, alternatives/ablation và method versions | ADR-007, PERFORMANCE_DESIGN |
| PostgreSQL schema | 24 tables với types/PK/FK/UQ/index/nullability/retention; logical design | DATABASE_DESIGN |
| Vector/object storage | d theo manifest, UUID point, private keys/content proxy, isolated migration | DATABASE_DESIGN mục 4–5 |
| Cross-store consistency | Durable staging, ready CAS, stale writer caveat, tombstone/drain/reconcile | SAD mục 7, DATABASE_DESIGN mục 6 |
| APIs | 8 required routes và 1 supporting content route; schemas/examples/auth/errors/pagination | API_SPECIFICATION |
| Agent transport | Synchronous JSON; SSE406; token hooks hoặc null, không đo giả | API_SPECIFICATION mục 5 |
| Performance/research | Boundaries/budgets/metrics/ground truth/E1–E4/raw samples và controlled variables | PERFORMANCE_DESIGN |
| Security và rights | SEC-01…08 mapped; limits có proposal, public deployment/rights còn mở | SAD mục 8; matrix mục 4–5 |
| ADR | 8 records đủ context/decision/alternatives/rationale/tradeoffs/consequences/status | adr/ADR-001…008 |
| Không triển khai vượt phase | Chỉ có files dưới docs; không model/services/app code | Kiểm tra filesystem ở mục 7 |

“Đạt” ở đây chỉ nghĩa thiết kế có nội dung kiểm tra được, không có nghĩa test runtime đã pass.

## 3. Danh mục artifacts

**Tạo mới 26 files:** 7 tài liệu, 8 ADR, 11 Mermaid sources. **Cập nhật 4 files baseline:** MASTER_SPEC, REQUIREMENTS, ROADMAP, DECISIONS. ENGINEERING_STANDARDS giữ nguyên. Tổng bộ docs hiện tại: 31 files.

| Nhóm | Files |
| --- | --- |
| Baseline được cập nhật | [MASTER_SPEC.md](archive/MASTER_SPEC.md), [REQUIREMENTS.md](archive/REQUIREMENTS.md), [ROADMAP.md](ROADMAP.md), [DECISIONS.md](DECISIONS.md) |
| Baseline giữ nguyên | [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md) |
| Tài liệu Phase 02 | [PRD.md](PRD.md), [SAD.md](SAD.md), [SYSTEM_ARCHITECTURE.md](archive/SYSTEM_ARCHITECTURE.md), [DATABASE_DESIGN.md](DATABASE_DESIGN.md), [API_SPECIFICATION.md](API_SPECIFICATION.md), [PERFORMANCE_DESIGN.md](../research/PERFORMANCE_DESIGN.md), [DESIGN_REVIEW.md](DESIGN_REVIEW.md) |
| ADR | [ADR-001.md](../adr/ADR-001.md), [ADR-002.md](../adr/ADR-002.md), [ADR-003.md](../adr/ADR-003.md), [ADR-004.md](../adr/ADR-004.md), [ADR-005.md](../adr/ADR-005.md), [ADR-006.md](../adr/ADR-006.md), [ADR-007.md](../adr/ADR-007.md), [ADR-008.md](../adr/ADR-008.md) |
| Context/container/component | [system_context.mmd](../diagrams/system_context.mmd), [container_architecture.mmd](../diagrams/container_architecture.mmd), [component_architecture.mmd](../diagrams/component_architecture.mmd) |
| Ingestion/text/image | [image_ingestion_sequence.mmd](../diagrams/image_ingestion_sequence.mmd), [text_search_sequence.mmd](../diagrams/text_search_sequence.mmd), [image_search_sequence.mmd](../diagrams/image_search_sequence.mmd) |
| Multimodal/multi-intent/multi-hop | [multimodal_search_sequence.mmd](../diagrams/multimodal_search_sequence.mmd), [multi_intent_sequence.mmd](../diagrams/multi_intent_sequence.mmd), [multi_hop_agent_sequence.mmd](../diagrams/multi_hop_agent_sequence.mmd) |
| Database/deployment | [database_erd.mmd](../diagrams/database_erd.mmd), [deployment_architecture.mmd](../diagrams/deployment_architecture.mmd) |

Không tạo API_CONTRACTS/EVALUATION_PLAN song song; tên từng đề xuất ở Phase 01 được cập nhật thành API_SPECIFICATION/PERFORMANCE_DESIGN theo Phase 02.

## 4. Requirement traceability matrix

Các tests là **planned** cho implementation phases, chưa chạy. `POST search` gồm JSON text và multipart image; `CLI` là operator/evaluation nội bộ được thiết kế. Có đủ 43 baseline IDs và FR-024 tách rõ embedding adapter.

| Legacy | Canonical | Component / data | API hoặc interface | Planned test | Phase |
| --- | --- | --- | --- | --- | --- |
| FR-01 | FR-001 | Text encoder, retrieval, image_embeddings | POST search | TC-FR-001 | 05 |
| FR-02 | FR-002 | Image encoder, objects, vectors | POST search image-only | TC-FR-002 | 05 |
| FR-03 | FR-003 | Candidate/rank/eligibility | SearchOptions K/C | TC-FR-003 | 05 |
| FR-04 | FR-004 | Ingestion, images, image_objects, jobs | POST images / index jobs | TC-FR-004 | 04 |
| FR-05 | FR-005 | Hash UQ, image/index PK, idempotency | POST images / index jobs | TC-FR-005 | 04 |
| FR-06 | FR-006 | Metadata repository, UUID links | GET images/id, content | TC-FR-006 | 04–05 |
| FR-07 | FR-007 | Worker, items, attempts, leases | POST/GET index jobs, reconcile CLI | TC-FR-007 | 04 |
| FR-08 | FR-008 | embedding_models, search_indexes, active pointer | Reindex API, activate/rollback CLI | TC-FR-008 | 04–05 |
| FR-09 | FR-009 | API layer, DTO/auth/error models | Tất cả v1 routes | TC-FR-009 | 03–05 |
| FR-10 | FR-010 | React forms/grid/detail/preview | Core search/image/content APIs | TC-FR-010 | 10 |
| FR-11 | FR-011 | Evaluation tables, judgments, metric harness | Evaluation CLI | TC-FR-011 | 07 |
| FR-12 | FR-012 | ASGI middleware, raw samples, benchmark_runs | Metrics sink / load CLI | TC-FR-012 | 05/07 |
| FR-13 | FR-013 | Paired encoders, union, weighted RRF | POST search/multimodal | TC-FR-013 | 06 |
| FR-14 | FR-014 | Query router, explicit agent gate | Search mode/capabilities | TC-FR-014 | 06 |
| FR-15 | FR-015 | Constraint AST/evidence tri-state | constraints, require_verified | TC-FR-015 | 06 |
| FR-16 | FR-016 | Metadata filters, PG recheck, payload indexes | FilterSpec | TC-FR-016 | 06 |
| FR-17 | FR-017 | Candidate limits, optional reranker | rerank enabled/on_failure | TC-FR-017 | 06–07 |
| FR-18 | FR-018 | Hybrid experiment/adoption decision | Dev evaluation CLI | TC-FR-018 | 06–07 |
| FR-19 | FR-019 | Evidence/RAG, image-ID citations | explain optional on search/agent | TC-FR-019 | 08 |
| FR-20 | FR-020 | One-way optional dependencies | Core with generator disabled | TC-FR-020 | 08 |
| FR-21 | FR-021 | Bounded workflow state/deadline | POST search/agent | TC-FR-021 | 09 |
| FR-22 | FR-022 | entities/relationships, typed tools | Entity/retrieval tool registry | TC-FR-022 | 09 |
| FR-23 | FR-023 | React capability/evidence controls | GET health, advanced APIs | TC-FR-023 | 06/08–10 |
| FR-01/02/08 mở rộng | FR-024 | Compatible processor/model manifest | encode_text/encode_image | TC-FR-024 | 04–05 |
| NF-01 | NFR-001 | Full response metrics | ASGI + load CLI | TC-NFR-001 | 07 |
| NF-02 | NFR-002 | Generator hooks/tool spans | Agent/explain instrumentation | TC-NFR-002 | 08–09 |
| NF-03 | NFR-003 | Structured errors/dependency adapters | Error envelope, HTTP status | TC-NFR-003 | 03–11 |
| NF-04 | NFR-004 | Limits/deadline/admission | Config + all input validation | TC-NFR-004 | 03–11 |
| NF-05 | NFR-005 | Ready CAS, tombstone, reconciliation | Worker/reconcile/delete job | TC-NFR-005 | 04/11 |
| NF-06 | NFR-006 | Typed module ports/config/logs | Lint/type/build/startup checks | TC-NFR-006 | 03–11 |
| NF-07 | NFR-007 | Pins/manifests/migrations/deploy | Clean setup/reproduce CLI | TC-NFR-007 | 03/12 |
| NF-08 | NFR-008 | Environment/load/resource manifests | Benchmark artifacts | TC-NFR-008 | 07/12 |
| NF-09 | NFR-009 | Core dependency graph | LLM-off/provider-down regression | TC-NFR-009 | 08–11 |
| NF-10 | NFR-010 | live/ingest/search readiness | GET health | TC-NFR-010 | 03–05 |
| NF-11 | NFR-011 | Dedup/stable ranking/score labels | SearchResponse | TC-NFR-011 | 05–07 |
| NF-12 | NFR-012 | Privacy/secret policy/opt-in history | Safe log/config/history policy | TC-NFR-012 | 03–12 |
| SEC-01 | SEC-01 | Resource-limited content decoder | Multipart search/images | TC-SEC-01 | 04–05/11 |
| SEC-02 | SEC-02 | Generated keys/source registry | Source ID / admin CLI | TC-SEC-02 | 04/11 |
| SEC-03 | SEC-03 | Private objects/least privilege | Authenticated content proxy | TC-SEC-03 | 03–05/11 |
| SEC-04 | SEC-04 | CORS, Bearer scopes, quotas | All routes/auth matrix | TC-SEC-04 | 03/11 |
| SEC-05 | SEC-05 | Typed field/filter validators | DTOs, parameterized repository | TC-SEC-05 | 03–06/11 |
| SEC-06 | SEC-06 | Deadline/rate/admission limits | Search/upload/agent | TC-SEC-06 | 03–11 |
| SEC-07 | SEC-07 | Untrusted evidence, tool allowlist | RAG/agent interfaces | TC-SEC-07 | 08–09/11 |
| SEC-08 | SEC-08 | Rights/temp/delete/retention policy | Ingest registry, delete job | TC-SEC-08 | 02/04/12 |

## 5. Security acceptance cases và design walkthrough

| Case | Given–When–Then thiết kế |
| --- | --- |
| TC-SEC-01 | Given bytes quá cap, decompression bomb, hỏng hoặc multiframe; When upload; Then reject413/415/422 hoặc timeout có giới hạn, không index/publish |
| TC-SEC-02 | Given filename traversal/symlink escape/arbitrary URL; When submit dataset/upload; Then không dùng client path làm object key, chỉ source registry được cấp quyền |
| TC-SEC-03 | Given không token/read scope hoặc image deleting; When GET metadata/content hoặc direct bucket; Then không đọc được bytes; bucket private |
| TC-SEC-04 | Given origin ngoài allowlist/token thiếu scope/quota vượt; When request; Then deny CORS/auth/rate theo policy, không chỉ ẩn UI |
| TC-SEC-05 | Given unknown fields/filter injection/bad UUID/bounds; When API parse/repository query; Then structured safe errors, không raw SQL hoặc stack leakage |
| TC-SEC-06 | Given queue đầy/request chậm/agent quá calls; When thực thi; Then fail-fast503 hoặc bounded504, không thả slot khi compute vẫn sống |
| TC-SEC-07 | Given caption/tool evidence chứa instruction hoặc forged image/entity ID; When explanation/agent; Then không execute instruction, validate IDs/evidence/citations |
| TC-SEC-08 | Given dữ liệu chưa được cấp quyền hoặc query upload chỉ để tìm; When ingest/search/delete; Then reject rights thiếu, không tự index query image, cleanup theo policy và tombstone chặn đọc |

Walkthrough thủ công đã đối chiếu thiết kế: (1) text/image-only không cần generator; (2) multimodal hai encoder cùng manifest và UUID union; (3) multi-intent missing metadata không pass hard filter; (4) multi-hop seed→city→landmarks→retrieval dùng bindings có evidence; (5) simultaneous duplicate dùng hash UQ; (6) Qdrant upsert thành công nhưng PG ready commit lỗi vẫn không searchable; (7) stale worker không publish do CAS và delete cần quiescence; (8) chưa có model/index chỉ search-ready=false, bootstrap ingestion infrastructure không bị coi process dead. Đây là desk review, không execution evidence.

## 6. Rủi ro và quyết định còn mở

| Risk / open input | Ảnh hưởng | Mitigation / deadline |
| --- | --- | --- |
| Corpus/rights/language chưa chọn (O-01/03) | Không thể kết luận accuracy/multilingual hoặc public redistribution | Registry/rights manifest; chốt trước nonfixture ingestion/model selection |
| Hardware/load chưa biết (O-02/04) | Budget300ms có thể không khả thi, memory cho hai model activation chưa đủ | Inspect environment Phase 03, pin before benchmark; bounded switching503 nếu không dual-load được |
| Exact model/library/container pins còn mở (O-13) | Không có dependency compatibility proof | Pin và smoke ở Phase 03/04; dimension/processor assert từ artifact |
| Numeric quality gates/labels/annotators chưa xác nhận (O-07) | Không thể pass quality acceptance hoặc claim corpus recall | Freeze guide/dev-test/judgments/gates trước tuning; báo pooled-label limitations |
| Semantic verification coverage hạn chế | RRF/caption không chứng minh conjunction, negation/edit khó | Tri-state, strict verifier gating, best-effort disclosure, per-condition labels |
| Multi-store eventual consistency/stale writers | Có thể stale point/object drift sau ready | PG recheck/CAS/receipt/reconcile; deletion tombstone và writer drain; test crash/outage |
| Shared inference device/cancellation | Offline work làm tăng tails; thread timeout không hủy GPU | Admission/queues, process isolation/resource allocation; mixed-load benchmark |
| API/core deadline2s với upload lớn | Slow body/decode có thể timeout dù file dưới byte cap | Báo modality/size separately, đo client latency; bounds/timeout tune minh bạch trước final runs |
| Public exposure và multi-tenancy chưa thiết kế (O-05/18) | Static local tokens/in-process rate caps không đủ mô hình public phức tạp | Bind loopback, private data ports; public auth/TLS/shared enforcement design trước exposure |
| Data retention/backup rights (O-09/18) | Deletion live stores không đồng nghĩa backup đã purge | Owner chốt policy trước real user data; publish restore/deletion caveats |
| Git metadata workspace không hợp lệ (O-20) | Chưa thể commit hoặc assert clean worktree | Dùng source snapshot hashes; chọn writable project repo Phase 03, không sửa managed .git |
| Mermaid không có renderer tại môi trường | Chưa có parser/render evidence | Structural checks + manual review; chạy renderer khi toolchain có ở Phase 03 |

Register chi tiết và resolution mới tại [DECISIONS](DECISIONS.md), giữ đủ O-01…20. Không thêm technology để che các unknown này; mỗi technology có purpose tại MASTER_SPEC/SAD/ADR. Không phát hiện missing P0 requirement trong desk review; acceptance runtime vẫn chưa được chứng minh.

### Checklist vấn đề chưa giải quyết

Các mục dưới còn mở; checklist nghiệm thu tài liệu 7/7 không đóng các dependency này. Chỉ đánh dấu hoàn tất khi có quyết định hoặc evidence tương ứng.

- [ ] Chốt dataset, license/provenance và ngôn ngữ query trước nonfixture ingestion/model selection — O-01/O-03.
- [ ] Xác định hardware, corpus size và workload/concurrency trước cấu hình inference và benchmark — O-02/O-04.
- [ ] Pin và kiểm tra tương thích runtime/packages/container images, checkpoint/processor revisions, precision/dimension/index settings — O-13, Phase 03–07.
- [ ] Chốt annotators, judgments, dev/test splits và numeric quality gates trước tuning/held-out evaluation — O-07.
- [ ] Xác minh semantic-verifier coverage và hành vi strict/best-effort bằng tests/evaluation — O-08.
- [ ] Chốt quyền riêng tư, retention, deletion/backup policy trước nhận dữ liệu người dùng thật — O-09/O-18.
- [ ] Chốt auth/TLS, shared rate limiting và tenant isolation nếu mở public hoặc multi-tenant — O-05/O-18; ngoài local MVP hiện tại.
- [x] Chọn writable Git repository location trước repository initialization — O-20 local đã giải quyết ở Phase 03: host .git rỗng/writable, init main; chưa commit/remote/CI.
- [x] Parse/render 11 Mermaid sources bằng engine — bổ sung Phase 03: Mermaid CLI11.17.1/Chromium, [kết quả](../verification/mermaid.json) và SVG trong verification/diagrams.
- [ ] Chốt provider/evidence/entity data và budgets khả thi trước khi bật RAG/Agent — O-14…17; không chặn core scaffold.

## 7. Validation thực sự đã chạy

Đã đọc năm baseline docs và specification đính kèm trước khi viết. Đã chạy Python3 kiểm tra: FR/NFR IDs đầy đủ/unique; 12 JSON code-fence examples parse bằng `json.loads`; đủ 11 Mermaid files và source headers/bracket/sequence-block/ER-table-block checks; 24 ER entities có tên trong schema; 8 ADR đủ 7 trường; relative file links. Trước khi tạo report này, các link DESIGN_REVIEW là planned deliverable duy nhất chưa tồn tại; final pass kiểm tra lại sau khi tạo report.

Một check ban đầu đếm `{`/`}` trên toàn ER file không phù hợp vì crow's-foot relationship chứa `o{`; đã sửa **validator** để chỉ đếm table blocks. Đây không phải kết quả Mermaid parser. Desk review còn sửa hop definition/example: seed lookup không tính hop, nên unresolved seed có0 hops/1 tool call. Không có lỗi JSON example trong lượt kiểm tra.

`command -v` và `shutil.which` không tìm thấy `mmdc`, `node`, `npm`. **Chưa parse/render Mermaid bằng Mermaid engine.** Structural checks không chứng minh toàn bộ syntax/render layout. Chưa chạy PostgreSQL schema parser, migrations, API/runtime tests, model smoke, benchmark hoặc Docker. Git status báo workspace không là repository; không tạo commit.

Lệnh kiểm tra tài liệu có thể tái chạy từ project root (không cần dependency ngoài Python standard library):

```bash
python3 - <<'PY'
from pathlib import Path
import json, re, shutil
root = Path('docs')
phase2 = ['MASTER_SPEC','REQUIREMENTS','ROADMAP','ENGINEERING_STANDARDS','DECISIONS','PRD','SAD','SYSTEM_ARCHITECTURE','DATABASE_DESIGN','API_SPECIFICATION','PERFORMANCE_DESIGN','DESIGN_REVIEW']
assert all((root / (name + '.md')).is_file() for name in phase2)
json_count = 0
for p in root.rglob('*.md'):
    text = p.read_text()
    assert text.startswith('# '), p
    for target in re.findall(r'\]\(([^)]+)\)', text):
        if '://' not in target and not target.startswith('#'):
            assert (p.parent / target.split('#')[0]).is_file(), (p, target)
    for block in re.findall(r'```json\s*\n(.*?)\n```', text, re.S):
        json.loads(block)
        json_count += 1
prd = (root / 'PRD.md').read_text()
assert re.findall(r'^\| (FR-\d{3}) ·', prd, re.M) == [f'FR-{i:03}' for i in range(1,25)]
assert re.findall(r'^\| (NFR-\d{3}) \(', prd, re.M) == [f'NFR-{i:03}' for i in range(1,13)]
diagrams = list((root / 'diagrams').glob('*.mmd'))
assert len(diagrams) == 11
for p in diagrams:
    text = p.read_text()
    assert text.splitlines()[0] in ('flowchart LR', 'flowchart TB', 'flowchart TD', 'sequenceDiagram', 'erDiagram'), p
    assert text.count('[') == text.count(']'), p
    assert '```' not in text, p
    if text.startswith('sequenceDiagram'):
        opened = sum(bool(re.match(r'\s*(alt|opt|loop|par|critical|break|rect)\b', line)) for line in text.splitlines())
        assert opened == sum(line.strip() == 'end' for line in text.splitlines()), p
    if text.startswith('erDiagram'):
        assert len(re.findall(r'^    \w+ \{$', text, re.M)) == len(re.findall(r'^    \}$', text, re.M)), p
tables = re.findall(r'^    (\w+) \{', (root / 'diagrams/database_erd.mmd').read_text(), re.M)
assert len(tables) == 24
for table in tables:
    assert f'`{table}`' in (root / 'DATABASE_DESIGN.md').read_text(), table
for n in range(1,9):
    text = (root / 'adr' / f'ADR-{n:03}.md').read_text()
    for field in ('Trạng thái','Bối cảnh','Quyết định','Phương án đã cân nhắc','Lý do','Đánh đổi','Hệ quả'):
        assert f'## {field}' in text, (n, field)
review = (root / 'DESIGN_REVIEW.md').read_text()
for prefix, count in [('FR',24),('NFR',12)]:
    for n in range(1,count+1):
        assert f'TC-{prefix}-{n:03}' in review
for n in range(1,9):
    assert f'TC-SEC-{n:02}' in review
print('PASS: files/links/IDs/traceability/JSON/ER inventory/ADR/structural Mermaid checks')
print('JSON examples:', json_count)
print('Renderer availability:', {name:shutil.which(name) for name in ('mmdc','node','npm')})
PY
```

Lệnh này chỉ kiểm tra artifact consistency; không phải Mermaid renderer, JSON Schema validator, SQL validator hoặc runtime acceptance suite.

Final pass sau khi tạo report và hoàn thiện full response examples đã chạy chính snippet trên: **PASS** file count/relative links/IDs/traceability/12 JSON examples/24-table ER inventory/8 ADR fields/11 structural Mermaid checks. Review cuối còn làm rõ `rights_ref` có cột lưu trữ riêng và publish-ready phải row-lock/recheck tombstone để không làm sống lại ảnh đang xóa. Không có check runtime mới được suy diễn từ các kết quả này.

## 8. Sửa các lệch baseline và dependency validation theo thứ tự

1. Đã inspect/read baseline; không có app files để overwrite, ENGINEERING_STANDARDS giữ nguyên.
2. PRD được viết trước: personas/stories, canonical aliases, 12 groups, inputs/rules/outputs/deps/tests và targets không bịa số.
3. SAD dùng requirements đó, xác định typed ports, one-way dependencies và failure/timeouts.
4. SYSTEM_ARCHITECTURE dùng đúng ports, phân biệt six behaviors, constraints/fusion và agent state/budgets.
5. DATABASE_DESIGN bổ sung index registry/embedding/job-item/object/source tables cần cho lifecycle; không chỉ liệt kê 14 minimum tables thiếu consistency state.
6. API_SPECIFICATION dùng đúng UUID/state/auth/lifecycle; thêm content proxy route để private image URLs có handler cụ thể; health503 body là ngoại lệ đã khai báo.
7. PERFORMANCE_DESIGN khớp API timing/limits, budgets giả định và E1…E4/labels/metrics; không cộng stage percentiles.
8. Sinh11 Mermaid sources từ các luồng/schema trên, không thiết kế topology thứ hai.
9. Tạo8 ADRs; do ADR-002…008 mới không trùng ý nghĩa các label Phase 01, đổi namespace cũ thành P01-ADR-nnn và giữ full original decisions.
10. Review link/inventory/JSON/schema/API/requirements/diagrams và desk walkthrough; sửa hop definition; báo rõ parser/tool limitations.
11. Tạo report này và final consistency pass. Phase 02 dừng ở tài liệu, không tự triển khai Phase 03.

## 9. Bàn giao Phase 03

Khi được yêu cầu: chọn writable repo location, inspect hardware/toolchain, pin compatible Python/Node/packages/service images, tạo backend/frontend scaffolds, Compose private services, config/secrets example, health/auth/error skeleton, migration baseline và verification commands. Search-ready có thể false tới Phase 04/05, liveness/ingest infrastructure vẫn kiểm tra được. Không cần quyết định agent provider để scaffold core.

Trước ingestion thật phải chốt rights/privacy/resource limits/model manifest và thực thi tests. Trước quality/performance claims phải có actual labels/hardware/load và raw outputs. Các limitations ở mục6/7 phải đi theo phase handoff. Không có cam kết P90/P95/Recall hoặc grounded multi-hop success đã đạt.
