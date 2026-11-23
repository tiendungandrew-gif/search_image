# Backup và phục hồi

## Backup có maintenance window

```bash
python3 scripts/deploy.py backup --output backups
```

CLI giữ operation lock, dừng API/worker để quiesce writers, đọc inventory sau khi dừng, tạo PostgreSQL custom dump, dừng Qdrant/MinIO rồi archive volumes cold. Sau đó khởi động lại dependencies trước API/worker và kiểm tra readiness/search nếu đang bật. Cần dừng các administrator/import processes ngoài CLI này trước backup; không giả định transaction PostgreSQL làm atomic cả ba stores.

Mỗi backup có UTC timestamp/random ID, directory0700, files0600, không ghi đè backup cũ. Manifest có SHA-256/size, storage versions, inventory, active index/model identifiers và một số config không nhạy cảm. Chỉ manifest hoàn tất và checksum hợp lệ mới được gọi là backup verified. Transfer dùng streaming có deadline, không đọc toàn bộ volume vào RAM.

Files: postgres.dump, qdrant.tgz, minio.tgz, manifest.json. Configuration/provider/API keys không được copy từ `.env`; **raw storage có thể chứa security metadata và toàn bộ ảnh/metadata private**, nên backup vẫn là dữ liệu nhạy cảm. Chưa mã hóa backup hoặc tự đồng bộ off-host. Bảo vệ/encrypt bản copy ngoài máy theo công cụ và key-management được tổ chức lựa chọn; không commit backup. Gợi ý retention7 daily/4 weekly/12 monthly phải cân đối dữ liệu, storage và quy định của nơi chạy; CLI không tự xóa.

PostgreSQL dùng [custom dump/pg_restore](https://www.postgresql.org/docs/16/app-pgdump.html). Qdrant/MinIO ở đây dùng **cold volume archives cùng phiên bản**, không phải distributed online snapshots. Qdrant có [snapshot API riêng](https://qdrant.tech/documentation/operations/snapshots/) nhưng không trộn hai phương pháp mà bỏ qua version/consistency rules.

## Restore vào môi trường mới

Không restore in-place hoặc tự xóa DB/collection/object đang có. Chuẩn bị env riêng và dùng release đã build tương thích:

```bash
python3 scripts/deploy.py --env-file .env.restore init --project image-search-restore --port 8090 --model-path /absolute/model-cache --dataset-path /absolute/datasets --release existing_release
python3 scripts/deploy.py --env-file .env.restore restore --backup backups/BACKUP_ID
python3 scripts/deploy.py --env-file .env.restore check
python3 scripts/deploy.py --env-file .env.restore status
```

Chưa chạy `up`/bootstrap trên destination trước restore: pg_restore cần public schema trống. Guard kiểm tra project khác nguồn, database chưa có tables, Qdrant không collections và MinIO không objects; đích có dữ liệu bị từ chối. Script kiểm SHA, archive paths/no symlink, storage versions, bucket và model config trước phục hồi. Các application image IDs được quản lý bằng release manifest; bảo quản manifest/release/source cùng backup ở nơi an toàn.

Sau pg_restore/cold extraction, bootstrap idempotent, model/index compatibility, inventory và index consistency phải pass. RAG/Agent flags/keys không tự sao chép sang môi trường mới. Dataset và model artifacts cần cung cấp riêng qua mounts; weights không nằm trong backup này. Kiểm tra original media và search thực trước đổi ingress/DNS. Không chuyển traffic public tự động.

Nếu extraction/restore đã hoàn tất nhưng startup thất bại, kiểm tra và sửa nguyên nhân process/health trước. Đích đã có dữ liệu sẽ không cho restore lần nữa. Sau khi `up` thành công, chạy `python3 scripts/deploy.py --env-file .env.restore verify-restore --backup backups/BACKUP_ID` để đối chiếu inventory và verify mọi index mà không ghi đè stores. Phase12 đã gặp và sửa health probe import quá nặng trong chính tình huống này; giữ nguyên dữ liệu restore khi sửa.

## Tình huống phục hồi

| Sự cố | Hướng xử lý |
| --- | --- |
| PostgreSQL mất | Restore dump tương ứng cùng object/vector point-in-time; chỉ objects không khôi phục đầy đủ metadata/provenance |
| Qdrant mất/hỏng | Restore cold archive cùng version, hoặc tạo index mới/re-embed từ originals/metadata còn nguyên |
| MinIO mất | Restore original/thumbnail/manifest objects; nếu originals và backup đều mất thì không cam kết phục hồi ảnh |
| Model cache mất | Prepare lại đúng pinned cache hoặc chép offline và verify hashes |
| Worker chết | Lease expiry/fencing và bounded retry; kiểm tra receipts/consistency trước activate |
| Release lỗi | Rollback image nếu schema tương thích; nếu schema đổi không an toàn thì restore vào namespace mới |

Các test restore thực và dữ liệu đối chiếu được ghi ở [FINAL_PROJECT_REPORT](../FINAL_PROJECT_REPORT.md), không lấy việc tạo archive thành công làm bằng chứng search đã phục hồi. Chưa có bằng chứng off-site recovery, host disk loss, multi-node storage, KMS-encrypted source data hoặc recovery time SLA production.
