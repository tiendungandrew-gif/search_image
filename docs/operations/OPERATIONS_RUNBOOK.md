# Runbook vận hành

Mọi command từ repository root, thêm `--env-file <private-file>` trước subcommand khi không dùng `.env.deploy`. Dùng `--tls` nhất quán cho môi trường HTTPS. Docker Snap hiện tại thêm DEPLOY_USE_SG=1.

| Nhu cầu | Command |
| --- | --- |
| Start / stop giữ dữ liệu | `python3 scripts/deploy.py up` / `python3 scripts/deploy.py down` |
| Restart ứng dụng | `python3 scripts/deploy.py restart` |
| Readiness/API/dataset/worker | `python3 scripts/deploy.py check` |
| Container và inventory | `python3 scripts/deploy.py status` |
| Logs gần đây | `python3 scripts/deploy.py logs --tail 100` |
| Worker logs | `python3 scripts/deploy.py logs --service worker --tail 100` |
| Model thực | `python3 scripts/deploy.py model-verify` |
| Backup trước maintenance | `python3 scripts/deploy.py backup --output backups` |

`check` qua frontend ingress, kiểm tra healthz/live/ready/workspace và worker heartbeat. `status` tách counts/images/objects/embeddings, active pointer, indexes, collections và job counts. Model artifacts present_unverified không phải model ready. API health worker field cũ có thể unknown; nguồn worker operational health là Docker healthcheck/heartbeat, không giả freshness từ API.

Metrics research có read auth tại `/api/v1/system/search-runtime`, `/system/search-metrics`, `/rag/samples`, `/search/agent/samples`. Giữ request ID, mode/model/index, durations/error categories. Không log raw query/prompt/API keys mặc định. Nginx access log off, API dùng structured JSON, Docker logs rotate10MiB×3/container. Logs local không phải centralized durable audit; cần xuất log trước recreate nếu tổ chức cần giữ lâu dài.

## Chẩn đoán

| Triệu chứng | Kiểm tra và xử lý |
| --- | --- |
| Bootstrap fail | Logs bootstrap; connectivity, credentials, migration head/pending guard. Không reset DB |
| live200, ready503 | PostgreSQL/Qdrant/MinIO probe, disk/resource/container health |
| ready200, dataset empty | Bình thường khi chưa import; dùng import guide |
| Search NOT_READY | Model cache/manifest, active index, initialization logs; không dựng vector giả |
| Worker blocked | Heartbeat/error category, model availability, job attempts/lease; sửa nguồn rồi retry có giới hạn |
| INFERENCE_BUSY | Queue capacity/wait budget; giảm offered load, đo lại; không tăng vô hạn queue |
| RAG timeout/quota | Provider status/limits; retrieval vẫn dùng được; không gọi fallback là generated |
| Agent insufficient evidence | Kiểm tra verified entities/relations/image links; không bịa facts |
| Browser image401 | Read token/session, authenticated proxy; không public hóa bucket |
| MinIO exec EPERM trên Snap | Xem DEPLOYMENT_AUDIT, không kết luận model/data hỏng |
| Disk gần đầy | Kiểm tra volume sizes/backups/cache qua Docker; không chạy system prune/volume rm thiếu review |

Container restart không phải zero downtime; requests đang chạy có thể bị hủy. Worker dùng durable claims/leases, bounded retry và fencing. Native CPU inference không thể hard-kill bằng asyncio; stop_grace_period45s rồi supervisor có thể SIGKILL, job sẽ cần lease recovery. Không báo job thành công trước receipt verification.

## Update/rollback

```bash
python3 scripts/deploy.py build --release release_2026_11_08_b
python3 scripts/deploy.py update --release release_2026_11_08_b
python3 scripts/deploy.py rollback --release release_2026_11_08_a
```

Build release mới không đổi release đang chạy. Update/rollback kiểm tra local image IDs với manifest, backup trước rồi khởi động/verify. Không publish hoặc retag đè release khác source. Rollback chỉ cho schema head tương thích; không tự downgrade migration. Khi schema không tương thích, restore backup vào namespace mới theo [BACKUP_AND_RECOVERY](BACKUP_AND_RECOVERY.md). Operator phải review migrations, model/index compatibility và traffic maintenance trước update production.
