# Thư viện chung cho thành viên — 19/11/2026

Đã triển khai quyền tự động đọc thư viện chung cho mọi tài khoản đã đăng nhập, gồm User vừa tự đăng ký. Admin bật **Chia sẻ cho mọi thành viên** trong **Quản trị → Thư viện** và lưu. Thư viện riêng vẫn dùng grant riêng, khách chưa đăng nhập không được truy cập. Chỉ Admin được thêm/sửa/ẩn ảnh hoặc đổi cấu hình thư viện.

## Chính sách và thay đổi

- Migration `20261119_shared_datasets` thêm `access_datasets.shared_with_members`, mặc định false. Mọi thư viện hiện có giữ nguyên quyền riêng; không tự công khai dữ liệu cũ.
- Truy vấn `accessible_datasets` dùng chung cho snapshot tài khoản và request principal: các thư viện active có cờ chung hợp với grant riêng. Không sao chép grant khi đăng ký, không tạo hàng grant cho từng User.
- Kiểm tra trực tiếp mỗi request giữ phạm vi PostgreSQL, Qdrant, media, evidence RAG và tri thức Agent thống nhất. Bỏ chia sẻ có hiệu lực từ request kế tiếp; grant riêng vẫn còn hiệu lực. Tạm dừng thư viện chặn cả hai loại quyền. Nội dung đã được người có quyền tải về trước đó không thể thu hồi khỏi thiết bị của họ.
- Admin thấy cờ chung khi tạo/sửa và trạng thái chung/riêng ở danh sách. Màn hình thành viên đánh dấu thư viện chung tự động, chỉ lưu các lựa chọn cấp riêng. Chỉnh tên bằng client cũ không vô tình tắt cờ chia sẻ.
- Thêm `POST /admin/users/{id}/sessions/revoke` và nút **Đăng xuất mọi thiết bị**: Admin-only, Origin/CSRF, audit, thu hồi mọi phiên nhưng giữ mật khẩu/role/is_active. Khóa tài khoản để chặn cả đăng nhập lại.
- Giới hạn đăng ký/đăng nhập, tìm kiếm, RAG/Agent hiện có tiếp tục áp dụng; không bổ sung MFA hoặc dịch vụ email trong thay đổi này.

## Kiểm chứng

| Kiểm tra | Kết quả | Bằng chứng |
| --- | --- | --- |
| Frontend unit/component | 72 pass, 18 files; gồm 2 test quản trị mới | [frontend-test.txt](frontend-test.txt) |
| ESLint | Pass | [lint.txt](lint.txt) |
| TypeScript + Vite build | Pass | [build.txt](build.txt) |
| Backend unit/security/reliability | 257 pass | [backend-fast.log](backend-fast.log) |
| PG/Qdrant/MinIO integration | 25 pass; gồm 3 test quyền chung mới | [backend-services.log](backend-services.log) |
| Browser Chromium desktop/mobile/320px, Firefox | 4 pass | [browser.json](browser.json), [browser.txt](browser.txt) |
| Ruff check/format 9 file Python sửa/thêm | Pass | Kiểm tra trực tiếp trước bàn giao |

Integration sử dụng database/bucket/collection QA riêng và vector tổng hợp, kiểm tra: User mới đọc chung không cần grant, private images bị 404, search/filter/evidence và Agent entity không rò dữ liệu riêng, anonymous 401, User không sửa dữ liệu/quyền, thay cờ/active có hiệu lực không đăng nhập lại, grant riêng giữ độc lập và không trùng kết quả, CSRF, audit, thu hồi hai phiên cùng lúc và đăng nhập lại bằng mật khẩu cũ.

Browser [script](check.mjs) chạy API/UI QA thật: Admin bật cờ, đăng ký User mới, đọc ảnh chung 200/ảnh riêng 404/Admin 403, xem quyền tự động, tắt/bật lại có hiệu lực ngay và thu hồi phiên từ màn hình thành viên. Axe ở màn hình cấu hình không violation, không tràn ngang. QA browser không chạy CLIP; search và evidence được kiểm chứng trong integration. Đã xem [quản lý thư viện](libraries-desktop.png); lưu [mobile](libraries-mobile.png), [quản lý phiên](accounts-desktop.png), [trang User mới](member-desktop.png).

## Áp dụng local và dữ liệu

Đã restart backend development để chạy migration và nạp routes: [runtime](local-runtime.json). [Trước](preservation-before.json) và [sau](preservation-after.json): 513 ảnh, 5 tài khoản, 6 grant, 3 thư viện, active index không đổi. Revision lên `20261119_shared_datasets`; số thư viện chung hiện tại bằng 0, chờ Admin chủ động chọn dữ liệu để chia sẻ. Không thêm tài khoản thử hoặc ảnh QA vào database chính.

Không tạo database dump: automatic approval review từ chối việc xuất toàn bộ database vì có thể chứa dữ liệu tài khoản nhạy cảm. Đã dùng phương án không xuất dữ liệu: chỉ đọc số lượng tổng hợp, ID active index và phiên bản schema; migration chỉ thêm cột false. Không còn thao tác bàn giao nào phụ thuộc vào bản dump.

QA riêng được dọn sau kiểm chứng. Code chưa commit. Release production-like 8088 chưa cập nhật.

## Dùng ngay

1. Mở http://localhost:5173 bằng Admin → **Quản trị → Thư viện**.
2. Mở thư viện phù hợp, bật **Chia sẻ cho mọi thành viên**, chọn **Lưu thư viện**.
3. User đăng ký/đăng nhập sẽ được tìm và xem thư viện đó ngay; không cần Admin duyệt từng người.
