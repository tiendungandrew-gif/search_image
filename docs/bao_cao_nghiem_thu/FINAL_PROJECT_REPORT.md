# Báo cáo bàn giao cuối dự án — Phase12

> Snapshot nghiệm thu trước chuẩn hóa repository và trước nâng cấp tài khoản/UI. Bản mới xem [phân quyền](architecture/ACCESS_CONTROL.md) và [nghiệm thu hiện hành](verification/access_control/REPORT.md). Đường dẫn tài liệu đã cập nhật; commands/source hashes/test counts bên dưới giữ lịch sử thời điểm chạy. Cấu trúc và kết quả refactor hiện hành tại [REPOSITORY_STRUCTURE](REPOSITORY_STRUCTURE.md). `.env.phase12` được host CLI ánh xạ sang `config/environments/deployment.env`; credentials/project IDs giữ nguyên.

Ngày08/11/2026 · Trạng thái **READY_WITH_LIMITATIONS**. Đây là mốc bàn giao phần mềm độc lập với dataset: đã triển khai và kiểm chứng trên Linux/Docker local, chưa provision máy chủ public. [Danh mục bằng chứng](verification/phase12/INDEX.md) phân biệt command thực thi, test pass, thất bại đã sửa và phần chưa đo. Không chuyển tiếp sang phase khác.

## A. Tổng quan dự án

Hệ thống tìm kiếm ảnh đa phương thức gồm React/TypeScript, FastAPI, PostgreSQL, Qdrant và MinIO private. CLIP paired encoder phục vụ text/image/multimodal; multi-intent dùng decomposition/fusion/reranking hữu hạn. RAG giải thích sau retrieval và Agent quan hệ nhiều bước là các tính năng tùy chọn, có nguồn evidence, timeout, trace và fallback; fast search không phụ thuộc LLM.

Phase12 giữ modular monolith và các contracts trước, bổ sung packaging/vận hành. App khởi tạo không có dataset/model/provider, sau đó có thể import/index/activate mà không rebuild frontend hoặc đổi kiến trúc. Dữ liệu chính513 ảnh được giữ ở project development riêng; các thử nghiệm deployment dùng7 ảnh hình học tổng hợp được đánh dấu rõ.

## B. Trạng thái triển khai các thành phần

| Thành phần | Trạng thái thực tế |
| --- | --- |
| Frontend | VERIFIED: Vite dist qua Nginx, deep links, responsive/private media/details và empty benchmark; Linux browser matrix |
| Backend | VERIFIED: FastAPI runtime image, authenticated APIs, typed errors/health, giới hạn input/deadline |
| PostgreSQL | VERIFIED: fresh migration head, metadata/jobs/leases/active pointer và persistent volume |
| Qdrant | VERIFIED: collection512 chiều từ model manifest thật, active7 vectors; collection cũ6 points giữ riêng |
| MinIO | VERIFIED: bucket private, originals/manifest objects thật, read auth/cache policy qua API |
| Ingestion | TESTED_WITH_SYNTHETIC_DATA: dry-run decode/hash/metadata, background jobs, first import6 và incremental import1 với carry-forward6 |
| CLIP/SigLIP | CLIP CPU thật đã verify512 chiều; SigLIP2 có evaluation adapter/thực nghiệm Phase07, chưa có production serving adapter/GPU nghiệm thu |
| Semantic Search | VERIFIED với CLIP thật/storage thật và synthetic corpus; Phase11 có số đo513 ảnh riêng |
| Multimodal Search | VERIFIED HTTP text+image và real-model QA; không đảm bảo compositional editing |
| Multi-intent Search | IMPLEMENTED/QA regression: supported patterns, fusion/reranking; visual constraints thiếu evidence vẫn UNKNOWN |
| RAG | Gemini đã kiểm chứng thật ở Phase08–11; deployment mới mặc định OFF/không key, disabled/not-ready behavior verified |
| AI Agent | Typed tools/budgets/trace/JSON/SSE đã có; proxy SSE và abstention thiếu facts được kiểm chứng Phase12 |
| Multi-hop | Workflow có nguồn NPS đã kiểm chứng Phase09; synthetic7 ảnh không có image–entity links, không coi fallback là multi-hop success |
| Evaluation | Snapshot/query/labels/Recall/nDCG/latency/resources/report tools có sẵn; chưa có human relevance/faithfulness labels được xác nhận |

## C. Kiến trúc triển khai

[FINAL_SYSTEM_ARCHITECTURE](architecture/FINAL_SYSTEM_ARCHITECTURE.md) mô tả kiến trúc thực tế. `compose.yaml` giữ development/Vite; `compose.prod.yaml` là stack độc lập, `compose.tls.yaml` bổ sung TLS. API/worker cùng backend image; bootstrap one-shot chờ infrastructure, migrate có advisory lock/guard và tạo bucket private trước startup.

Chỉ frontend publish ingress, mặc định127.0.0.1:8080. PostgreSQL/Qdrant/MinIO ở network internal, không có host ports. API/worker có egress cho provider nếu cấu hình. Persistent volumes theo project: postgres_data, qdrant_data, minio_data, evaluation_artifacts. Model/dataset là read-only mounts; source code không bind vào runtime. Heartbeat worker ở tmpfs, job state bền vững ở PostgreSQL.

API/worker UID10001, Nginx UID101, read-only rootfs/cap-drop/resource limits/log rotation. Local Snap cần ngoại lệ no-new-privileges mô tả tại mục K. Không suy ra HA, multi-node, zero downtime hoặc unlimited capacity từ Compose.

## D. Kết quả build

Các lệnh thực thi dùng env riêng `.env.phase12`, prefix `DEPLOY_USE_SG=1` và `--evidence-dir docs/verification/phase12/runs`:

```bash
python3 scripts/deploy.py --env-file .env.phase12 validate
python3 scripts/deploy.py --env-file .env.phase12 build --release phase12-verify-v4
python3 scripts/deploy.py --env-file .env.phase12 build --release phase12-final
```

Build API/worker và static frontend thành công. Backend dùng Python3.12.12/uv0.13.7, frozen lock với ML dependencies, không pytest/Ruff/test source/weights/env. Frontend dùng Node22.23.4/npm11.21.1 khi build, runtime Nginx1.30.5-alpine pinned digest, không Node/Vite dev server. MinIO image pin source/archive checksum kế thừa đã build thật, không thay bằng mock.

[Release manifest](verification/phase12/release.json) lưu source SHA-256 và immutable image IDs của release cuối. [Source snapshot cuối](verification/phase12/final_source.json) và archives giữ khả năng đối chiếu khi working tree chưa commit. `build` không đổi running release và từ chối retag khác source; `update` mới chuyển version. Không tag Git, push code hoặc publish registry trong lượt này.

## E. Xác minh startup

Fresh namespace `image-search-phase12` khởi động PostgreSQL16.15, Qdrant1.20.0, MinIO2025-09-07, bootstrap exit0, API/worker/frontend healthy. Migration head là `20261106_agent_knowledge`. Infrastructure readiness200 và worker idle khi rỗng. Nginx phục vụ SPA/API và private bytes thực, không development source mounts.

Project restore riêng `image-search-phase12-restore` ở8089 được phục hồi từ backup của source8088. Hệ thống chính5173/8000 vẫn513 ảnh, active generation3, knowledge4/3/3; [runtime audit](verification/phase12/runtime_audit.json) có read-only đối chiếu. Các project không dùng chung volumes/credentials.

## F. Cấu hình môi trường

[CONFIGURATION_REFERENCE](operations/CONFIGURATION_REFERENCE.md) liệt kê toàn bộ Settings và biến Compose/deployment. `init` sinh env0600, random PG/Qdrant/MinIO/API credentials, read/write tokens khác nhau, không copy `.env` serving; default SEARCH/RAG/AGENT=false. Validate kiểm production/debug, endpoint DB/storage nội bộ, secret lengths, flags, project/release names và read/write scopes. Typed Settings/bootstrap kiểm các bounds còn lại.

Model config gồm ID/revision/cache/device/batch/threads; compatibility dựa manifest/hash, không chỉ dimension. Provider keys chỉ ở backend env, không VITE/build/URL. CORS là JSON origins rõ ràng. Resource/ports/TLS/cert paths là cấu hình host; không giả định public domain đã tồn tại. Logs scrub secret values; validate dùng `config --quiet`, không dump credentials.

## G. Chế độ chưa có dataset

[HTTP empty](verification/phase12/http_20261108T021321_224938.json) và [browser empty](verification/phase12/browser_empty_20261108T021622_004161.json) xác nhận: frontend/deep links200, authenticated workspace báo empty_dataset/0 ảnh, search chưa ready trả lỗi rõ, RAG không sinh câu trả lời, Agent disabled không bịa evidence, evaluation không có experiment/metric giả. Empty browser4 pass/4 skip indexed-only.

[Missing-model test](verification/phase12/missing_model.json) đổi sang directory thực sự không có artifacts: frontend200, infrastructure ready200, search503 NOT_READY, inventory not_installed. App vẫn chạy. Không tự tải model khi API/worker idle, không tạo collection có dimension giả và không có fallback vector ngẫu nhiên.

## H. Thêm dữ liệu sau bàn giao

Các lệnh dưới là hướng dẫn cho dataset do operator cung cấp; placeholder paths/license cần thay bằng đầu vào thật. Toàn bộ interface đã được thực thi với fixtures riêng trong Phase12:

```bash
python3 scripts/deploy.py model-verify
python3 scripts/deploy.py import --input /absolute/datasets/batch-v1 --name my_dataset --version v1 --license LICENSE-ID --rights-ref https://source.example/dataset --dry-run
python3 scripts/deploy.py import --input /absolute/datasets/batch-v1 --name my_dataset --version v1 --index-version my_dataset_v1 --batch-size 4 --license LICENSE-ID --rights-ref https://source.example/dataset
python3 scripts/deploy.py status
python3 scripts/deploy.py check
python3 scripts/deploy.py knowledge --input /absolute/datasets/knowledge.json
python3 scripts/deploy.py knowledge --input /absolute/datasets/knowledge.json --apply
```

Input nằm dưới DEPLOY_DATASET_PATH, metadata.jsonl dùng filename tương đối duy nhất; validation decode/hash/schema thực, không tin extension/MIME. Dry-run accepted=0 và không ghi services. Apply đăng ký model/index, kế thừa ready ảnh cũ bằng reindex jobs, worker generate embeddings, verify PG/objects/points rồi activate, bật search/recreate API. Không rebuild frontend. Lỗi input/job/deadline không tự activate partial index; accepted jobs vẫn inspect/retry được.

Đã import6 rồi thêm1: images7, original receipts7, stored objects9 gồm7 originals+2 dataset manifests; ready embeddings13 trên hai index6+7. Thumbnail tạo theo yêu cầu, không giả định hai objects/ảnh. Knowledge dry-run nguồn NPS4 entities/3 relations/0 links đã validate, không apply vào shapes deployment; apply/referential integrity đã có QA/Phase09. [DATASET_IMPORT_GUIDE](operations/DATASET_IMPORT_GUIDE.md) là hướng dẫn đầy đủ.

## I. Sẵn sàng mô hình AI

Đã dùng `openai/clip-vit-base-patch32`, revision `3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268`, real CPU inference512 chiều, manifest `7f843c0bf81c571eee3b12621fc41811cea174113e6802684e9063b447e707dc`. Image embeddings/paired text queries và hash/index compatibility được verify với Qdrant thật. Model warm-load khoảng10s trong lượt benchmark, tách khỏi warm request latency.

`model-prepare` tải có chủ đích qua tools profile vào mount writable riêng; runtime mount read-only. Có thể chép pinned cache offline rồi `model-verify`. Không đặt weights trong Git/images. `--without-ml` dành empty CI, muốn inference phải build ML release. GPU cần image/driver/device config riêng và chưa nghiệm thu; SigLIP production chưa hỗ trợ bằng cách chỉ đổi model ID. [MODEL_MANAGEMENT](operations/MODEL_MANAGEMENT.md) ghi rõ tài nguyên/compatibility/download và giới hạn này.

## J. Độ tin cậy và chẩn đoán

Infrastructure health, search model/index health và worker heartbeat tách riêng. API health field worker=unknown không thay cho probe worker; CLI `check` kiểm heartbeat container độc lập. Logs JSON có request IDs, safe codes, Docker rotation; `logs/status/check` có deadlines/exit nonzero. Worker lazy-load, poll/retry hữu hạn, durable jobs/lease/fencing/idempotency tái sử dụng Phase04/11.

Đã restart API/worker/frontend và update/rollback với đủ7 ảnh/gen2 sau recovery. Bootstrap có thể chạy lại, không reset stores. Đã sửa health CLI nhập SQLAlchemy/NumPy trước khi đọc heartbeat: probe cũ3.5–3.9s gần timeout4s, bản mới khoảng0.64–0.87s ở audit Docker Snap. Unit regression bắt probe không import application stack. [OPERATIONS_RUNBOOK](operations/OPERATIONS_RUNBOOK.md) có triage, job repair, update và rollback.

## K. Bảo mật và rủi ro triển khai

Auth read/write, private media/no-store, no client keys, input/decode/path limits, allowlisted Agent tools và bounded calls tiếp tục hoạt động. Nginx chặn image/index mutations từ ingress; operator CLI có Docker access riêng. Read-only/non-root/cap-drop và không publish data ports đã kiểm bằng inspect. [Secret audit](verification/phase12/secret_audit.json) quét exact known values trong Git candidate files, dist và source archives; không in giá trị và không thay cho audit toàn lịch sử Git.

Local TLS đã verify với CA tự ký được chỉ định rõ và hostname/SAN validation; [tls_local.json](verification/phase12/tls_local.json). Không dùng verify=false. Không có public CA/domain/firewall hay thiết bị ngoài mạng được xác minh. Docker Snap từ chối exec với no-new-privileges=true; local env đặtfalse có ghi nhận, template vẫntrue.

Trước mở public còn phải tách PostgreSQL/MinIO least-privilege runtime roles, quyết định TLS nội bộ/exposure, edge quotas/rate limit và account/RBAC theo use case, off-host encrypted backups, CVE scan/pentest và certificate renewal. Runtime hiện dùng credentials quản trị trong network riêng; đây là giới hạn đáng kể cho external production, không che thành hardening pass. Chưa xác định license phân phối của repository; phải chốt trước public redistribution. [SECURITY_DEPLOYMENT](operations/SECURITY_DEPLOYMENT.md) giữ danh sách cụ thể.

## L. Backup, restore và rollback

Backup quiesce API/worker, pg_dump custom, cold archive Qdrant/MinIO cùng version, manifest SHA/size và permissions0700/0600. Stores/API tự khởi động lại theo thứ tự và health/search được kiểm tra. Không tự xóa backup, không mã hóa hoặc tự copy off-host; raw storage có thể chứa security metadata nên vẫn nhạy cảm.

Backup7 ảnh `20261108T023457_05fd3337` đã restore sang project mới trống. Guard chặn source=destination và đích đã có tables/collections/objects. Inventory sau restore khớp7 images/7 receipts/13 embeddings/13 succeeded job items/9 objects, hai collections6+7, active index `bb8bd6b1-efff-4910-b99a-97ab1938d63a` gen2; verify-all không missing/orphan. HTTP original/thumbnail/multimodal/search ở8089 cũng pass. Có log startup restore thất bại do probe nặng trước khi sửa, sau sửa `verify-restore` pass; không xóa dữ liệu để chạy lại.

Đã rollback releaseV4→V3 rồi update lạiV4, schema head không đổi và data/pointer giữ nguyên. Update release cuối cũng có backup trước chuyển. Rollback không tự downgrade DB; schema khác head bị chặn, cần kế hoạch migration/restore riêng. Đây là rehearsal local một node, chưa xác nhận disaster-recovery/RPO/RTO SLA. [BACKUP_AND_RECOVERY](operations/BACKUP_AND_RECOVERY.md) có exact commands và recovery sau startup failure.

## M. CI/CD

[quality.yml](../.github/workflows/quality.yml) giữ unit/lint/type/frontend/mock/service/fault/optional real-model jobs; thêm production build/bootstrap/empty HTTP/Chromium smoke bằng credentials ngẫu nhiên và image không ML. Actions pin commit, permissions read-only, artifacts/teardown always. Không publish/deploy external hay dùng production keys.

actionlint1.7.9 local pass; Make deploy aliases dry-run pass. Remote GitHub execution **NOT_RUN**, không gọi local checks là CI green. Chưa có registry signing, image vulnerability gate hoặc automatic public release workflow được nghiệm thu.

## N. Kết quả kiểm thử

| Nhóm thực thi Phase12 | Kết quả cuối | Phạm vi |
| --- | --- | --- |
| Backend fast |246 pass,0 fail,0 skip |214 unit +28 security +4 reliability, gồm14 deployment cases |
| Service integration |11 pass,0 fail | PostgreSQL/Qdrant/MinIO/migrations/concurrency/worker process trong QA riêng |
| Real model integration |1 pass,0 fail | CLIP thật và disposable images; không phải semantic relevance evaluation |
| Tổng backend đã chọn |258 pass | Không cộng reruns, không gọi toàn bộ tests opt-in cũ là đã chạy |
| Frontend unit |44 pass | Vitest11 files |
| Frontend lint/TypeScript/build |PASS | Không lỗi chưa xử lý |
| Backend Ruff/format/compileall |PASS |189 Python files được format check; compileall không phải static type check |
| Production browser empty |4 pass,4 skip | Indexed-only không áp dụng ở state rỗng |
| Production browser indexed |8 pass,0 skip | Chromium desktop/mobile, Firefox, WebKit; final functional run qua Nginx |
| Deployment/API/TLS |PASS | Fresh empty, absent model, import/incremental, private media, Agent abstention/SSE, restart và restore |
| Real dataset chất lượng |PENDING |513 ảnh serving được bảo toàn; không có nhãn xác nhận Recall/nDCG/faithfulness |
| Real provider ở deployment mới |NOT_CONFIGURED |RAG/planner keys không copy từ serving; lịch sử thật nằm Phase08–11 |
| Public host/GPU/remote CI |NOT_VERIFIED / NOT_RUN |Không tính là pass |

Hai browser profiles có12 successful case executions và4 intentional skips; không cộng lượt indexed lặp. Phase11 còn giữ66 browser checks và8 fault scenarios là **bằng chứng lịch sử**, không cộng vào Phase12. Logs thất bại ban đầu giữ lại: Snap/sandbox restrictions, selector benchmark sai, RAG-disabled assertion sai, worker health timeout và unit regression bắt lỗi đó. Harness được sửa theo contract; health code được sửa và tests cuối pass. Không gọi các failed attempts là test pass.

## O. Hiệu năng thực đo

Re-use Phase07 benchmark framework, snapshot7 synthetic images,3 English text queries, seed42, CLIP CPU4 threads, K7/candidates50, warmup10, C1 closed loop,300 requests, same-host HTTP qua Nginx8088. [Experiment raw](../evaluation/results/phase12/20261108T032218_benchmark_d385b66936/result.json) lưu mọi samples/resources/warmups/errors và provenance; chạy trên releaseV4 cùng application logic với release bàn giao.

[Đối chiếu component bytes](verification/phase12/component_comparison.json) xác nhận backend app/alembic và frontend static files không đổi giữaV4 và phase12-final. [HTTP smoke release cuối](verification/phase12/http_20261108T033503_024266.json) kiểm tra lại proxy/media/multimodal/SSE sau update; không cộng thêm lần chạy cùng browser tests vào tổng pass.

| Số đo | Kết quả |
| --- | --- |
| Thành công / lỗi / timeout |300/300 ·0 ·0 |
| Full API server P50 / P90 / P95 |127.95 /139.04 /143.28ms |
| HTTPX qua proxy P50 / P90 / P95 |133.90 /146.04 /150.27ms |
| Throughput đạt được |7.43 successful requests/s trong40.40s |

Các mục tiêu fast P90≤300ms/P95≤500ms được quan sát trong workload này; không đại diện corpus lớn, concurrency cao, cold load, tiếng Việt, browser render hoặc SLA public. Không so corpus7 với513 như một cải thiện thuật toán. Baseline Phase11 trên513 ảnh giữ nguyên: C1 500/500, serverP90=128.55ms/P95=135.45ms; C4 có3/100 INFERENCE_BUSY. Gemini Phase11 generated answers khoảng6.37–6.74s, miss mục tiêu3s; planner/browser có timeout/fallback. Chưa có quality-verified Recall@K/nDCG/Vietnamese retrieval, RAG faithfulness hoặc broad Agent task accuracy.

## P. Tài liệu bàn giao

Đã tạo [DEPLOYMENT_GUIDE](operations/DEPLOYMENT_GUIDE.md), [CONFIGURATION_REFERENCE](operations/CONFIGURATION_REFERENCE.md), [DATASET_IMPORT_GUIDE](operations/DATASET_IMPORT_GUIDE.md), [MODEL_MANAGEMENT](operations/MODEL_MANAGEMENT.md), [OPERATIONS_RUNBOOK](operations/OPERATIONS_RUNBOOK.md), [BACKUP_AND_RECOVERY](operations/BACKUP_AND_RECOVERY.md), [SECURITY_DEPLOYMENT](operations/SECURITY_DEPLOYMENT.md), [TESTING_AND_VERIFICATION](operations/TESTING_AND_VERIFICATION.md), [FINAL_SYSTEM_ARCHITECTURE](architecture/FINAL_SYSTEM_ARCHITECTURE.md), báo cáo này và [FINAL_HANDOVER](FINAL_HANDOVER.md). [DEPLOYMENT_AUDIT](archive/DEPLOYMENT_AUDIT.md) ghi baseline/gaps/changes.

Cập nhật README, MASTER_SPEC, ROADMAP, SETUP, DEVELOPMENT và API_SPECIFICATION để phân biệt development/production/history. Contracts/database/search/RAG/Agent/evaluation docs trước vẫn là nguồn chi tiết, không viết lại kiến trúc đã nghiệm thu. [INDEX bằng chứng](verification/phase12/INDEX.md) liên kết raw QA logs, deployment commands, source/release/dataset versions và các manual checks.

## Q. Vấn đề đã biết và điều kiện chưa đủ

Không còn lỗi Critical/High **đã quan sát trong phạm vi local milestone** chưa sửa. Không kết luận repository không còn lỗi. Các điều kiện external production đáng kể tại mục K vẫn mở: runtime administrative credentials, Snap no-new-privileges compatibility, public cert/host/firewall/renewal, quotas/auth theo môi trường và off-host encryption/recovery.

| Ưu tiên khi mở public | Mục còn mở | Hành động trước exposure |
| --- | --- | --- |
| HIGH | API/worker dùng PG/MinIO administrative credentials | Tách runtime roles/policies và kiểm tra lại migration/import/backup bằng operator role riêng |
| HIGH | Host/domain/public TLS/exposure chưa xác minh | Kiểm DNS/CA/renewal/firewall và acceptance trên host được chọn |
| HIGH | no-new-privileges bị tắt trong local Snap compatibility | Xác minh hardening mặc định trên host phù hợp; không dùng ngoại lệ local như security sign-off |
| Theo use case | Shared tokens, chưa account/RBAC/edge quotas | Chốt access/threat model và controls tương ứng trước cung cấp dịch vụ nhiều người |
| Theo recovery policy | Backup local chưa encrypted/off-host/DR SLA | Chọn retention/key management/storage ngoài host và diễn tập recovery |

Human labels tiếp tục pending theo lựa chọn người dùng; không tự chấm thay người. Tiếng Việt/visual constraints/negation/near duplicates và general multi-hop không được chứng nhận chất lượng bằng các smoke tests. Optional generation3s chưa đạt ở các lượt provider thật trước. Production SigLIP/GPU, scale/concurrency/HA, physical mobile/cross-OS, remote CI và licensing distribution chưa nghiệm thu. Các phần này không chặn app empty/local core search nhưng chặn những tuyên bố chất lượng/public tương ứng.

## R. Trạng thái bàn giao

**READY_WITH_LIMITATIONS**: production-like artifacts và functional local milestone đã hoàn tất, có empty deployment, synthetic import bằng CLIP thật, persistence, backup/restore/rollback và tests. Nhãn này không tương đương full production certification hoặc real-data quality acceptance. Không chọn READY_FOR_EXTERNAL_DEPLOYMENT khi exposure/security/provider/data decisions chưa xác nhận.

## S. Điểm vào và lệnh vận hành

Mặc định cài mới ở8080 bằng `.env.deploy`; phiên kiểm chứng đã có ở8088 dùng `.env.phase12`. Các lệnh sau là hướng dẫn dùng interface đã kiểm tra, không khẳng định đã tạo thêm một project mặc định:

```bash
python3 scripts/deploy.py init
python3 scripts/deploy.py validate
python3 scripts/deploy.py build
python3 scripts/deploy.py up
python3 scripts/deploy.py check
python3 scripts/deploy.py status
python3 scripts/deploy.py logs --tail 100
python3 scripts/deploy.py backup --output backups
python3 scripts/deploy.py down
```

Health liveness công khai ở `/api/v1/health/live`; readiness/search/workspace cần Bearer read token. FastAPI factory ở backend/app/main.py; worker `python -m app.cli.worker`; ingestion/knowledge dùng CLI mục H. Các exact QA/lint/browser commands ở [TESTING_AND_VERIFICATION](operations/TESTING_AND_VERIFICATION.md). Install Docker/Compose theo [SETUP](operations/SETUP.md); host deployment CLI chỉ cần Python3.11+, build dùng pinned container tooling. Make aliases là tiện ích, không bắt buộc.

Không gửi token/key vào chat hoặc lưu vào browser build. Trước dùng ngoài thực tế cần đủ hosting/resources/rights, model artifacts, data/verified labels phù hợp, đóng các deployment gates mục K/Q và chạy lại acceptance trên chính host đó. [FINAL_HANDOVER](FINAL_HANDOVER.md) là checklist ngắn cho người nhận.

## T. Hoạt động còn cần dữ liệu thật

Theo quyền dữ liệu và tài nguyên được phê duyệt: nhập corpus đánh giá đại diện, freeze query/splits, lấy relevance judgments độc lập, đo Recall@K/nDCG@K, Vietnamese retrieval, representative load/cold/concurrency, RAG grounding/faithfulness và Agent multi-hop task accuracy với provenance đầy đủ. Giữ synthetic tests riêng, không suy qrels từ ranking và không dùng fallback làm positive reasoning label.

Không tự crawl, mua tài nguyên, bật provider mới, publish hay mở phase tiếp theo. Hệ thống và workflow gán nhãn/import đã sẵn để thực hiện các hoạt động này khi có đầu vào tương ứng.
