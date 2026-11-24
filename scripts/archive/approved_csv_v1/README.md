# Công cụ nhập liệu approved CSV — lịch sử

Bốn helper Python được giữ để đối chiếu quy trình bulk import trước đây, thay vì đặt lẫn trong thư mục dữ liệu local. Đây không phải worker phục vụ chính; worker hiện hành là `python -m app.cli.worker`.

Các helper phụ thuộc backend, local dataset, model cache và phiên bản source thời điểm import. `fast_worker.py` đặt biến môi trường và monkey-patch worker khi chạy, nên không import hoặc chạy chỉ để kiểm tra. File local gốc trong `datasets/approved_csv_v1/` được giữ nguyên để không thay đường dẫn của tiến trình đã có.

Muốn nhập bộ mới, dùng [dataset import guide](../../../docs/operations/DATASET_IMPORT_GUIDE.md). Không áp dụng scheduler lịch sử cho production hiện hành nếu chưa kiểm chứng riêng.
