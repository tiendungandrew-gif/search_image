# Giao diện khi chưa có dữ liệu

Trạng thái dữ liệu được lấy từ `GET /api/v1/system/workspace` có xác thực. UI không dựa trên một truy vấn trả 0 ảnh hoặc một lỗi kết nối để kết luận database rỗng.

| Dataset state | Ý nghĩa và hành động |
|---|---|
| `empty_dataset` | PostgreSQL chưa có image live; không có receipt/vector mâu thuẫn được quan sát. Hiển thị hướng dẫn nhập dữ liệu; khóa tìm kiếm |
| `index_building` | Có dữ liệu, index building/validating; chờ worker, refresh/poll |
| `index_not_ready` | Có dữ liệu nhưng thiếu active index, receipt/vector hoặc runtime model/index không khớp; kiểm tra model/index |
| `ready` | Hạ tầng, runtime và active index đủ điều kiện; bật từng capability được cấu hình |
| `unavailable` | Dependency/snapshot lỗi hoặc count chưa đọc được; hiển thị chưa xác định, không hiển thị count giả bằng 0 |
| Query `EMPTY` | Dataset có thể vẫn ready; nới filters/đổi truy vấn, không hướng người dùng nhập lại dataset |

Trước khi nhập token: shell, form, chọn ảnh local, navigation và theme vẫn dùng được; dataset hiển thị chưa xác minh. RAG/Agent tắt thì controls không nhận request tương ứng; thiếu provider không xóa chức năng xem ảnh. Missing relation của Agent là thiếu bằng chứng, không phải database ảnh rỗng. Quota provider có thông báo riêng.

## Khi bổ sung dữ liệu

1. Thực hiện ingestion/indexing và activation bằng quy trình đã có trong [IMAGE_INDEXING.md](IMAGE_INDEXING.md) và README. Ảnh query upload ở UI không thay thế bước ingestion.
2. Kiểm tra health/readiness, active model/index và các receipt.
3. Nhấn “Làm mới dataset” hoặc chờ polling 30 s ở tab hiện. App dùng snapshot mới, không sửa source/hardcode số ảnh.

## Kiểm chứng dữ liệu rỗng thật

`scripts/archive/phase10_empty_server.py` là fixture kiểm thử, tạo database PostgreSQL tên ngẫu nhiên `phase10_empty_*`, bucket private riêng và collection Qdrant 512 chiều riêng. Không xóa hay chuyển active index của corpus live. Schema tạo từ metadata hiện tại; migration thật được kiểm tra riêng bởi integration suite.

Fixture xác nhận collection có 0 điểm, bucket có 0 object; workspace xác nhận DB 0 ảnh, 0 indexed receipt, dependencies healthy, mọi search capability false, RAG/Agent tắt. Backend test ở cổng 8001 và frontend proxy riêng ở 5174. Browser tests `phase10-empty.spec.ts` chạy desktop/mobile, đọc API thật, không mock. Trang evaluation thật không có artifact, không render bảng/metric giả. Tài nguyên tạm được dọn khi server dừng.

Khởi động từ repo đã có Compose stack:

```bash
docker compose run --rm -d --no-deps --name phase10-empty \
  -p 127.0.0.1:8001:8001 \
  -v "$PWD/scripts/archive/phase10_empty_server.py:/srv/scripts/archive/phase10_empty_server.py:ro" \
  backend python /srv/scripts/archive/phase10_empty_server.py
docker compose run --rm -d --no-deps --name phase10-empty-frontend \
  -p 127.0.0.1:5174:5173 \
  -e VITE_PROXY_TARGET=http://phase10-empty:8001 frontend
backend/.venv/bin/python scripts/checks/check_frontend.py --project=empty-desktop --project=empty-mobile
docker stop phase10-empty-frontend phase10-empty
```

Chỉ chạy fixture khi tài khoản DB có quyền tạo database tạm trong môi trường phát triển. Cleanup chỉ áp dụng ID tài nguyên fixture tự tạo; không dùng lệnh xóa volume. Ca chuyển empty→ready không sửa source được kiểm tra thêm bằng mock riêng để điều khiển trạng thái nhập dữ liệu; không gộp ca đó với bằng chứng empty backend thật.
