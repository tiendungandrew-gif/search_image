# Bảo mật triển khai

## Boundary đang áp dụng

Chỉ frontend ingress publish port; PostgreSQL/Qdrant/MinIO không có host ports. Data network internal; API/worker có egress để dùng provider khi cấu hình. Frontend static không chứa read/write/storage/provider keys. UI giữ read token theo session memory, private media qua same-origin authenticated proxy; không public bucket hoặc presigned bearer URL.

API/worker chạy UID10001, frontend UID101; root filesystem read-only và temporary paths writable riêng. Capabilities của ba application containers bị drop. Default no-new-privileges=true; Docker Snap máy kiểm chứng cần compatibility=false vì exec bị kernel/runtime từ chối. Sự khác biệt này được lưu ở [DEPLOYMENT_AUDIT](../archive/DEPLOYMENT_AUDIT.md). Cần kiểm tra control này trên host thực trước khi mở public.

Env sinh0600, không overwrite env serving. `.env*`, caches và backups bị loại khỏi Git/build context; source/provenance archives loại private env. Các operation logs scrub giá trị secrets, request logger có allowlist; không chạy `docker compose config` ra console chứa credentials, dùng `deploy.py validate`.

## HTTP/API

Nginx phục vụ Vite dist, deep-link fallback, dynamic Docker DNS, proxy buffering off cho SSE, không tự retry POST, bounded body/timeouts. [Nginx proxy documentation](https://nginx.org/en/docs/http/ngx_http_proxy_module.html) phân biệt read timeout giữa các lần đọc và deadline toàn request ở backend. Headers có CSP/frame deny/nosniff/referrer/permissions policy. Admin image/index mutations bị chặn ở public ingress; operator dùng CLI qua Docker access có kiểm soát. Backend vẫn kiểm read/write scopes, schema và idempotency.

Uploads decode nội dung thật, allowlist JPEG/PNG/WebP, byte/pixel/side/decode limits, safe generated object keys; không tin MIME/extension. Agent chỉ typed allowlisted tools, bounded hops/calls/deadline; không shell/SQL tùy ý. Retrieved captions và relations không có quyền override system instructions. [SECURITY_AUDIT Phase11](../archive/SECURITY_AUDIT.md) lưu các payload/regressions và giới hạn của injection testing.

## TLS public

`compose.tls.yaml` mount `infra/nginx/tls.conf`, cert directory chứa tls.crt/full chain và tls.key. Nginx hỗ trợ TLS1.2/1.3; HTTP redirect ngoài healthz. Key cần0600 và owner/group phù hợp UID101 đọc được; không chmod key world-readable. Operator quản lý certificate renewal, chain, SAN, expiry và reload/recreate frontend. Với local test CA, DEPLOY_TLS_CA_FILE chỉ định CA tin cậy cho CLI check; không dùng verify=false.

```bash
python3 scripts/deploy.py --tls validate
python3 scripts/deploy.py --tls up
python3 scripts/deploy.py --tls check
```

DEPLOY_TLS_PATH phải tồn tại, DEPLOY_HTTPS_PORT mặc định8443. Public hostname/CORS_ORIGINS/DEPLOY_CHECK_URL phải đúng domain HTTPS; bind mặc định loopback. Nếu bind ngoài loopback, CLI yêu cầu host được khai báo và --tls. Firewall/DNS/80→8080,443→8443 hoặc host-port mapping do nơi chạy quyết định. Không cấu hình domain/cert public giả. Certificate tự ký trong test chỉ xác minh transport/config local, không chứng minh trình duyệt ngoài mạng tin cậy chứng chỉ.

## Những việc cần đóng trước external production

Local Compose hiện dùng credentials PostgreSQL/MinIO cấp quản trị cho các application services, chưa tách DB/S3 least-privilege roles/policies. Các data connections nội bộ chưa TLS. Không có multi-tenant RBAC, edge quota/rate limiting, off-host encrypted backups, full CVE/container scan hoặc pentest được nghiệm thu. Docker socket access có quyền mạnh; không mount socket vào ứng dụng hoặc giao cho user web.

Các mục này là deployment risks cần xử lý theo hosting/exposure thực. Không gọi local compatibility mode, self-signed TLS, npm audit hoặc unit tests là production security certification. Không đưa write token cho người chỉ cần tìm kiếm và không gọi provider-configured là provider SLA healthy.
