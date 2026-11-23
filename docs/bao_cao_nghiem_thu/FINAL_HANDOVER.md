# Bàn giao cuối — Phase12

Cập nhật 08/11/2026: [Đăng nhập và quản trị thư viện](operations/ACCOUNTS.md) — Admin/User, quyền theo thư viện và khu quản trị riêng.
Kết quả tài khoản/UI hiện hành: [nghiệm thu phân quyền](verification/access_control/REPORT.md). Các test counts Phase12 bên dưới là snapshot lịch sử.

**READY_WITH_LIMITATIONS ·08/11/2026.** Mốc phần mềm đã kiểm chứng local; chưa phải chứng nhận public production hoặc chất lượng tìm kiếm trên dữ liệu có nhãn. Báo cáo đầy đủ [A–T](FINAL_PROJECT_REPORT.md), [bằng chứng](verification/phase12/INDEX.md), [kiến trúc cuối](architecture/FINAL_SYSTEM_ARCHITECTURE.md).

## Đã bàn giao

- [x] Backend/worker image cùng codebase, frontend static/Nginx và Compose production riêng.
- [x] Fresh bootstrap/migration/private bucket, worker idle khi chưa có ảnh/model/provider.
- [x] Env riêng0600, không copy secrets serving vào image/frontend.
- [x] Model/cache/manifest compatibility và CLIP CPU inference thật.
- [x] Dry-run/import/index/verify/activate không rebuild frontend; incremental import giữ ảnh cũ.
- [x] Health/logs/status, bounded retries/deadlines và restart giữ dữ liệu.
- [x] Backup checksum, restore namespace trống, verify inventory/index/media; update/rollback rehearsal.
- [x] Backend258 selected tests, frontend44 unit; browser empty4 pass/4 skip và indexed8 pass; lint/type/build pass.
- [x] Benchmark raw/provenance, các thất bại đã sửa và các phần chưa nghiệm thu được giữ rõ.
- [x] Hướng dẫn deploy/config/import/model/operations/security/backup/testing và báo cáo cuối.

## Điểm vào hiện tại

| Địa chỉ | Môi trường |
| --- | --- |
| http://127.0.0.1:8088 | Production-like có tài khoản Admin/User, `config/environments/deployment.env`, 7 ảnh tổng hợp; Admin ở `.cache/auth/deployment-admin-login.json` |
| http://localhost:5173 | Development hiện có, corpus513 ảnh từ các phase trước; không dùng làm production ingress |
| http://localhost:8000/api/v1/health/live | Liveness development; production-like dùng cùng path qua8088 |

App mới mặc định8080; không chạy thêm mặc định trên máy này nếu chỉ muốn xem phiên8088 đã có. RAG deployment mới OFF/không key, Agent chỉ deterministic khi đã bật; synthetic shapes không có knowledge links. Không copy Gemini/storage keys giữa môi trường để làm test pass.

## Cài mới và vận hành

Prerequisites Linux/Python3.11+/Docker/Compose theo [SETUP](operations/SETUP.md). Từ root repository, ở máy hoặc project mới:

```bash
python3 scripts/deploy.py init
python3 scripts/deploy.py validate
python3 scripts/deploy.py build
python3 scripts/deploy.py up
python3 scripts/administration/accounts.py bootstrap --env-file .env.deploy --output .cache/auth/deployment-admin-login.json
python3 scripts/deploy.py check
python3 scripts/deploy.py status
python3 scripts/deploy.py logs --tail 100
python3 scripts/deploy.py backup --output backups
python3 scripts/deploy.py down
```

Đây là hướng dẫn, không phải log của một lần cài mới khác. `init` từ chối overwrite; `down` giữ volumes. Với phiên8088 thêm `--env-file config/environments/deployment.env` trước subcommand. Docker Snap tại máy này dùng `DEPLOY_USE_SG=1`; ngoại lệ local no-new-privileges được ghi trong [DEPLOYMENT_GUIDE](operations/DEPLOYMENT_GUIDE.md), không mặc nhiên áp dụng lên host khác. Release Phase12 lịch sử ở [release.json](verification/phase12/release.json), release hiện hành tại [nghiệm thu tài khoản/UI](verification/access_control/REPORT.md); build source đã đổi phải dùng release tag mới.

## Thêm dataset/model

Chuẩn bị ảnh có quyền dưới DEPLOY_DATASET_PATH, metadata.jsonl, pinned model cache hoặc `model-prepare`. Sau đó:

```bash
python3 scripts/deploy.py model-verify
python3 scripts/deploy.py import --input /absolute/datasets/batch-v1 --name my_dataset --version v1 --license LICENSE-ID --rights-ref https://source.example/dataset --dry-run
python3 scripts/deploy.py import --input /absolute/datasets/batch-v1 --name my_dataset --version v1 --index-version my_dataset_v1 --batch-size 4 --license LICENSE-ID --rights-ref https://source.example/dataset
python3 scripts/deploy.py check
```

Thay các placeholders bằng nguồn thật. [DATASET_IMPORT_GUIDE](operations/DATASET_IMPORT_GUIDE.md) có metadata/knowledge/retry rules; [MODEL_MANAGEMENT](operations/MODEL_MANAGEMENT.md) có download/offline/CPU và giới hạn GPU/SigLIP. Không bật search trên index chưa verify, không dùng caption như quan hệ đã xác nhận.

## Kiểm thử và phục hồi

```bash
python3 scripts/qa.py fast
python3 scripts/qa.py frontend
python3 scripts/qa.py up --with-model
python3 scripts/qa.py services
python3 scripts/qa.py ai
python3 scripts/qa.py down
```

AI profile cần cache thật đã chuẩn bị, không tự download; Docker Snap dùng QA_USE_SG=1. [TESTING_AND_VERIFICATION](operations/TESTING_AND_VERIFICATION.md) ghi lint/type/browser và phân loại kết quả. [BACKUP_AND_RECOVERY](operations/BACKUP_AND_RECOVERY.md) ghi restore vào env/project mới, verify-restore, permissions và giới hạn version/encryption. [OPERATIONS_RUNBOOK](operations/OPERATIONS_RUNBOOK.md) ghi release update/rollback không tự downgrade schema. Backups chứa dữ liệu nhạy cảm, giữ ngoài Git và cần chính sách off-host riêng.

## Điều kiện trước khi mở public hoặc công bố chất lượng

- [ ] Chọn host/domain/resources/exposure, chứng chỉ tin cậy/renewal và kiểm lại firewall/TLS tại môi trường đó.
- [ ] Tách DB/S3 runtime credentials theo quyền tối thiểu; xác minh no-new-privileges trên host phù hợp, account/quotas/rate limit theo use case.
- [ ] Backup mã hóa ngoài host, diễn tập recovery; CVE scan/pentest và license phân phối được chấp thuận.
- [ ] Push/review code và chạy GitHub Actions thực; chưa có remote CI green hay registry release được tạo trong lượt này.
- [ ] Có dataset/splits/nhãn relevance/faithfulness do người đánh giá xác nhận; đo Recall/nDCG/Vietnamese/RAG/Agent và capacity đại diện.

Các việc trên cần đầu vào bên ngoài. Phần mềm vẫn khởi động và nhận dataset sau bàn giao; không tự mở phase mới.
