# Kiểm toán hệ thống — Phase11

> Tài liệu lịch sử theo phase; lệnh trong nội dung giữ tên đường dẫn cũ. Hướng dẫn hiện hành tại [danh mục tài liệu](../README.md) và [scripts](../../scripts/README.md).

Kiểm tra ngày 07/11/2026 trên repository hiện có. [Báo cáo nghiệm thu](PHASE11_TEST_REPORT.md) là trạng thái mới nhất; báo cáo các phase trước giữ giá trị lịch sử. Không triển khai Phase12.

Đã đọc 15 tài liệu nền: Master Spec, PRD, SAD, kiến trúc, database, API, engineering standards, Semantic/Multimodal/Multi-intent Search, RAG, Agent, frontend, evaluation methodology và báo cáo Phase10. [Danh mục](../verification/phase11/baseline/document_inventory.json) xác nhận không thiếu tài liệu này. Nội dung tài liệu được đối chiếu với routes, schemas, services, migrations và tests; sự tồn tại của tài liệu không được tính là kiểm chứng tính năng.

Working tree đã có nhiều thay đổi Phase08–10 trước lượt này. [Git baseline](../verification/phase11/baseline/git_status.txt) và [source baseline](../verification/phase11/baseline/source.json) được giữ để phân biệt; không reset, commit hoặc push thay người dùng. [Source changes](../verification/phase11/source_changes.json) phân biệt24 file sửa và34 mục thêm vào snapshot so với baseline, không gộp thay đổi Phase08–10 vào Phase11.

## Kiến trúc thực tế

React → FastAPI → application services → PostgreSQL/Qdrant/MinIO. Worker dùng chung ingestion/embedding/index contracts, không nằm trên request tìm kiếm. Fast search không gọi Gemini. RAG và Agent là khả năng tùy chọn; thiếu provider hoặc knowledge không được suy diễn thành bằng chứng.

PostgreSQL sở hữu identity, metadata, job/lease, embedding receipt và active-index generation. Qdrant chứa vector/payload dẫn xuất; MinIO chứa object private. Không có distributed transaction: lease fencing, idempotency, verification và repair xử lý partial writes. Model manifest, dimension và index generation được kiểm tra trước retrieval.

## Ma trận trạng thái

| Module | Trạng thái cao nhất đã kiểm chứng | Bằng chứng và giới hạn |
| --- | --- | --- |
| FastAPI/config/auth/errors | VERIFIED_WITH_REAL_SERVICES | Startup, API, malformed input; unit/security/reliability |
| PostgreSQL/migrations | VERIFIED_WITH_REAL_SERVICES | Fresh database cho từng integration fixture, FK/unique/repository; không reset DB phục vụ |
| Qdrant | VERIFIED_WITH_REAL_SERVICES | Upsert/query/filter/dimension, zero-vector guard, versioning |
| MinIO/private media | VERIFIED_WITH_REAL_SERVICES | Upload/download/delete trong QA, anonymous 403, API thiếu token 401 |
| Ingestion/worker | TESTED_WITH_SYNTHETIC_DATA | JPEG/PNG/WebP, real storage, retry, duplicate, lease, SIGKILL, cancellation |
| CLIP encoder | TESTED_WITH_SYNTHETIC_DATA | CLIP thật, 512 chiều, normalized, identity round-trip; không phải relevance accuracy |
| Semantic Search | VERIFIED_WITH_REAL_DATA | Read-only corpus nhỏ 513 ảnh, 500 request C1; chưa có human qrels |
| Multimodal/Multi-intent | VERIFIED_WITH_REAL_DATA | Workload corpus hiện có + QA/fixture; constraint UNKNOWN vẫn UNKNOWN |
| Constraint semantic verifier tổng quát | NOT_IMPLEMENTED | Strict semantic constraints bị từ chối khi thiếu verifier; không giả xác nhận |
| RAG | VERIFIED_WITH_REAL_DATA | Gemini thật và citations; grounding/timeout/injection được kiểm tra thêm bằng mocks |
| Agent/tool executor | VERIFIED_WITH_REAL_DATA | Quan hệ NPS hiện có + fixture hư cấu cô lập; allowlist/budget/abstention |
| Frontend/API integration | VERIFIED_WITH_REAL_SERVICES | Vitest, Playwright mock/QA/serving; viewport emulation |
| Empty Dataset Mode | VERIFIED_WITH_REAL_SERVICES | Stack QA ban đầu không image/index/knowledge/benchmark |
| Evaluation formulas | TESTED_WITH_MOCKS | Numeric fixtures, frozen artifacts; không tự tạo nhãn relevance |
| Human relevance/faithfulness | BLOCKED | Chờ nhãn đã được người đánh giá xác nhận, theo lựa chọn trước của người dùng |
| Production-scale performance | IMPLEMENTED_UNVERIFIED | Có harness; corpus/hardware/load đại diện chưa có |
| GitHub Actions | IMPLEMENTED_UNVERIFIED | YAML/actionlint và local equivalents pass; chưa chạy trên GitHub |
| Deployment production/TLS | NOT_IMPLEMENTED | Thuộc Phase12; không mở rộng phạm vi lượt này |

Các trạng thái dùng đúng tập của Phase 11. `VERIFIED_WITH_REAL_DATA` chỉ mô tả execution trên dữ liệu thật hiện có, không đồng nghĩa AI đạt chất lượng sản phẩm.

## Sai lệch được xử lý

Đã bổ sung DTO/OpenAPI cho workspace/evaluation, chặn control characters trước database, kiểm tra vector trước RPC, sửa lifecycle/cancellation, SSE fallback và ErrorBoundary. Chi tiết root cause ở [BUG_FIX_REPORT](BUG_FIX_REPORT.md). Không thay API request hoặc thứ tự ranking để làm test pass.

Signed URL không phải đường phục vụ đang dùng: browser đọc qua authenticated same-origin proxy, `private, no-store`. Signed/expired URL là **N/A**, không báo pass cho tính năng không tồn tại. Worker metrics nay có giới hạn bộ nhớ; raw query, prompt và credentials không nằm trong log allowlist.
