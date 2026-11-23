# Báo cáo tích hợp — Phase11

> Tài liệu lịch sử theo phase; lệnh trong nội dung giữ tên đường dẫn cũ. Hướng dẫn hiện hành tại [danh mục tài liệu](../README.md) và [scripts](../../scripts/README.md).

## Kết quả

**11 service integration tests và 1 AI integration test pass** trên hạ tầng QA thật. [Log service](../verification/phase11/runs/20261107T144831_617439_services.log) ghi kiểm tra sau bản sửa cancellation; danh mục bằng chứng cuối được ghi trong `final_audit.json`. Không tính tests legacy chưa chọn là đã chạy.

| Boundary | Kiểm tra đã chạy | Phân loại |
| --- | --- | --- |
| Alembic → PostgreSQL | Fresh schema, migration head, constraints, SQL bind parameters | REAL_SERVICES |
| FastAPI → ba dịch vụ | Liveness/readiness, workspace DTO, empty state, auth | REAL_SERVICES |
| PIL → ingestion → MinIO/PG/Qdrant | JPEG/PNG/WebP, bytes/hash, receipts, normalized vectors | SYNTHETIC_DATA + REAL_SERVICES |
| Concurrent ingestion | Cùng idempotency key, conflict hoặc cùng receipt, không nhân đôi | SYNTHETIC_DATA + REAL_SERVICES |
| Worker → Qdrant | RPC timeout mô phỏng một lần, real retry/upsert sau đó | FAULT_MOCK + REAL_SERVICES |
| Worker lease | Expired claim, old owner bị fencing, repair vector thiếu | REAL_SERVICES |
| Worker process | SIGKILL child đã claim; lease recovery hoàn tất durable job | REAL_PROCESS + REAL_SERVICES |
| Worker cancellation | Cancel lúc encoder thread còn đọc ảnh; ảnh được giữ đến completion | CONTROLLED_THREAD + REAL_SERVICES |
| Storage audit | Object orphan report-only; xóa object chỉ trong bucket fixture; anonymous403 | REAL_SERVICES |
| CLIP → full search | Sáu ảnh tổng hợp, embedding512, text/image/fusion/multi-intent | REAL_MODEL + SYNTHETIC_DATA |
| Agent knowledge | Fixture quan hệ hư cấu, 4 tools, ảnh liên kết đúng fixture | SYNTHETIC_DATA + REAL_SERVICES |
| RAG | Fixture provider, context metadata và citation validation thật | MOCK_LLM + REAL_SERVICES |

`test_real_dependency_failure_is_reported` có fault double cho probe; không gọi nó là service termination. Service termination thật nằm riêng trong [RELIABILITY_TEST_REPORT](RELIABILITY_TEST_REPORT.md).

## Kiểm tra vector và dữ liệu

Qdrant thực tế nhận zero vector, nên không thể dựa vào server để xác nhận embedding hợp lệ. Test hồi quy tái hiện worker báo succeeded với zero encoder; bản sửa chặn empty batch, sai shape, NaN/Inf và vector không L2-normalized trước RPC. Job lỗi là `INVALID_EMBEDDING`, collection không có point tương ứng.

AI test kiểm tra exact image identity score >0,99 khi exclude_self=false; đây là kiểm chứng round-trip, không phải Recall@10 ngữ nghĩa. Manifest mismatch bị từ chối. Alternative encoder cần index riêng; Phase11 không reindex SigLIP hoặc trộn embedding spaces.

Các fake vector có 8 chiều và manifest `fixture=true`; encoder đó chỉ tồn tại trong tests. Seed browser dùng CLIP cache thật. City/tag/metadata là authoritative SQL constraints; payload Qdrant không được dùng thay nguồn dữ liệu gốc.

## Giới hạn và cảnh báo

Qdrant client báo HTTP API key trên mạng nội bộ không TLS. Cảnh báo được giữ nguyên; TLS/exposure production thuộc Phase12. Signed URL là N/A vì media đi qua authenticated API proxy. Không chạy destructive test hoặc mutation trên corpus513 ảnh. Tích hợp Gemini trên corpus hiện có là phép đọc riêng, báo cáo ở [PERFORMANCE_REGRESSION](PERFORMANCE_REGRESSION.md).
