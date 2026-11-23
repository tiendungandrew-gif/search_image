# Cấu hình theo môi trường

Các file `.env` thực chứa credentials và bị loại khỏi Git/build context. Giữ nội dung và project IDs khi chuyển vị trí; không sinh credentials mới cho volumes đã tồn tại.

| File | Vai trò |
| --- | --- |
| `../../.env` | Development chính, frontend5173/backend8000; Compose mặc định đọc file này |
| `../../.env.qa` | Credentials QA riêng do `scripts/qa.py` quản lý |
| `deployment.env` | Bản nghiệm thu production-like8088, trước đây `.env.phase12` |
| `restore.env` | Diễn tập restore đã dừng, trước đây `.env.phase12-restore` |
| `archive/phase04.env` | Cấu hình nghiệm thu indexing cũ, trước đây `.env.phase04` |
| `archive/native.env` | Cấu hình native cũ, trước đây `.env.native` |

Mẫu công khai vẫn tại [`.env.example`](../../.env.example) và [`.env.deploy.example`](../../.env.deploy.example). Cài mới bằng `python3 scripts/deploy.py init` vẫn sinh `.env.deploy` riêng; thư mục này không tự áp cấu hình lên app.

Chạy deployment hiện có:

```bash
DEPLOY_USE_SG=1 python3 scripts/deploy.py --env-file config/environments/deployment.env up
```

`scripts/deploy.py` và `scripts/run_local.py` hỗ trợ các tên env cũ ở project root như alias khi file cũ không còn. Docker Compose trực tiếp cần đường dẫn thật; cấu hình development mặc định `.env` được giữ nguyên. File env đặt ngoài project không bị tự chuyển sang alias của project. Native/QA/serving configs tiếp tục bị deployment CLI từ chối.

[Cấu hình ứng dụng](../../docs/operations/CONFIGURATION_REFERENCE.md) · [Vận hành](../../docs/operations/OPERATIONS_RUNBOOK.md)

Giao diện mới đăng nhập bằng tài khoản, không nhập token từ env. Xem [tài khoản và quyền thư viện](../../docs/operations/ACCOUNTS.md). Migration bổ sung giữ nguyên dữ liệu và project IDs; release triển khai thay đổi riêng, secrets được giữ.
