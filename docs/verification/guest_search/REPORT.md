# Tìm kiếm cho khách — 20/11/2026

Đã bật tại http://localhost:5173. Trang đầu cho phép tìm bằng tiếng Việt có dấu,
không dấu và English trong thư viện công khai; không tự đăng nhập tài khoản demo.
Chọn tìm bằng ảnh mở trang đăng nhập. Không có quyền guest cho upload, RAG/Agent,
quản trị, thư viện chỉ chia sẻ thành viên hoặc thư viện cấp riêng.

`AccessDataset.is_public` tách khỏi `shared_with_members`, mặc định false khi
migrate và khi tạo mới. User đã đăng nhập đọc hợp của công khai/chung/grant riêng;
khách chỉ nhận phạm vi public đang hoạt động. Qdrant lọc trước, PostgreSQL/media
kiểm tra lại quyền và moderation. Quyền công khai được đọc mỗi request, không
cache kết quả theo câu tìm; cache vector không chứa quyền/kết quả ảnh.

## Dữ liệu và cấu hình

Chỉ bộ 10 ảnh mẫu đã dùng trên trang đăng nhập được mở, đối chiếu SHA256 từng
ảnh qua API trước khi bật. [Receipt](public-sample.json). Thư viện còn lại giữ
nguyên quyền. Ảnh/metadata riêng không trả cho khách qua UUID trực tiếp hoặc
bộ lọc source. MinIO vẫn private; search, metadata và media trả `private, no-store`.

Trước/sau: 513 ảnh, 5 users, 6 grants, 3 libraries; sau có 1 thư viện public.
Index giữ `b4597021-4b91-491d-99ae-0617a6ca389c`. Không nhập lại ảnh hoặc reindex.
Migration `20261120_public_datasets` chỉ thêm cột false; bật mẫu qua Admin API
có audit. Script chuẩn bị là `scripts/runtime/publish_sample_library.py`.

Khách mặc định tối đa 12 kết quả/lượt, 20 lượt tìm/phút theo địa chỉ peer server;
counter PostgreSQL atomic, không tạo User/AuthSession, không tin X-Forwarded-For
tự gửi. Chặn multipart/reference image và chức năng nâng cao trước inference.
POST guest yêu cầu Origin hợp lệ; POST có session vẫn phải có CSRF token như cũ.

## Kiểm chứng

| Kiểm tra | Kết quả |
| --- | --- |
| Backend unit/security/reliability | 275 pass |
| Integration PG/Qdrant/MinIO | 27 pass, gồm 2 ca guest với nhiều assertion |
| Frontend unit | 78 pass / 19 files |
| Build, ESLint, Ruff, diff check | Pass |
| Bộ browser đầy đủ trên 4 projects | 12 pass, 0 fail/skip/flaky; [log](browser-all.txt), [JSON](browser-all.json) |
| Guest: cuộn tải toàn bộ ảnh và chụp trang | 4 pass bổ sung; [log](browser-guest-all.txt) |
| API development thực | [Pass](api.json): ảnh mèo khớp hash, private metadata/original/thumbnail 404, Admin/RAG/Agent 401 |

Integration dùng database/bucket/collection QA riêng và vector tổng hợp; kiểm
tra public khác member-sharing, thay đổi công khai không xóa grant/chia sẻ,
thu hồi/deactivate có hiệu lực ở request tiếp theo, quota/reset bucket, spoof IP,
Origin, bearer sai, Top-K, multipart và tắt guest feature. Migration/schema và
rollback cũng đạt trên DB QA. QA đã dọn, không đụng volume development.

Browser dùng model/API/dữ liệu development thật. Guest tìm `con meo` và `a cat`
đưa mèo mẫu lên đầu; không có session cookie, không hiện thư viện riêng. Mở ảnh,
đổi lưới, reduced motion, đăng nhập User/Admin, CSRF và phân quyền cũ vẫn hoạt động.
Axe không có violation ở các trạng thái được kiểm tra; không tràn ngang.
Đã xem ảnh chụp [desktop](guest-desktop.png), [mobile](guest-mobile.png),
[320px](guest-narrow.png), [Firefox](guest-firefox.png). Đây là browser emulation,
không phải thử điện thoại vật lý, benchmark tải công khai hay đánh giá relevance rộng.

Lượt đầu có lỗi môi trường QA chưa chạy, kỳ vọng 401 cũ được đổi thành 404 cho
ảnh riêng khi guest feature bật. Các kỳ vọng login tại trang đầu/logout được cập nhật thành landing khách. Hai test registration bị timeout dưới tải khi
chạy song song; chạy riêng và chạy full một worker đạt, không sửa timeout runtime.
Các log lỗi ban đầu giữ ở `docs/verification/phase11/runs/`.

```bash
QA_USE_SG=1 python3 scripts/qa.py fast
QA_USE_SG=1 python3 scripts/qa.py services
backend/.venv/bin/python scripts/checks/check_guest_api.py
backend/.venv/bin/python scripts/checks/check_consumer_browser.py
backend/.venv/bin/python scripts/checks/check_consumer_browser.py --spec guest
```

Chưa commit. Bản production-like 8088 không cập nhật trong thay đổi này.
