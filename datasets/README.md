# Dữ liệu ảnh và catalog

Repository giữ hướng dẫn, manifest và catalog nhỏ; ảnh thật, nguồn CSV/metadata hàng loạt, receipts, logs và trạng thái nhập liệu được lưu local hoặc trong hệ thống backup có quyền truy cập phù hợp.

| Đường dẫn | Nội dung | Theo dõi bằng Git |
| --- | --- | --- |
| `catalogs/approved_csv_v1.json` | Snapshot tổng hợp lần nhập corpus địa điểm/công trình/dịch vụ Việt Nam | Có |
| `sample_manifest.json` | Nguồn, checksum và rights reference của 10 ảnh mẫu scikit-image | Có |
| `sample/` | File ảnh mẫu tải theo manifest | Không |
| `coco_phase08_*/` | COCO images, captions và artifacts tải/nhập | Không |
| `landmarks_phase09_*/` | Ảnh NPS, metadata và artifacts local | Không |
| `approved_csv_v1/` | Corpus CSV đã nhập, ảnh/receipts/logs và trạng thái xử lý | Không |

## Corpus approved CSV

[Catalog](catalogs/approved_csv_v1.json) ghi snapshot ngày 22/11/2026: 27.029 dòng CSV, 182 nhãn nguồn và 24.023 ảnh sau nhập/dedup. Nội dung đa chủ đề về địa điểm, kiến trúc, lưu trú, ăn uống, hạ tầng và cơ sở sản xuất/dịch vụ tại Việt Nam. Đây không phải số đếm database thời gian thực.

Dữ liệu local vẫn giữ ở `datasets/approved_csv_v1/`; thay đổi tổ chức repository không xóa ảnh hoặc sửa database/index đang phục vụ. Helpers nhập liệu lịch sử được lưu tại [scripts/archive/approved_csv_v1](../scripts/archive/approved_csv_v1/README.md).

**Clone mới không kèm corpus này.** Cần khôi phục dữ liệu từ bản backup được cấp quyền theo [backup/recovery](../docs/operations/BACKUP_AND_RECOVERY.md), hoặc nhập bộ dữ liệu có nguồn/license hợp lệ theo [dataset import guide](../docs/operations/DATASET_IMPORT_GUIDE.md). Catalog nhỏ không đủ để tái tạo ảnh gốc.

## Dữ liệu kiểm thử

Bộ scikit-image v0.25.2 có 10 ảnh: camera, brick, grass, gravel, coffee, chelsea, horse, rocket, clock_motion và hubble_deep_field. Xem [manifest](sample_manifest.json) cho URL, SHA-256 và rights reference từng file. Đây là fixture kỹ thuật, không thay bộ nhãn relevance đại diện.

```bash
python3 scripts/data/download_sample_dataset.py
```

Model weights nằm trong `.cache/clip/`; tests không tự tải mạng. Bộ COCO có caption được mô tả tại [RAG dataset](../docs/research/RAG_DATASET.md); bộ địa danh NPS tại [public landmark dataset](../docs/research/PUBLIC_LANDMARK_DATASET.md).

Dataset nhập phải nằm trong `DATASET_ROOT` allowlist; CLI không theo symlink thoát root hoặc fetch URL tùy ý. Metadata có thể cung cấp qua JSONL theo hướng dẫn nhập. Xác nhận license, provenance và privacy trước khi dùng ảnh thật. Ảnh gốc có thể giữ EXIF trong bucket private; không dùng ảnh nhạy cảm làm fixture công khai.

## Quy tắc lưu trữ

- Không commit raw images, source CSV hàng loạt, import receipts, credentials hoặc backup vào Git.
- Chỉ cập nhật catalog tổng hợp sau khi đối chiếu report; không đưa danh sách URL/ID riêng tư vào catalog.
- `.gitignore` tránh thêm lại dữ liệu local; `.dockerignore` ngăn đưa corpus vào image build context. Runtime vẫn đọc dataset qua mount theo cấu hình.
- Việc ngừng theo dõi không xóa dữ liệu khỏi lịch sử Git đã có; không tự rewrite history hoặc force-push trong lần dọn này.
