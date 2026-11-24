> Bản lưu PRD trước lần biên soạn 2.0 ngày 23/11/2026. Nội dung có các cập nhật sau baseline 03/11; giữ nguyên để truy vết lịch sử. Tài liệu hiện hành: [PRD.md](../PRD.md). Các đường dẫn và mô tả triển khai lịch sử có thể không còn đúng.

# PRD — Hệ thống tìm kiếm ảnh đa phương thức

Cập nhật triển khai Phase 06: multimodal late fusion, multi-intent/AND/OR và lightweight reranking đã được bổ sung trên core Phase 05. Fast path không gọi LLM hoặc tự fan-out query đơn giản. [Báo cáo Phase 06](../../archive/ADVANCED_SEARCH_TEST_REPORT.md) ghi tests/số đo/giới hạn; [API hiện hành](../../features/ADVANCED_SEARCH_API.md) bổ sung contracts. Các sections baseline/historical bên dưới giữ ngữ cảnh thiết kế, không phải bằng chứng triển khai mọi tính năng tương lai.

Phiên bản thiết kế: 1.1.0 · Ngày: 2026-11-03 · Giai đoạn: Phase 02. Đây là đặc tả, chưa phải tính năng đã triển khai. Baseline: [MASTER_SPEC](MASTER_SPEC.md), [REQUIREMENTS](REQUIREMENTS.md).

## 1. Tổng quan sản phẩm

**Tên:** AI Multimodal Image Search System. **Vấn đề:** tìm kiếm chỉ bằng từ khóa không biểu đạt tốt nội dung và ngữ cảnh thị giác; người dùng còn cần tìm bằng ảnh tham chiếu và điều kiện kết hợp. **Giá trị:** tìm ảnh theo ngữ nghĩa trong corpus đã được cấp quyền, trả kết quả có metadata và phương pháp xếp hạng rõ ràng.

**Mục tiêu sản phẩm:** P0 gồm ingestion/indexing bền vững, text-to-image, image-to-image, Top-K, metadata, API, web responsive và đánh giá thực nghiệm. P1 bổ sung text + image, multi-intent, filter, fusion/reranking; hybrid chỉ khi có bằng chứng lợi ích. P2 tùy chọn gồm RAG, agent và multi-hop có evidence. Hệ thống hoạt động đầy đủ ở P0 khi không có LLM.

**Động lực nghiên cứu:** so sánh embedding model, mức đánh đổi ANN/quality/latency, fusion và mức thỏa điều kiện; xác định khi nào reasoning nhiều bước mang lại lợi ích đủ bù chi phí. Không coi cosine là xác suất liên quan hoặc một bằng chứng thỏa toàn bộ điều kiện.

**Phạm vi phi chức năng:** chất lượng truy hồi có ground truth, đo latency đúng biên, bảo mật upload, phục hồi lỗi liên kho, observability, reproducibility, giới hạn tài nguyên và deployment có thể thay thế model.

**Ngoài phạm vi MVP:** native mobile, huấn luyện model mới, graph database, microservices, agent không giới hạn, thu thập URL tùy ý và tự động caption bắt buộc. Chưa xác định corpus, quy mô, hardware hoặc chất lượng tiếng Việt; tài liệu tiếng Việt không đồng nghĩa model đã hỗ trợ tiếng Việt đạt chuẩn.

## 2. Người dùng và giả định sản phẩm

| Persona | Nhu cầu | Quyền dự kiến |
| --- | --- | --- |
| Người tìm ảnh phổ thông | Tìm bằng mô tả/ảnh; xem ảnh, metadata, trạng thái lỗi | `search:read` |
| Người nghiên cứu | So sánh phương thức, xem evidence và hạn chế | `search:read`; kết quả thí nghiệm được chia sẻ riêng |
| Quản trị dataset | Nạp batch, sửa metadata qua quy trình quản trị, reindex, xóa, theo dõi lỗi | `images:write`, `index:manage` và quyền đọc |
| Developer/evaluator | Reproduce build/run, chạy benchmark, phân tích trace đã khử dữ liệu nhạy cảm | CLI nội bộ được cấp quyền; không mở benchmark API công khai |

Giả định triển khai đầu tiên: một corpus, một tổ chức/single-tenant, Linux local, bind loopback. Bearer token opaque ánh xạ scope bằng cấu hình backend; không có đăng ký tài khoản trong MVP. Không bật anonymous write. Trình duyệt giữ token do người vận hành cấp trong memory của phiên, không nhúng vào bundle. Public exposure và multi-tenancy cần thiết kế bổ sung trước khi bật. Đây là lựa chọn phát triển, không phải thông tin người dùng đã xác nhận.

## 3. User stories

| ID | User story |
| --- | --- |
| US-01 | Là người tìm ảnh, tôi muốn nhập mô tả văn bản để tìm nội dung có cùng ý nghĩa. |
| US-02 | Là người tìm ảnh, tôi muốn upload ảnh tham chiếu và xem preview để xác nhận đúng đầu vào. |
| US-03 | Là người tìm ảnh, tôi muốn tìm ảnh tương tự bằng ảnh mà không cần nhập text. |
| US-04 | Là người tìm ảnh, tôi muốn kết hợp ảnh với mô tả thay đổi để tìm kết quả đáp ứng cả hai nguồn thông tin. |
| US-05 | Là người tìm ảnh, tôi muốn truy vấn một ý định được xử lý trực tiếp để nhận kết quả nhanh. |
| US-06 | Là người nghiên cứu, tôi muốn khai báo nhiều điều kiện bắt buộc/tùy chọn để biết ảnh đáp ứng điều kiện nào và điều kiện nào chưa được xác minh. |
| US-07 | Là người nghiên cứu, tôi muốn bật filter/rerank khi phù hợp để so sánh chất lượng với chi phí tăng thêm. |
| US-08 | Là người nghiên cứu, tôi muốn tìm theo quan hệ nhiều bước để kết quả dựa trên entity và evidence đúng. |
| US-09 | Là quản trị dataset, tôi muốn nạp và retry batch để ảnh hợp lệ được index mà không tạo bản sao. |
| US-10 | Là người tìm ảnh, tôi muốn xem chi tiết, metadata và nguồn evidence để đánh giá độ phù hợp. |
| US-11 | Là evaluator, tôi muốn chạy bộ query/label cố định để đo Recall@10, nDCG@10 và latency có thể tái lập. |

## 4. Quy ước yêu cầu và nghiệm thu

ID chuẩn mới `FR-001`…`FR-023` ánh xạ 1:1 từ `FR-01`…`FR-23` của Phase 01; không xóa ID cũ. `FR-024` tách rõ generation embedding vốn nằm trong FR-01/02/08. `NFR-001`…`NFR-012` ánh xạ `NF-01`…`NF-12`; SEC-01…08 giữ nguyên. Traceability đầy đủ tại [DESIGN_REVIEW](../DESIGN_REVIEW.md).

Mỗi dòng dưới là một yêu cầu gồm tên/mô tả, ưu tiên, đầu vào, quy tắc, đầu ra, dependency và acceptance/test. `TC-FR-nnn` là **test thiết kế**, chưa được chạy. Mẫu Given–When–Then được diễn đạt trong cột cuối: Given là fixture/điều kiện, When là thao tác, Then là kết quả có thể kiểm tra. Các fixture liên quan phải có nhãn thật khi đo relevance.

### 4.1 Danh mục chức năng

| ID / Tên / Nhóm | Ưu tiên | Đầu vào | Xử lý | Đầu ra | Dependency | Acceptance / test |
| --- | --- | --- | --- | --- | --- | --- |
| FR-001 · Text search · Semantic Retrieval | P0 | Text không rỗng, K | Encode bằng paired text encoder của index đang dùng | Top-K ảnh, score type, version | FR-008/024, Qdrant, metadata | TC-FR-001: Given corpus có judgment; When tìm text; Then ID/rank hợp lệ và query smoke có ảnh liên quan, không gọi LLM |
| FR-002 · Image similarity · Semantic Retrieval | P0 | File hoặc image ID được phép đọc | Decode/encode ảnh, không yêu cầu text | Top-K tương tự | FR-004/024 | TC-FR-002: Given ảnh hợp lệ; When tìm chỉ bằng ảnh; Then có kết quả từ index tương thích; ảnh hỏng trả lỗi |
| FR-003 · Top-K · Semantic Retrieval | P0 | K mặc định 10 | Validate 1…100, dedup, tie-break UUID | 0…K ảnh eligible | Retrieval, FR-006 | TC-FR-003: Given ít hơn K ảnh eligible; When tìm; Then trả ít hơn K, không lấp bằng ảnh không hợp lệ |
| FR-004 · Ingestion · Image Ingestion | P0 | Upload/dataset đã đăng ký | Validate/hash/stage, tạo durable job, worker embed/store/index | Image ID và job ID/status | SEC-01/02/08, storage | TC-FR-004: Given file hợp lệ; When ingest và worker hoàn tất; Then object/metadata/point cùng ID và ready |
| FR-005 · Dedup · Image Ingestion | P0 | Bytes giống nhau, request đồng thời | Unique SHA-256; unique image/index; idempotency key | Một identity; trạng thái duplicate | PostgreSQL constraints | TC-FR-005: Given hai upload đồng thời; When hash giống nhau; Then không nhân đôi asset/vector record |
| FR-006 · Metadata · Administration | P0 | Image ID được cấp quyền | Hydrate metadata/provenance/lifecycle; không lộ object key nội bộ | Metadata, content URL | Metadata repository | TC-FR-006: Given ảnh ready/deleted; When đọc; Then ready có metadata nhất quán, deleted không đọc được |
| FR-007 · Durable jobs · Image Ingestion | P0 | Batch/job/item | Claim lease, bounded retry, per-item failure, recovery | Job progress và failed items | PostgreSQL, worker | TC-FR-007: Given worker chết giữa upsert/commit; When lease hết và retry; Then phục hồi không duplicate, không publish sai |
| FR-008 · Model/index versions · Embedding Generation | P0 | Immutable manifest, target index | Build riêng, kiểm tra compatibility, activate/rollback có kiểm soát | Version ready/active và lịch sử | FR-024, index registry | TC-FR-008: Given query/index khác manifest; When search; Then từ chối; index cũ vẫn dùng trước activation |
| FR-009 · API versioning · Administration | P0 | Contract v1 | Validate/auth/error schema; pagination job items | Typed API, structured errors | API layer | TC-FR-009: Given input sai/thiếu scope; When gọi từng endpoint; Then HTTP/code đúng contract |
| FR-010 · Web cơ bản · Frontend | P0 | Text/file/K | Preview, loading/empty/error, grid/details responsive | Luồng tìm thực trên desktop/mobile | Core APIs, content proxy | TC-FR-010: Given backend thật; When thao tác keyboard và viewport đã chọn; Then tìm/xem chi tiết và lỗi dùng được |
| FR-011 · Retrieval evaluation · Evaluation | P0 | Corpus/query/qrels cố định | Metric đúng định nghĩa, chia G1…G5 | Báo cáo E1…E4 áp dụng được | Dataset và judgment manifests | TC-FR-011: Given ranking/grade tính tay; When evaluate; Then metric khớp, unjudged/zero-relevant được ghi rõ |
| FR-012 · Latency/load · Evaluation | P0 | Workload, hardware, raw samples | Timer full ASGI, client riêng, error accounting | P50/P90/P95, throughput, errors | Instrumentation, harness | TC-FR-012: Given response có serialization/send delay; When đo; Then full timer chứa delay, partial timer được đặt tên khác |
| FR-013 · Combined input · Multimodal Search | P1 | Text và ảnh, weights | Encode riêng, union candidates, weighted RRF, optional rerank | Joint ranking và fusion version | FR-001/002/017 | TC-FR-013: Given query joint có labels; When thay một modality; Then thực thi cả hai encoder và báo đúng method; đánh giá ablation |
| FR-014 · Router · Multi-intent Search | P1 | Mode, text, constraints | Deterministic text/image/multi-intent routing; agent chỉ explicit | Executed mode và warnings | Query processor | TC-FR-014: Given nhiều ý định không quan hệ; When mode auto; Then không gọi planner/LLM |
| FR-015 · Decomposition · Multi-intent Search | P1 | AND/OR, required/optional | Extract patterns hỗ trợ, candidate union, verify tri-state | Constraint evidence; không tự khẳng định | FR-014, evidence adapters | TC-FR-015: Given thiếu evidence một required clause; When strict verification; Then ảnh không được ghi confirmed và bị loại |
| FR-016 · Metadata filters · Filtering and Reranking | P1 | Typed filters | AND giữa fields, any/all tags rõ ràng; PG recheck | Chỉ ảnh thỏa hard predicate | Metadata, Qdrant payload | TC-FR-016: Given field bắt buộc null/payload stale; When filter; Then không lọt vào kết quả |
| FR-017 · Candidate/rerank · Filtering and Reranking | P1 | K/C, rerank flag | C ≥ K, bounded fan-out, reranker versioned optional | Ranking/method/warnings | Retrieval, approved reranker | TC-FR-017: Given reranker lỗi; When fallback được phép; Then direct ranking và warning; không âm thầm đổi chính sách |
| FR-018 · Hybrid có điều kiện · Filtering and Reranking | P1 | Development evidence | So sánh lexical + semantic với baseline; chỉ adopt khi có lợi | Quyết định adopt/defer và ablation | FR-011 | TC-FR-018: Given báo cáo phát triển; When review; Then có rationale, cost và metric thật hoặc deferred rõ |
| FR-019 · Explanation · RAG | P2 | Retrieved evidence + image IDs | Generate có trích dẫn, validate ID/claim | Explanation hoặc insufficient_evidence | Evidence, optional generator | TC-FR-019: Given metadata không chứng minh màu xe; When giải thích; Then không khẳng định màu; citation chỉ tới ảnh đã retrieve |
| FR-020 · Retrieval độc lập RAG · RAG | P2 | Feature flag/provider lỗi | Không đưa generator vào dependency core | Core vẫn trả ảnh | Dependency injection | TC-FR-020: Given generator tắt/unavailable; When core search; Then không khởi tạo/call generator và vẫn thành công |
| FR-021 · Bounded reasoning · Multi-hop Search | P2 | Relational query và budgets | Output bước trước → input bước sau; evidence validation, bounded fallback | Final results, trace, resolved status | FR-022, retrieval | TC-FR-021: Given relation unknown/cyclic plan; When chạy; Then dừng trong budget, unresolved/fallback rõ ràng |
| FR-022 · Tools/entities · AI Agent | P2 | Typed entity/tool inputs | Lookup PostgreSQL có provenance; allowlist tools | Evidence entities và retrieval results | Entity repository | TC-FR-022: Given ID sai hoặc evidence chứa instruction; When tool call; Then reject ID, không thực thi instruction |
| FR-023 · Advanced controls · Frontend | P1/P2 | Capabilities và mode | Hiện filter/explanation khi khả dụng | UI và lỗi capability thống nhất | Health/API, FR-010 | TC-FR-023: Given agent disabled; When UI load/caller gọi agent; Then UI vô hiệu hóa và API 409 FEATURE_DISABLED |
| FR-024 · Compatible embeddings · Embedding Generation | P0 | Validated text/RGB image, model manifest | Processor riêng model, inference, finite/nonzero check, L2 normalize | Vector d chiều + manifest hash | Pinned PyTorch/Transformers model | TC-FR-024: Given vector NaN/zero hoặc processor khác revision; When encode/search; Then lỗi rõ, không index/search sai space |

### 4.2 Đủ mười hai nhóm

| Nhóm | Yêu cầu chính |
| --- | --- |
| Image Ingestion | FR-004/005/007 |
| Embedding Generation | FR-008/024 |
| Semantic Retrieval | FR-001/002/003 |
| Multimodal Search | FR-013 |
| Multi-intent Search | FR-014/015 |
| Filtering and Reranking | FR-016/017/018 |
| RAG | FR-019/020 |
| AI Agent | FR-022 |
| Multi-hop Search | FR-021 |
| Frontend | FR-010/023 |
| Evaluation | FR-011/012 |
| Administration | FR-006/009; job/reindex/delete của FR-007/008 |

## 5. Non-functional requirements

| ID (alias cũ) | Thuộc tính và tiêu chí đo | Verification thiết kế |
| --- | --- | --- |
| NFR-001 (NF-01) | P90 ≤ 300 ms, P95 đề xuất ≤ 500 ms; giả thuyết trên workload/hardware được khai báo, không phải kết quả | TC-NFR-001: load test full ASGI theo PERFORMANCE_DESIGN; báo pass/miss đúng số đo |
| NFR-002 (NF-02) | Agent/RAG TTLast mục tiêu ≤ 3 s; đo TTFirst, TTLast, full response và tool spans; null khi không đo được token | TC-NFR-002: streaming/provider instrumentation kiểm tra marker thời gian |
| NFR-003 (NF-03) | Mọi lỗi invalid/dependency/inference/timeout/overload có HTTP và safe error envelope; không giả thành empty result | TC-NFR-003: fault-injection và API negative cases |
| NFR-004 (NF-04) | Bounds hữu hạn cho upload, K/C, concurrency, queue, retry, hop/call/token/deadline; quá tải fail fast | TC-NFR-004: boundary/saturation/cancellation cases |
| NFR-005 (NF-05) | Không ready nếu thiếu artifact; retry/crash không phá identity; deletion chặn đọc trước cleanup | TC-NFR-005: partial-write và lease fencing/reconciliation |
| NFR-006 (NF-06) | Typed interfaces, strict TS, startup config validation, structured logs và correlation; lint/type/build checks không lỗi bắt buộc | TC-NFR-006: CI/local checks được pin tại Phase 03 |
| NFR-007 (NF-07) | Clean setup/reproduce bằng version pins, model/data/config hashes; migration/rollback và backup/restore được kiểm tra trước release | TC-NFR-007: clean environment và restore drill ở Phase 12 |
| NFR-008 (NF-08) | Mọi capacity/resource claim có corpus/hardware/load/precision/settings và CPU/GPU/RAM/VRAM samples; không đặt QPS tùy tiện | TC-NFR-008: manifest completeness và stress curve |
| NFR-009 (NF-09) | Core search chạy khi RAG/agent tắt/lỗi; không import/init optional provider bắt buộc | TC-NFR-009: regression với feature flags off/provider down |
| NFR-010 (NF-10) | Health tách live/ingest-ready/search-ready; thiếu index/model báo search chưa ready, optional agent không làm core unready | TC-NFR-010: dependency/bootstrap/disabled-mode matrix |
| NFR-011 (NF-11) | Không duplicate ID; tie-break UUID; score có type/version, không trình bày thành probability | TC-NFR-011: rank/dedup/schema checks |
| NFR-012 (NF-12) | Không secrets/raw query/image trong Git/log mặc định; search history opt-in; retention và rights rõ | TC-NFR-012: secret/log/retention inspection; SEC-01…08 |

Chất lượng retrieval được đo và tối ưu; chưa đặt numeric quality gate khi chưa có corpus/labels. Trước tuning ở Phase 07 phải chốt gate và split. Tính bảo mật chi tiết giữ SEC-01…08 trong baseline và được thiết kế tại SAD/API/DATABASE; test TC-SEC-01…08 ở DESIGN_REVIEW. Không có uptime/QPS/RTO/RPO cam kết chưa được xác nhận.

## 6. Performance objectives và giả định

| Chỉ số | Mục tiêu |
| --- | --- |
| Semantic Search P90 | ≤ 300 ms, giả thuyết cần benchmark |
| Semantic Search P95 | Đề xuất ≤ 500 ms, giả thuyết cần benchmark |
| Agent/RAG TTLast | Mục tiêu ≤ 3 giây, phụ thuộc model/output/hops |
| Default Top-K | 10 |
| Recall@10, nDCG@10 | Đo bằng judgment thật; chưa có baseline hoặc ngưỡng được xác nhận |

Biên server: nhận ASGI request scope trước đọc body → hoàn thành final response-body send. Bao gồm queue trong app, upload parsing/decode và mạng nội bộ; không bao gồm browser/external transit/proxy backlog trước ASGI. Client nhận toàn bộ response và browser rendering được đo riêng. Response JSON chỉ chứa `processing_ms` đo trước serialization; full latency ở metrics.

Warm inference: model/processors và pool đã preload, workload warmup đã tách. Cold: startup/model load/cache trạng thái ghi riêng. Chưa biết hardware/corpus/concurrency thực; không gán mục tiêu cho mọi môi trường. Giả định dự toán fast path ban đầu: API 15 + preprocessing 20 + inference 100 + vector 35 + filter 10 + optional rerank 40 + metadata 20 + serialization 10 = 250 ms, dành 50 ms dự phòng. Đây là ngân sách kỹ thuật, **không phải tổng P90 của các component** hoặc kết quả đo. Chi tiết workload/cache/timeout tại [PERFORMANCE_DESIGN](../../research/PERFORMANCE_DESIGN.md).

## 7. Nghiệm thu sản phẩm và giới hạn

P0 được nghiệm thu khi ingestion thật và text/image search qua API/UI thật hoạt động, có error handling, consistent identity, test tích hợp thực, evaluation và số đo reproducible. Khi chưa có đủ nhãn, chỉ được báo smoke correctness, không báo retrieval accuracy. P1/P2 phải có ablation/regression và feature gating; disabled mode trả lỗi rõ. Không đủ metadata thì giải thích/verification có thể unknown. Strict semantic mode có thể trả 0 ảnh; best-effort phải ghi rõ không đảm bảo tất cả điều kiện.

Các bảng FR/NFR là acceptance inventory, không phải danh sách test đã chạy. Tại Phase 02 chỉ nghiệm thu tính đầy đủ/nhất quán của thiết kế. Dataset rights, hardware, quality thresholds và public deployment là dependency còn mở; không cản scaffold local Phase 03 nhưng chặn claim/triển khai phụ thuộc vào chúng.
