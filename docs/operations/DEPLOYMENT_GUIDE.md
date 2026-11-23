# Hướng dẫn triển khai

Cập nhật tài khoản/UI 08/11/2026: xem [thiết kế quyền](../architecture/ACCESS_CONTROL.md) và [hướng dẫn đăng nhập](../operations/ACCOUNTS.md). Các hướng dẫn dùng data token trước đây chỉ áp dụng khi bật legacy; mặc định mới dùng session tài khoản.
## Ba môi trường

Development tiếp tục dùng `compose.yaml`, ports5173/8000, Vite và source mounts. Production-like dùng `compose.prod.yaml`: static frontend, API/worker cùng image, bootstrap riêng, volumes/network riêng. Production public bổ sung `compose.tls.yaml`, domain/cert thực, firewall và quyết định network của nơi chạy. Lượt này kiểm chứng local, không có máy chủ public được triển khai thay người dùng.

Máy kiểm chứng: Linux,16 logical CPUs/RAM khoảng15GiB, Docker29.8.0/Compose5.5.1. CLI vận hành cần Python3.11+ trên Linux và Docker/Compose; không cần cài Node/PyTorch lên host để build images. Node22.23.4/npm11.21.1, Python3.12.12/uv0.13.7 được pin trong Dockerfiles/locks. Dự trù tài nguyên cho hai process CLIP và cache/volumes; default API3GiB/worker3GiB là giới hạn, không phải RAM tối thiểu đã đo. Theo dõi disk và RAM trước khi tăng corpus/concurrency.

## Cài mới không dataset/model/provider

Từ repository root:

```bash
python3 scripts/deploy.py init
python3 scripts/deploy.py validate
python3 scripts/deploy.py build
python3 scripts/deploy.py up
python3 scripts/deploy.py check
python3 scripts/deploy.py status
```

`init` sinh `.env.deploy` mode0600, credentials riêng, không đọc/ghi đè `.env` serving. Khởi tạo project mặc định `image-search-prod`; frontend tại http://127.0.0.1:8080. Không có backend/data-service host ports trong deployment. Read token nhập vào UI từ `.env.deploy` tại máy người quản trị; không gửi token qua chat hoặc đưa vào VITE/build.

`build` tạo image API/worker và static frontend tại local Docker; không push registry. `up` không build/tải model ngầm. Bootstrap chờ dependencies, migrate head, tạo/kiểm tra bucket private; không tạo collection có dimension giả. Worker khởi động idle, không đòi dataset/index/model. SEARCH/RAG/AGENT mặc định false; app và navigation vẫn dùng được.

Chạy lại `up` không reset volumes hoặc active index. Script có operation lock, deadline, exit nonzero và logs tại `.cache/deployment/logs/`. Bootstrap kiểm tra các migration upgrade có DROP/TRUNCATE/DELETE: cần manual review, không tự vượt guard. Kiểm tra này không thay review một migration Python tùy ý.

## Docker Snap

Máy hiện tại dùng `DEPLOY_USE_SG=1` trước mỗi command deploy để dùng nhóm docker đã được cấu hình. Nếu tái hiện lỗi exec của Snap, đặt `DEPLOY_NO_NEW_PRIVILEGES=false` trong env **local kiểm chứng**; template mặc định true. Không giảm control trên máy chủ khác khi chưa kiểm tra nguyên nhân. Cài Docker theo [hướng dẫn Linux hiện có](SETUP.md); không cấp socket Docker cho container ứng dụng.

## Model và dữ liệu sau cài đặt

[MODEL_MANAGEMENT](MODEL_MANAGEMENT.md) hướng dẫn `model-prepare` hoặc cung cấp cache offline. [DATASET_IMPORT_GUIDE](DATASET_IMPORT_GUIDE.md) có dry-run/import/activation; không rebuild frontend khi thêm dữ liệu. Build `--without-ml` dành empty smoke/CI: để inference cần release mới có ML dependencies, không chỉ bật SEARCH_ENABLED.

## Dừng và khôi phục process

```bash
python3 scripts/deploy.py logs --tail 100
python3 scripts/deploy.py restart
python3 scripts/deploy.py down
python3 scripts/deploy.py up
```

`down` giữ persistent volumes; không có `down --volumes` trong CLI production. Khi startup lỗi, xem service failed trong log và [OPERATIONS_RUNBOOK](OPERATIONS_RUNBOOK.md). Không xóa volumes để làm startup pass.

## HTTPS và thiết bị khác

Đặt `DEPLOY_TLS_PATH` tới thư mục có `tls.crt` (full chain) và `tls.key`; frontend UID phải đọc được key mà không làm key public. Dùng `--tls` cho validate/up/check. [SECURITY_DEPLOYMENT](SECURITY_DEPLOYMENT.md) nêu permissions, CA và ports. Domain/certificate tin cậy, firewall, DNS và remote access vẫn phải được thiết lập tại môi trường thật. Local self-signed test không phải chứng chỉ public.

Để điện thoại/máy khác truy cập, cần bind địa chỉ LAN được phép, hostname/cert phù hợp và firewall cho ingress. Không dùng các hostname postgres/qdrant/minio trong trình duyệt. Giao diện là web; Linux headless/viewport emulation đã kiểm tra, không có ứng dụng native Android/iOS hoặc bằng chứng thiết bị vật lý.
