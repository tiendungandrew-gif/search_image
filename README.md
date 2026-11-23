# Synlens

Cập nhật 08/11/2026: [Tài khoản và giao diện](docs/operations/ACCOUNTS.md) — Admin/User, quyền theo thư viện và khu quản trị riêng.
Đăng ký tài khoản User: chọn **Đăng ký** trên trang đăng nhập, dùng ngay các thư viện chung cho thành viên; thư viện riêng do Admin cấp thêm. [Hướng dẫn tài khoản](docs/operations/ACCOUNTS.md).
Đăng nhập nhanh local: xem [hai vai trò trải nghiệm](docs/operations/QUICK_LOGIN.md).
Giao diện đa chủ đề 19/11/2026: [gallery nhiều kích thước, gợi ý chủ đề và ba cách tìm](docs/features/USER_INTERFACE.md). [Kiểm chứng UI người dùng](docs/verification/consumer_ui/REPORT.md).
Tìm kiếm Việt–Anh mặc định trong cùng ô nhập, tự xử lý tiếng Việt không dấu như `con meo`, không chọn ngôn ngữ: [cấu hình và kiểm chứng](docs/features/BILINGUAL_SEARCH.md).
Khách tìm ảnh công khai ngay tại trang đầu; đăng nhập ở `/login`. Admin chọn
thư viện công khai riêng với chia sẻ thành viên. [Hướng dẫn](docs/operations/ACCOUNTS.md)
· [Kiểm chứng guest](docs/verification/guest_search/REPORT.md).

Tìm kiếm ảnh bằng văn bản, ảnh tham chiếu hoặc kết hợp cả hai. Backend FastAPI dùng CLIP/Qdrant, PostgreSQL lưu metadata/jobs/knowledge, MinIO lưu ảnh private; React hiển thị kết quả và hỗ trợ RAG/Agent tùy cấu hình.

Trạng thái bàn giao Phase12: **READY_WITH_LIMITATIONS**. Functional deployment đã kiểm chứng local; human relevance/faithfulness, public hosting/security và capacity đại diện vẫn còn điều kiện chưa xác nhận. [Báo cáo A–T](docs/FINAL_PROJECT_REPORT.md) · [Checklist bàn giao](docs/FINAL_HANDOVER.md).

## Chạy hệ thống hiện có

Từ repository root, cần Docker Engine/Compose và quyền truy cập Docker:

```bash
docker compose up -d --wait --wait-timeout 180 backend frontend
```

Docker Snap trên máy kiểm chứng dùng:

```bash
sg docker -c 'docker compose up -d --wait --wait-timeout 180 backend frontend'
```

| Địa chỉ | Chức năng |
| --- | --- |
| http://localhost:5173 | Frontend development |
| http://localhost:8000/docs | Backend API/OpenAPI |
| http://localhost:8000/api/v1/health/live | Liveness |

Đăng nhập bằng tài khoản Admin/User. Thông tin Admin ban đầu nằm trong `.cache/auth/admin-login.json`; xem [quản lý tài khoản](docs/operations/ACCOUNTS.md). `.env` hiện có giữ credentials và dữ liệu của development. Khi setup development mới, chạy `python3 scripts/init_env.py` trước và thêm `--build` vào lệnh Compose; script không overwrite env đã có. [SETUP](docs/operations/SETUP.md) ghi prerequisites/model/data và cách chạy native.

```bash
docker compose logs -f --tail=100 backend frontend
docker compose down
```

`down` giữ named volumes. Có thể dùng `sg docker -c 'COMMAND'` cho các lệnh Docker còn lại trên máy Snap.

## Bản triển khai production-like

Môi trường nghiệm thu hiện có ở8088 dùng config riêng:

```bash
DEPLOY_USE_SG=1 python3 scripts/deploy.py --env-file config/environments/deployment.env up
```

Mở http://127.0.0.1:8088; tài khoản Admin dùng `.cache/auth/deployment-admin-login.json`. Bản nghiệm thu có7 ảnh tổng hợp, tách khỏi corpus513 ảnh của development. Alias `--env-file .env.phase12` vẫn được deployment CLI hỗ trợ. [Danh mục env](config/environments/README.md) giải thích các môi trường.

Cài production-like mới trên môi trường khác:

```bash
python3 scripts/deploy.py init
python3 scripts/deploy.py validate
python3 scripts/deploy.py build
python3 scripts/deploy.py up
python3 scripts/deploy.py check
```

Mặc định dùng `.env.deploy` và8080. App khởi động chưa có dataset/model/provider; tải model và import có chủ đích. [DEPLOYMENT_GUIDE](docs/operations/DEPLOYMENT_GUIDE.md) ghi Docker Snap compatibility, TLS và các giới hạn public deployment.

## Kiểm thử và dữ liệu

```bash
python3 scripts/qa.py up
python3 scripts/qa.py fast
python3 scripts/qa.py services
python3 scripts/qa.py frontend
python3 scripts/qa.py down
```

QA dùng `.env.qa` và namespace riêng. Docker Snap dùng `QA_USE_SG=1`; real-model profile cần cache đã chuẩn bị. [TESTING_AND_VERIFICATION](docs/operations/TESTING_AND_VERIFICATION.md) có browser/AI/lint commands và phân loại tests. Dataset/weights/backups/env thực bị loại khỏi Git/build context theo quy định tương ứng.

- [Nhập dataset](docs/operations/DATASET_IMPORT_GUIDE.md), [model](docs/operations/MODEL_MANAGEMENT.md).
- [Vận hành](docs/operations/OPERATIONS_RUNBOOK.md), [backup/restore](docs/operations/BACKUP_AND_RECOVERY.md), [bảo mật](docs/operations/SECURITY_DEPLOYMENT.md).
- [Cấu trúc repository](docs/REPOSITORY_STRUCTURE.md), [tài liệu theo chủ đề](docs/README.md), [danh mục scripts](scripts/README.md).
- [Kiến trúc](docs/architecture/FINAL_SYSTEM_ARCHITECTURE.md), [API](docs/architecture/API_SPECIFICATION.md), [database](docs/architecture/DATABASE_DESIGN.md).

README theo phase trước được giữ tại [archive](docs/archive/README_PHASE12.md). Raw benchmark/verification artifacts giữ kết quả gốc; đường dẫn lệnh đang dùng xem các hướng dẫn hiện hành.
