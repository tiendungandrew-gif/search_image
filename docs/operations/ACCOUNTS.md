# Sử dụng tài khoản và giao diện mới

Mở http://localhost:5173 cho development, http://127.0.0.1:8088 cho bản chạy Compose production trên máy này. Dùng tài khoản cá nhân. Không đưa API_TOKEN hay key Gemini vào ô mật khẩu.

Development có thêm [đăng nhập nhanh Admin/User](QUICK_LOGIN.md) bằng tài khoản trải nghiệm local.

## Khách chưa đăng nhập

Từ 20/11, trang đầu development mở tìm kiếm văn bản cho khách. Đăng nhập tại
http://localhost:5173/login hoặc bấm **Đăng nhập**. Chọn **Tìm bằng ảnh** khi là
khách cũng mở trang đăng nhập; Guest không được upload ảnh truy vấn, gọi
RAG/Agent hoặc dùng công cụ quản trị.

Vào **Quản trị → Thư viện & hình ảnh**, mở thư viện, bật
**Công khai cho khách (không cần đăng nhập)** rồi **Lưu thư viện**. Mặc định
thư viện mới và dữ liệu cũ đều không công khai. Checkbox **Chia sẻ cho mọi
thành viên** vẫn chỉ cho người đã đăng nhập; không cấp quyền khách. Tắt công
khai thu hồi quyền khách từ yêu cầu tiếp theo, không xóa grant hoặc quyền
chia sẻ cho thành viên. Tạm dừng thư viện chặn cả ba nguồn quyền.

Development đã mở đúng bộ 10 ảnh mẫu `scikit-image-v0.25.2`, sau khi kiểm tra
hash từng ảnh khớp bộ mẫu đã dùng ở trang đăng nhập. Các thư viện khác giữ
nguyên quyền. Không bật public bucket MinIO. Admin có thể bật/tắt từng thư
viện qua UI; không cần reindex.

`GUEST_SEARCH_ENABLED=true`, `GUEST_SEARCH_PER_MINUTE=20`,
`GUEST_MAX_TOP_K=50` là mặc định. Quota dùng địa chỉ peer do server xác định,
lưu counter theo phút trong PostgreSQL, không tin header IP tự khai. Khi qua
reverse proxy chưa cấu hình trust đúng, nhiều khách có thể chung quota của
proxy. Không dùng cấu hình đăng nhập nhanh development trên website công khai.

`GET /api/v1/public/workspace` chỉ đếm/liệt kê thư viện công khai. Search và
media luôn áp dụng phạm vi này, kể cả khi người gọi gửi source/ID riêng. URL
metadata/ảnh riêng trả 404 cho khách; endpoint quản trị vẫn yêu cầu tài khoản.
Migration `20261120_public_datasets` bổ sung quyền công khai, mặc định false.
[Kiểm chứng](../verification/guest_search/REPORT.md).

Thông tin Admin development được lưu riêng tại `.cache/auth/admin-login.json`, quyền 0600; mở file bằng IDE để lấy username/password. File này bị bỏ qua bởi Git và Docker build. Đổi mật khẩu tại trang Tài khoản sau lần đăng nhập đầu; file ban đầu không tự cập nhật sau khi đổi. Admin của bản deployment dùng file `.cache/auth/deployment-admin-login.json` riêng, database riêng.

## Đăng ký tài khoản

Tại trang đăng nhập, chọn **Đăng ký**, nhập tên hiển thị, tên đăng nhập (3–120 ký tự) và mật khẩu (12–128 ký tự), rồi xác nhận mật khẩu. Tên đăng nhập dùng chữ Latin/số và các dấu `. _ @ + -`, được chuẩn hóa về chữ thường. Tên trùng hoặc tên tài khoản trải nghiệm dành riêng sẽ bị từ chối.

Đăng ký thành công đưa về form đăng nhập và điền sẵn tên tài khoản; không tự tạo phiên. Đăng nhập bằng mật khẩu vừa chọn để vào ứng dụng. Tài khoản mới có vai trò **User**, hoạt động ngay không cần duyệt, tự có quyền tìm/xem thư viện công khai và các thư viện được chia sẻ chung cho thành viên. Thư viện riêng do Admin cấp tại **Tài khoản → thư viện được cấp**. Nếu chưa có thư viện công khai, thư viện chung hoặc quyền cấp riêng, danh sách thư viện sẽ trống. Không cần nhập email; khôi phục mật khẩu vẫn qua Admin.

API `POST /api/v1/auth/register` nhận `{display_name,username,password}`, trả HTTP 201 `{status:"registered"}`. Chỉ nhận các trường trên, không nhận role/grants; kiểm tra Origin và giới hạn lượt thử như đăng nhập. Mật khẩu dùng salted scrypt và tên đăng nhập unique trong database; trường hợp hai yêu cầu cùng tên đồng thời chỉ tạo một tài khoản. Đăng ký không cần migration riêng; chính sách thư viện chung dùng migration `20261119_shared_datasets`.

[Kết quả kiểm chứng đăng ký](../verification/registration/REPORT.md).

## Chuẩn bị từ checkout mới

```bash
python3 scripts/init_env.py
docker compose up -d --build
# Nếu startup chưa migration:
docker compose exec -T backend python -m alembic -c backend/alembic.ini upgrade head
python3 scripts/administration/accounts.py bootstrap --env-file .env --output .cache/auth/admin-login.json
# Worker xử lý nhập/sửa ảnh và lập chỉ mục:
docker compose --profile indexing up -d --build indexing-worker
```

Bootstrap chỉ tạo Admin khi chưa có Admin hoạt động. Chạy lại không đổi mật khẩu tài khoản hiện tại; output đã tồn tại được giữ nguyên. Trên máy dùng Docker Snap nhưng shell chưa nhận nhóm docker, dùng `sg docker -c 'docker compose ...'` cho các lệnh Docker; đặt `ACCOUNTS_USE_SG=1` trước lệnh helper tài khoản.

Với deployment đã khởi tạo:

```bash
python3 scripts/administration/accounts.py bootstrap --env-file config/environments/deployment.env --output .cache/auth/deployment-admin-login.json
```

Admin vào **Quản trị → Thư viện** để tạo hoặc đặt tên thư viện đã có. Vào **Tài khoản → Tạo tài khoản mới**, chọn Thành viên và mật khẩu ít nhất 12 ký tự, sau đó mở tài khoản để chọn các thư viện được cấp. User mới không cần grant riêng để đọc thư viện chung. Tạm dừng thư viện chặn cả quyền chung và quyền riêng. Bỏ chia sẻ chung giữ lại các grant riêng đã có; để thu hồi hoàn toàn, kiểm tra cả hai nguồn quyền. Backend cập nhật phạm vi từ yêu cầu kế tiếp.

## Thư viện chung và quản lý phiên

Vào **Quản trị → Thư viện**, mở thư viện muốn chia sẻ, bật **Chia sẻ cho mọi thành viên**, rồi chọn **Lưu thư viện**. Tùy chọn này cũng có khi tạo thư viện. Mọi User đang hoạt động, kể cả tài khoản mới, tự có quyền tìm và xem ảnh; không có quyền thêm/sửa/ẩn ảnh hoặc quản trị. Lựa chọn chia sẻ thành viên không cấp quyền khách; khách chỉ xem được nếu bật quyền công khai riêng. Thư viện mới và thư viện hiện có sau migration mặc định không chia sẻ; không tự công khai dữ liệu cũ.

Tại **Quản trị → Tài khoản**, thư viện chung hiện được đánh dấu tự động và không sửa riêng cho từng User. Các checkbox còn lại là quyền cấp riêng. Bỏ chia sẻ ở thư viện không xóa grant riêng; grant riêng được quản lý độc lập.

Nút **Đăng xuất mọi thiết bị** kết thúc mọi phiên của tài khoản, không đổi mật khẩu và không khóa tài khoản. Dùng **Cho phép đăng nhập** để khóa/mở khóa; khóa tài khoản sẽ thu hồi phiên và chặn đăng nhập lại. Các thao tác chia sẻ và thu hồi phiên được lưu trong **Nhật ký**.

Giới hạn sử dụng tiếp tục theo cấu hình `AUTH_LOGIN_ATTEMPTS_PER_MINUTE`, `USER_SEARCH_PER_MINUTE`, `USER_RAG_PER_DAY`, `USER_AGENT_PER_DAY`. User tự đăng ký không bỏ qua các hạn mức hoặc được nâng vai trò. [Kiểm chứng](../verification/shared_members/REPORT.md).

## Quản lý dữ liệu

- **Thư viện:** nhập ảnh JPEG/PNG/WebP tối đa 20 MB, khai báo giấy phép và nguồn/quyền sử dụng. Theo dõi job ở **Chỉ mục**. Nếu hệ thống chưa có model/index, chuẩn bị theo [nhập ảnh](../features/IMAGE_INDEXING.md) trước.
- **Sửa thông tin ảnh:** đổi tiêu đề/mô tả/thẻ/thư viện; worker cập nhật chỉ mục rồi ảnh mới trở lại kết quả. Cần worker đang chạy.
- **Ẩn khỏi tìm kiếm / Khôi phục:** thao tác đảo ngược được, giữ ảnh gốc. Không phải xóa vĩnh viễn.
- **Chỉ mục:** tạo version mới dùng model đã đăng ký, lập chỉ mục thư viện, làm mới theo dõi tác vụ, kiểm tra đạt rồi đưa vào sử dụng. Cần cùng model manifest runtime; thay model khác dùng CLI và restart theo tài liệu vận hành.
- **Tri thức:** chọn thư viện, tải/dán gói JSON đúng schema, kiểm tra rồi nhập. Các liên kết ảnh phải thuộc thư viện đó. Không tự biến caption hay phỏng đoán của LLM thành quan hệ đã xác minh.
- **Đánh giá / Nhật ký:** dành cho Admin. Nhãn chất lượng tìm kiếm và RAG vẫn chờ người đánh giá như trước.

## Khôi phục mật khẩu

Admin có thể đặt lại mật khẩu thành viên tại **Tài khoản**; thao tác kết thúc các phiên cũ. Nếu quên mật khẩu Admin, operator có quyền terminal của máy chủ dùng:

```bash
python3 scripts/administration/accounts.py reset --env-file .env --username admin --output .cache/auth/admin-reset-login.json
```

Helper sinh mật khẩu mới ngẫu nhiên, truyền qua stdin, lưu vào file riêng 0600; không truyền password qua command line. Với deployment thay `--env-file` tương ứng và dùng tên output khác. Reset không tự mở khóa hoặc nâng vai trò. Giữ ít nhất một Admin hoạt động; không chia sẻ tài khoản Admin cho người tìm ảnh.

## Kiểm tra và triển khai

```bash
QA_USE_SG=1 python3 scripts/qa.py services
python3 scripts/checks/check_access_browser.py --indexed
```

Browser suite dùng tài khoản QA riêng `.cache/auth/qa-admin-login.json`, tạo tài khoản kiểm thử chỉ trong database QA. Không chạy suite này vào thư viện chính. Kiểm tra deployment chỉ đọc có helper `scripts/checks/check_deployment_browser.py --env-file config/environments/deployment.env --indexed --login-file .cache/auth/deployment-admin-login.json`.

Dùng public host cần TLS, CORS_ORIGINS chính xác với HTTPS, `AUTH_COOKIE_SECURE=true`. Frontend/API nên cùng origin qua Nginx. Không publish database, Qdrant hay MinIO. Production trên máy localhost đang dùng HTTP phục vụ kiểm tra cục bộ; chưa được đưa lên public hosting.

Thiết kế quyền/API/giới hạn: [ACCESS_CONTROL](../architecture/ACCESS_CONTROL.md). Kết quả kiểm chứng: [REPORT](../verification/access_control/REPORT.md).
