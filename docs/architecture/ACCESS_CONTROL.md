# Tài khoản, vai trò và quyền thư viện

Cập nhật 20/11: khách có thể tìm văn bản và xem ảnh trong thư viện có
`is_public=true` và đang hoạt động. Đây là quyền độc lập với
`shared_with_members`. [Hướng dẫn khách và cấu hình](../operations/ACCOUNTS.md).

Cập nhật 20/11/2026. Khách tìm được ảnh công khai; chức năng thành viên dùng tài khoản cá nhân. Người dùng có thể tự đăng ký tài khoản User; Admin vẫn tạo/quản lý tài khoản và cấp thư viện. Tự đăng ký luôn tạo User hoạt động ngay; tự đọc thư viện công khai/chung đang hoạt động, ngoài các grant riêng được Admin cấp. Không tự có quyền Admin. Thay thế cách nhập token vận hành vào giao diện thông thường.

## Ma trận quyền

| Chức năng | Chưa đăng nhập | User | Admin |
| --- | --- | --- | --- |
| Đăng ký User (chưa có grant) | Có | Có | Có |
| Đăng nhập, health/live | Có | Có | Có |
| Tìm bằng văn bản | Chỉ thư viện công khai, có quota | Công khai, chung hoặc được cấp riêng | Tất cả thư viện |
| Tìm bằng ảnh, đa ý định, đa phương thức | Không | Công khai, chung hoặc được cấp riêng | Tất cả thư viện |
| Xem ảnh gốc, thumbnail, metadata | Công khai, đang hoạt động, ảnh không bị ẩn | Công khai, chung hoặc được cấp riêng, ảnh không bị ẩn | Ảnh không bị ẩn |
| Giải thích RAG, tìm kiếm Agent | Không | Cùng phạm vi thư viện, có hạn mức | Tất cả, khi tính năng đã cấu hình |
| Thay mật khẩu của mình, đăng xuất | Không | Có | Có |
| Tạo/khóa tài khoản, đổi vai trò, đặt lại mật khẩu | Không | Không | Có |
| Cấp/thu hồi thư viện, tạm dừng thư viện | Không | Không | Có |
| Nhập ảnh, sửa metadata, ẩn/khôi phục ảnh | Không | Không | Có |
| Tạo, lập, kiểm tra, kích hoạt chỉ mục | Không | Không | Có, model đã đăng ký |
| Nhập tri thức có trích nguồn | Không | Không | Có, chọn thư viện rõ ràng |
| Chẩn đoán, benchmark, nhật ký | Không | Không | Có |
| Docker, backup/restore, cấu hình secrets, tải model mới | Không | Không | Qua công cụ vận hành trên máy chủ |

Admin hoạt động trên toàn hệ thống; không dùng vai trò này cho người chỉ cần tìm ảnh. User mới chỉ tự đọc thư viện công khai/chung đang hoạt động; không được cấp ngầm grant riêng. Không được khóa hoặc hạ quyền Admin hoạt động cuối cùng. Nhập ảnh truy vấn chỉ dùng để tìm kiếm, không tự thêm vào corpus.

## Phiên và mật khẩu

- Mật khẩu tối thiểu 12, tối đa 128 ký tự khi tạo/đặt lại; scrypt N=131072, r=8, p=1, salt ngẫu nhiên 16 byte. Không trả hash trong API, không ghi mật khẩu vào audit.
- Session token ngẫu nhiên, database chỉ lưu SHA-256; cookie HttpOnly, SameSite=Strict, Path=/, mặc định 12 giờ. Đăng xuất thu hồi phiên hiện tại. Đổi mật khẩu, Admin reset, khóa hoặc đổi vai trò thu hồi các phiên liên quan.
- Khi `AUTH_COOKIE_SECURE=true`, cookie dùng tiền tố `__Host-` và Secure. Public origin bắt buộc HTTPS và Secure. Chỉ dùng HTTP cookie trên localhost/127.0.0.1 khi phát triển.
- Yêu cầu thay đổi dữ liệu và POST tìm kiếm có session dùng Origin trong allowlist + `X-CSRF-Token` khớp hash thuộc phiên. Guest POST chỉ dùng Origin allowlist và quota, vì không tạo session/CSRF cookie. CSRF cookie có thể đọc bởi frontend; session cookie không thể đọc bằng JavaScript. Trình duyệt gọi API cùng origin qua Vite/Nginx proxy.
- Login giới hạn mặc định 10 lần/phút theo username, 30 lần/phút theo IP. Chỉ tin IP của reverse proxy đã cấu hình; không lấy trực tiếp X-Forwarded-For tùy ý trong logic throttle. Chạy một API process theo cấu hình Compose hiện tại.
- User mặc định 60 lượt tìm/phút, 20 lượt RAG/ngày, 20 lượt Agent/ngày (UTC); 0 khóa tính năng tương ứng đối với User. Hạn mức được cập nhật nguyên tử trong PostgreSQL; Admin không áp dụng hạn mức User.

## Cô lập dữ liệu

`access_datasets.key` ánh xạ `image_metadata.source_dataset`; `__unassigned__` ánh xạ giá trị NULL. Migration backfill catalog theo dữ liệu sẵn có, không đổi source_dataset, metadata_revision, image checksum hoặc vector manifest. `dataset_grants` gắn User với thư viện đang hoạt động.

API kiểm tra danh tính và quyền ở mỗi yêu cầu. Request-local Principal đi cùng các tác vụ async qua ContextVar và được reset khi kết thúc request. CLI nội bộ không có Principal là ngữ cảnh vận hành tin cậy; không được đưa một API mới vào HTTP mà bỏ dependency xác thực.

Qdrant áp bộ lọc thư viện trước truy xuất. PostgreSQL tiếp tục kiểm tra quyền, trạng thái ảnh, phiên bản metadata và receipt trước khi xuất kết quả; payload vector cũ không thể tự cấp quyền. Đường xem ảnh trực tiếp trả 404 cho ID ngoài quyền. Không phát presigned URL hoặc public bucket. RAG chỉ lấy evidence từ các ảnh được phép. Agent lookup/quan hệ/liên kết ảnh kiểm tra bảng `entity_datasets` và `relation_datasets`, cùng quyền ảnh. Tri thức nhập qua giao diện được gắn thư viện trong cùng transaction nhập; liên kết ảnh phải thuộc thư viện đã chọn.

Phạm vi thành viên bằng hợp thư viện công khai/chung/grant riêng đang hoạt động, dùng cùng truy vấn `accessible_datasets` cho snapshot và request principal. Guest dùng `public_datasets`, chỉ lấy public đang hoạt động. Cột `access_datasets.shared_with_members` mặc định false; migration `20261119_shared_datasets` không mở quyền dữ liệu cũ. Không ghi hàng grant tự động, nên bỏ chia sẻ có hiệu lực mà không phải dọn quyền sao chép. Không áp dụng cho anonymous.

Grant được đọc lại mỗi request nên thu hồi không cần đăng xuất. Frontend làm mới danh tính khi lấy lại focus; thay đổi tài khoản/role/grants sẽ bỏ workspace cũ. Những byte ảnh hoặc câu trả lời đã được người có quyền tải xuống trước khi thu hồi không thể xóa từ thiết bị của họ. Request đã xác thực trước thời điểm thu hồi dùng snapshot quyền của request đó.

Ẩn ảnh dùng `image_moderation`, có thể khôi phục; không xóa object gốc. Sửa metadata tăng revision và tạo job trên active index. Ảnh tạm không đủ điều kiện tìm kiếm cho đến khi worker cập nhật payload và receipt. Worker daemon chỉ chọn index building/ready khớp manifest model đã cài, bỏ qua lease/retry chưa đến hạn và tạm hoãn index gặp lỗi để tiếp tục tác vụ khác; thông tin index cố định trong env không giới hạn tác vụ tạo từ Admin nữa.

## Bảng bổ sung

`users`, `auth_sessions`, `access_datasets`, `dataset_grants`, `entity_datasets`, `relation_datasets`, `image_moderation`, `auth_usage`, `login_throttles`, `audit_events`. Migration: `20261108_access_control`, sau `20261106_agent_knowledge`. Có khóa ngoại/cascade, unique username/key và check role. Không xóa bảng nghiệp vụ cũ.

Session hết hạn được dọn khi tạo phiên mới. Auth usage và throttle cần chính sách giữ liệu khi vận hành dài hạn; có thể dọn bucket usage quá 30 ngày và throttle quá 1 ngày bằng tác vụ PostgreSQL định kỳ. Audit nên được lưu/archival theo yêu cầu tổ chức; chưa có UI xóa audit. Không triển khai MFA/SSO hoặc gửi email khôi phục trong phạm vi này.

## API

Prefix `/api/v1`. Định dạng đầu vào chi tiết và trường giới hạn có trong Pydantic schemas và `/openapi.json`; lỗi theo ErrorEnvelope chung. UUID không hợp lệ trả 422. Mọi `/admin/*` bắt buộc Admin, kể cả GET.

| Đường dẫn | Phương thức | Payload/kết quả chính |
| --- | --- | --- |
| `/auth/me` | GET | `{user: null hoặc {id, username, display_name, role, is_active, datasets: [{id,key,name}]}, legacy_enabled}` |
| `/auth/register` | POST | `{display_name,username,password}` → 201 `{status:"registered"}`; Origin/throttle; không tạo phiên, role luôn User và không grant |
| `/auth/login` | POST | `{username,password}` → snapshot + cookies |
| `/auth/logout` | POST | Thu hồi phiên, xóa cookies |
| `/auth/password` | POST | `{current_password,password}` → `sign_in_again` |
| `/admin/users` | GET/POST | Phân trang `offset,limit`; tạo `{username,display_name,password,role}` |
| `/admin/users/{id}` | PATCH | `{display_name?,role?,is_active?}` |
| `/admin/users/{id}/sessions/revoke` | POST | Thu hồi mọi session, giữ nguyên mật khẩu/role/is_active; Admin-only, CSRF và audit |
| `/admin/users/{id}/password` | POST | `{password}`; thu hồi tất cả phiên của tài khoản |
| `/admin/users/{id}/datasets` | PUT | `{dataset_ids:[UUID]}` thay toàn bộ grant |
| `/admin/datasets` | GET/POST | Catalog có số ảnh; tạo `{key,name,description?}` |
| `/admin/datasets/{id}` | PATCH | `{name,description?,is_active}` |
| `/admin/images` | GET | `dataset_id?,offset,limit` → `{total,images:[...]}` |
| `/admin/images/upload` | POST | Multipart `image,dataset_id,metadata`; header Idempotency-Key; metadata gồm title/caption/tags/license/rights_ref |
| `/admin/images/{id}` | PATCH/DELETE | PATCH `{title,caption,tags,dataset_id}` → job_id; DELETE ẩn ảnh |
| `/admin/images/{id}/restore` | POST | Khôi phục ảnh đã ẩn |
| `/admin/indexes` | GET/POST | Danh sách index + 30 job; tạo `{model_id,version}` |
| `/admin/indexes/reindex` | POST | `{target_index_id,dataset_id?}`; tối đa 5000 ảnh/lượt web |
| `/admin/indexes/verify` | POST | `{index_id}` → báo cáo nhất quán; pass đánh dấu ready |
| `/admin/indexes/activate` | POST | `{index_id}`; cùng manifest runtime, ready, không job đang chạy → generation |
| `/admin/jobs/{id}` | GET | Tiến độ và lỗi từng item |
| `/admin/knowledge` | POST | `{dataset_id,apply,knowledge}`; kiểm tra trước với apply=false, tối đa 1 MiB |
| `/admin/audit` | GET | `offset,limit` → actor/action/resource/date/details đã chọn |

Các API upload/index cũ vẫn cần Admin; Nginx production giữ chặn các đường vận hành cũ. Giao diện Admin dùng `/admin/*`. Kích hoạt index online được thiết kế cho cấu hình một API process hiện tại; khi mở rộng nhiều replica cần cơ chế reload/publish generation cho từng replica. Các request đang xử lý giữ registry snapshot; không sửa manifest model đang dùng.

## Token vận hành tương thích

`AUTH_LEGACY_TOKENS_ENABLED=false` mặc định. API_TOKEN/WRITE_API_TOKEN không đăng nhập thay tài khoản trong chế độ này. API_TOKEN vẫn dùng riêng cho health ready/search probes để giám sát không phải có web session. Không cấp health key cho người dùng.

Bật legacy chỉ cho công cụ kiểm thử/cũ trong môi trường tin cậy: API_TOKEN có quyền đọc mọi thư viện và chẩn đoán; WRITE_API_TOKEN có quyền Admin. `/operator` chỉ mở khi backend báo legacy_enabled=true. QA bật rõ ràng để giữ kiểm thử lịch sử. Không bật cho deployment người dùng mặc định.

Thiết kế dựa trên [OWASP Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html), [Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html), [Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html) và [CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html). Báo cáo thực chạy: [nghiệm thu](../verification/access_control/REPORT.md).

## Đăng nhập nhanh local

[Tài khoản trải nghiệm](../operations/QUICK_LOGIN.md) là tính năng opt-in cho development/test; production vẫn dùng mật khẩu. `users.is_demo` tách tài khoản demo khỏi tài khoản cá nhân. Session demo bị chặn khi tắt tính năng, User vẫn áp ACL, còn kiểm tra last Admin chỉ đếm Admin cá nhân. Xem [nghiệm thu](../verification/quick_login/REPORT.md).
