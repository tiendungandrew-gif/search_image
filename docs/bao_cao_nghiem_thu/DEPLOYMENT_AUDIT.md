# Kiểm toán triển khai cuối — Phase12

> Tài liệu lịch sử theo phase; lệnh trong nội dung giữ tên đường dẫn cũ. Hướng dẫn hiện hành tại [danh mục tài liệu](../README.md) và [scripts](../../scripts/README.md).

Ngày08/11/2026. Baseline là [nghiệm thu Phase11](PHASE11_TEST_REPORT.md), trạng thái READY_WITH_DOCUMENTED_LIMITATIONS. [Working tree ban đầu](../verification/phase12/baseline/git_status.txt) và [source snapshot](../verification/phase12/baseline/source.json) được lưu trước khi sửa. Không reset Git, commit, tag hoặc push.

Đã đối chiếu Master Spec, PRD, SAD, database/API, engineering standards, ADR, Search/Multimodal/RAG/Agent/frontend/evaluation và báo cáo lỗi Phase11 với entrypoints thực tế. Đường dữ liệu vẫn là modular monolith; không thêm Kubernetes, crawler hay remote fallback.

## Khoảng trống và thay đổi

| Trước Phase12 | Thay đổi đã triển khai |
| --- | --- |
| Frontend dùng Vite development server | Dockerfile.prod build Vite rồi phục vụ static assets bằng Nginx |
| Compose development có source bind mounts | Compose production độc lập, không mount source, chỉ frontend publish port |
| Migration nằm trong API startup | Bootstrap one-shot riêng, advisory lock và kiểm tra destructive upgrade |
| Worker bắt buộc một index trước startup | Worker daemon idle khi rỗng, lazy-load CLIP khi có durable jobs |
| Chưa có công cụ vận hành riêng | deploy.py: validate/build/up/down/check/status/logs/import/backup/restore/update/rollback |
| Chưa kiểm tra cold backup/restore | pg_dump custom + quiesced Qdrant/MinIO archives, checksums, empty-target guard |
| Chưa có HTTPS artifact | TLS Compose overlay và Nginx config; public domain/cert vẫn là đầu vào bên ngoài |
| CI chỉ QA/dev | Job production build/empty deployment/browser smoke, không cần model hoặc production key |

## Trạng thái thực tế

| Module | Trạng thái | Phạm vi |
| --- | --- | --- |
| Static frontend/reverse proxy | VERIFIED_WITH_REAL_SERVICES | Deep links, private media, API và browser trên Linux |
| Backend/PostgreSQL/Qdrant/MinIO | VERIFIED_WITH_REAL_SERVICES | Fresh bootstrap, private bucket, persistent volumes |
| Ingestion/indexing/worker | TESTED_WITH_SYNTHETIC_DATA | Ảnh tổng hợp, real storage, CLIP thật; index replacement có carry-forward |
| CLIP CPU | TESTED_WITH_SYNTHETIC_DATA |512 chiều, manifest/hash compatibility, real inference |
| Semantic/multimodal/multi-intent | TESTED_WITH_SYNTHETIC_DATA | Deployment mới; corpus513 thật của Phase11 được bảo toàn riêng |
| RAG/Agent optional | IMPLEMENTED | Mặc định tắt; kiểm tra disabled/not-ready và SSE fallback; không mặc nhiên có LLM |
| SigLIP production/GPU | NOT_VERIFIED | SigLIP thuộc evaluation adapter; production image hiện dùng CLIP/PyTorch CPU |
| Human relevance/faithfulness | BLOCKED | Chờ nhãn theo lựa chọn của người dùng |
| Remote GitHub/public production | NOT_VERIFIED | Không có hosting/domain/cert/registry credentials được cung cấp |

## Vấn đề môi trường đã xác nhận

Docker Snap trên máy kiểm chứng từ chối `exec` khi dùng `no-new-privileges:true`; cùng image MinIO chạy được khi bỏ tùy chọn đó. Production template giữ mặc định true, môi trường local Phase12 ghi rõ `DEPLOY_NO_NEW_PRIVILEGES=false`. Cap-drop, non-root/read-only của API/worker/frontend và private networking vẫn được kiểm tra. Không coi lần chạy compatibility này là chứng nhận hardening cho máy chủ khác.

Các lỗi harness ban đầu được giữ trong artifacts: selector nhầm tiêu đề trang đánh giá và assertion RAG-disabled không theo contract. Hệ thống thực tế trả NOT_READY khi chưa có index; khi có index, RAG disabled vẫn giữ retrieval và trả generated=false. Không sửa ứng dụng để ép khớp assertion sai.

Tổng hợp kết quả cuối, backup/restore, rollback và giới hạn ở [FINAL_PROJECT_REPORT](../FINAL_PROJECT_REPORT.md). Những phần chưa kiểm chứng không được đánh dấu pass chỉ vì Docker build thành công.
