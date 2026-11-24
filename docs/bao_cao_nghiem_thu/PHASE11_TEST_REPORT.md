# Nghiệm thu Phase 11 — kiểm thử, debugging và chất lượng hệ thống

> Tài liệu lịch sử theo phase; lệnh trong nội dung giữ tên đường dẫn cũ. Hướng dẫn hiện hành tại [danh mục tài liệu](../README.md) và [scripts](../../scripts/README.md).

Ngày07/11/2026. **READY_WITH_DOCUMENTED_LIMITATIONS** cho milestone phần mềm độc lập dataset. Đã sửa lỗi xác nhận, chạy kiểm tra thật và bảo toàn corpus hiện có. Chưa tuyên bố production readiness hoặc chất lượng AI đã được người đánh giá xác nhận. Dừng sau Phase11.

## A. Tóm tắt điều hành

Backend244 tests được chọn pass, frontend44 unit/component tests pass, browser66 cases được chọn pass và4 loại fault scenario trên2 trạng thái dữ liệu đều pass. Fast search C1 trên513 ảnh đạt500/500, P90128,55/P95135,45ms. C4 có3/100 HTTP503 do queue; Gemini có planner retry timeout và RAG vượt3s. Hai browser RAG trả fallback generation_unavailable/LLM_TIMEOUT, UI vẫn giữ ảnh. Các kết quả này được báo nguyên trạng.

Đã bổ sung stack QA riêng, regression/security/reliability tests, CI không cần production secrets và11 tài liệu nghiệm thu. Không xóa/reindex/ingest corpus phục vụ để làm test pass.

## B. Kiểm toán repository

Đã kiểm tra frontend/backend, migrations/DB models, Compose, ingestion/jobs/worker, CLIP, search/fusion/constraints/reranker, RAG/provider, Agent/planner/tools/knowledge, evaluation/tracking, config/logging/auth và tài liệu. [SYSTEM_AUDIT](SYSTEM_AUDIT.md) có module status matrix đúng enum của Phase 11. 15 tài liệu tối thiểu đều hiện hữu; không dùng sự hiện hữu thay execution evidence.

Working tree có thay đổi trước lượt này; baseline status/source đã lưu tại [baseline](../verification/phase11/baseline). Các source snapshots của experiments có archive/hash; `.git` không bị reset/commit/push. Không áp dụng architecture rewrite.

## C. Môi trường kiểm thử

Linux kernel6.17.0-1033-oem x86_64, host Python3.12.3; container Python3.12.12. Node22.23.4/npm11.21.1, Docker29.8.0/Compose5.5.1. PostgreSQL16.15-bookworm, Qdrant1.20.0; MinIO build source commit `07c3a429bfed433e49018cb0f78a52145d4bedeb`, image local `ai-image-search/minio:2025-09-07`. [environment.json](../verification/phase11/environment.json) lưu runtime/images và dependency compatibility.

CLIP `openai/clip-vit-base-patch32`, pinned revision `3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268`,512 chiều/CPU; QA1 thread, serving4 threads. Cache xác minh hashes, không tải weights ngầm. Gemini native `gemini-3.5-flash-lite` đã gọi thật; provider key chỉ đọc trong server env.

QA ports8011/5175, project `phase11-qa-2c8ad1b9345d`, volumes/network/credentials riêng. Serving8000/5173 giữ513 images/vectors, generation3,4 entities/3 relations/3 image links. Corpus là mẫu nhỏ công khai hiện có, chưa có production dataset đại diện hoặc human qrels. User đã chọn giữ quality gate chờ xác nhận; không tự gán điểm.

## D. Phạm vi coverage

[TEST_COVERAGE](../testing/TEST_COVERAGE.md) đối chiếu backend, frontend, infrastructure, ingestion, semantic, multimodal, multi-intent, RAG, Agent, security và performance. Coverage là hành vi/boundary, không phải line coverage %. Backend không cấu hình mypy/pyright; Python type check riêng là NOT_CONFIGURED. TypeScript strict/typecheck bao gồm source, configs và E2E.

## E. Kết quả và lệnh thực thi

| Bộ kiểm tra cuối | Pass | Fail còn mở trong bộ | Skip theo profile |
| --- | ---: | ---: | ---: |
| Backend fast | 232 | 0 | 0 |
| Service integration | 11 | 0 | 0 |
| Real CLIP integration | 1 | 0 | 0 |
| Frontend Vitest | 44 | 0 | 0 |
| QA mock browser | 4 | 0 | 0 |
| QA empty browser | 4 | 0 | 8 indexed cases không áp dụng |
| QA indexed browser | 8 | 0 | 4 empty cases không áp dụng |
| Serving browser regression | 50 | 0 | 0 |
| QA fault checks:4 loại ×2 trạng thái | 8 | 0 | 0 |

Không cộng reruns/benchmarks vào số test; browser có12 mocked cases và54 cases không backend mock. Các tests legacy không chọn không được gọi là đã pass. Human quality evaluation BLOCKED do chưa có nhãn; production-scale/physical-device/soak NOT_VERIFIED. Failed reproductions và lỗi sandbox/setup ban đầu vẫn giữ trong logs và [BUG_FIX_REPORT](BUG_FIX_REPORT.md).

Các lệnh đã dùng: `scripts/qa.py up --with-model`, `fast`, `frontend`, `services`, `ai`, `mock-browser`, `browser`, `seed`, `faults`, `down`; `QA_INDEXED=1` cho indexed browser, `QA_USE_SG=1` cho Docker Snap máy này. Lint `ruff check`, `ruff format --check`, compileall và `git diff --check`; frontend npm ci/typecheck/lint/test/build. `uv pip check`:69 packages tương thích; npm audit:0 advisory. Backend image build dùng `uv sync --frozen` với extras dev/evaluation/ML theo profile.

Serving regression:

```bash
RUN_RAG_E2E=1 backend/.venv/bin/python scripts/check_frontend.py foundation.spec.ts phase10.spec.ts rag.spec.ts --project desktop --project mobile --project firefox --project webkit
```

Chi tiết reproduce/điều kiện ở [TEST_STRATEGY](../testing/TEST_STRATEGY.md). Kết quả cuối, source hash, logs và scan tại [final_audit.json](../verification/phase11/final_audit.json).

## F. Lỗi phát hiện

Chín lỗi được tái hiện: Content-Length500, control-character validation, Agent deadline race, resource lifecycle leak, health refresh cleanup, recoverable RAG SSE kết thúc sớm, zero-vector job báo thành công, benchmark monitor leak và worker đóng ảnh khi encoder vẫn đọc. P11-07 mức High về toàn vẹn indexing; các lỗi còn lại Medium trong phạm vi quan sát. Không xác nhận destructive corruption hoặc credential exposure trên serving data.

## G. Lỗi đã sửa

[BUG_FIX_REPORT](BUG_FIX_REPORT.md) ghi từng ID, reproduction, expected/actual, root cause, file sửa, regression và kết quả. Thêm ErrorBoundary, typed workspace/evaluation contracts, QA namespace guards, bounded worker metrics và safe trace fields. Không bỏ validation hoặc thay production encoders bằng fake để vượt test.

## H. Tình trạng tích hợp

React→FastAPI→PostgreSQL/Qdrant/MinIO đã chạy thật. Fresh migrations, private object round-trip, vector upsert/query/filter, retry/repair/lease và model-index compatibility đã xác minh. [INTEGRATION_TEST_REPORT](INTEGRATION_TEST_REPORT.md) phân biệt real RPC với injected fault/LLM double. Media dùng authenticated API proxy; presigned URL/expiry là N/A theo kiến trúc hiện hành.

## I. Dữ liệu rỗng

Stack QA mới khởi động không image/index/knowledge/benchmark; infrastructure ready không phụ thuộc dataset. UI không bịa ảnh/metrics, navigation và health hoạt động; disabled/not-ready có error/capability rõ. Đã kiểm tra empty→6 synthetic images→ready rồi dựng QA sạch lại. [EMPTY_DATASET_TEST_REPORT](EMPTY_DATASET_TEST_REPORT.md) và `empty_api.json` ghi bằng chứng.

## J. AI pipeline

Mocks kiểm tra thuật toán, timeout, malicious context và validation;8-dim vectors chỉ trong tests. Synthetic images kiểm tra file/pipeline/storage. CLIP thật tạo512-dim vectors, exact identity round-trip, các modes và incompatible manifest. Dữ liệu thật513 ảnh dùng cho API/browser/load; NPS facts hỗ trợ multi-hop. Gemini thật tạo2 câu RAG có citations trong Agent benchmark; browser live2 lần timeout trả fallback. Không suy ra semantic Recall@10, faithfulness hoặc entity resolution accuracy từ các execution checks này.

## K. Reliability

Ngắt4 container QA và SIGKILL worker child đều phục hồi đúng phạm vi. Request timeout, bounded retry/backoff, lease fencing, partial results/cancel/stale và resource cleanup được kiểm tra. [RELIABILITY_TEST_REPORT](RELIABILITY_TEST_REPORT.md) lưu latency/recovery và giới hạn: native CPU compute không hard-kill qua asyncio; chưa long soak/partition đa host/disk-full.

## L. Bảo mật

[SECURITY_AUDIT](SECURITY_AUDIT.md): input limits/control chars, auth/CORS, SQL binding, private buckets/media, XSS/URL checks, credentials/log allowlist và tool boundaries. Npm audit không advisory ở thời điểm chạy; không tuyên bố full CVE/pentest pass. HTTP nội bộ chưa TLS, đa tenant/edge/rate-limit/hardening thuộc deployment phase. Final scan kiểm tra docs/dist/artifacts không chứa giá trị secrets local.

## M. Hiệu năng

[PERFORMANCE_REGRESSION](PERFORMANCE_REGRESSION.md) ghi frozen data/config, server/client percentiles, throughput, failures và so sánh baseline. Fast C1 không thấy regression, đạt target quan sát trên corpus nhỏ. Image24/multi-intent30/multimodal24 success100%; C4 chỉ97/100. Gemini RAG TTLast6367,66–6744,84ms,0/2 đạt3s; planner2 initial timeouts trên4 attempts. Không áp target Fast Search cho multi-hop; không coi HTTP200 là không có timeout nội bộ.

## N. CI/CD quality gates

`.github/workflows/quality.yml` pin action commit, contents:read, bounded timeout/concurrency. Các jobs: backend-fast, frontend-fast/mock browser, real services/empty browser/faults và optional real CLIP manual. Normal PR không yêu cầu provider secrets/model download. Actionlint pass và local equivalents đã chạy; GitHub remote execution **NOT_VERIFIED**, chờ push/runs. Real dataset evaluation/load hiện là manual profiles, chưa có corpus/qrels production để provision CI. Không deploy/publish.

## O. Các mục còn mở

- [ ] Human relevance/faithfulness labels và evaluation đại diện; chờ xác nhận theo lựa chọn người dùng.
- [ ] Capacity plan cho C4/backpressure và tải/corpus production.
- [ ] Provider latency/availability: RAG≤3s chưa đạt; timeout/fallback là behavior có thật.
- [ ] Chạy GitHub Actions trên remote sau push, không gọi local pass là remote green.
- [ ] TLS/edge hardening, RBAC/backup-restore/soak/physical-device checks ở phạm vi thích hợp.

Không còn Critical/High confirmed software defect chưa xử lý trong phạm vi milestone này. Các mục chất lượng/latency vẫn là gate nếu release yêu cầu những mục tiêu đó; không đánh dấu đã pass chỉ vì unit tests xanh.

## P. Sẵn sàng cho Phase12

Có đủ nền tảng để tiếp tục packaging, cấu hình môi trường, orchestration, startup verification, runbook và dataset import procedures. Phần đó vẫn cần triển khai/nghiệm thu riêng. Dữ liệu hiện có đã giữ nguyên theo [preserved_data.json](../verification/phase11/preserved_data.json). Việc mở production hoặc tuyên bố chất lượng nghiên cứu cần đóng các gate liên quan trước.

## Q. Trạng thái cuối

**READY_WITH_DOCUMENTED_LIMITATIONS.** Phần mềm độc lập dataset đã được kiểm tra, lỗi xác nhận đã sửa, QA cô lập và có bằng chứng tái lập. Chất lượng AI, provider3s, capacity production và remote CI chưa xác nhận đầy đủ. **Dừng ở Phase11; không tự triển khai Phase12.**
