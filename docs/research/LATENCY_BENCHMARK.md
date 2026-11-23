# Latency, load và profiling — Prompt07

Full server latency từ ASGI receipt trước body read tới final body send; client latency từ initiate HTTP tới full response. Endpoint processing_ms trước serialize không là full response. Request IDs join bounded ring sau final send; missing successful server samples làm run incomplete_server_coverage, không im lặng bỏ mẫu. Preview image download/render không nằm trong search-response latency.

## Workloads và statistics

Profile fast dùng single-intent text; image upload kiểm image encoder thật; advanced dùng multi-intent/paired; mixed có selection weights50%fast/20%image/30%advanced và báo actual counts theo query type. Mode/rerank/fusion/candidates/query_types là config đã lưu, không giấu advanced vào fast.

Warmup ngoài measured window và được giữ cả outcome/failures. Closed-loop dùng fixed clients; open-loop có offered rate/duration, actual throughput, scheduling lag và client-capacity drops khi không còn slot. Không gọi client drops là API latency0 tốt; chúng là failures riêng. HTTP status/errors/client timeouts/504/503 được đếm; latency successful-only luôn kèm total/error counts. Duration includes drain, offered/achieved rates tách rõ.

Min/mean/median/nearest-rank P50/P90/P95/P99/max/population std được lưu. Nearest-rank index ceil(p*n), P50 có thể khác arithmetic median khi n chẵn, cả hai có field riêng. Không cộng component percentiles. Mỗi cấu hình steady-state chính≥300 requests; mixed fixed-duration có N thấp hơn và không dùng như fast SLO evidence. Fast target chỉ observed khi đủ samples, không lỗi, đủ server coverage và P90≤300/P95≤500; advanced/mixed không được tự áp cùng gate.

## Commands

```bash
backend/.venv/bin/python scripts/run_local.py --env-file .env -- backend/.venv/bin/python -m app.cli.evaluation benchmark --config evaluation/experiments/phase07/fast_default.json
backend/.venv/bin/python scripts/run_local.py --env-file .env -- backend/.venv/bin/python -m app.cli.evaluation benchmark --config evaluation/experiments/phase07/load20.json
sg docker -c 'backend/.venv/bin/python scripts/evaluation/run_evaluation_suite.py --optimization --matrix'
```

Last command là local operator workflow, thay .env object-check1/2 rồi recreate API và đợi search-ready, khôi phục width ban đầu sau controlled runs (mặc định bàn giao1). Cần Docker permission, host backend venv và existing model/index. Không truyền credentials qua CLI args hoặc ghi vào experiment config. Lệnh có thể mất nhiều phút; raw result folders dùng unique UTC/UUID IDs.

## Hardware, cold và resources

CPU Core7 240H/16 logical CPUs/15.11GiB RAM, CLIP float32 CPU4 Torch threads, one API inference slot. Private `/api/v1/system/search-runtime` trả safe model/index/thread/admission/RSS/HWM/CPU-time counters, không secrets/query data. Sampler một lần/giây tạo monitoring overhead được bật cùng cách khi so before/after; RSS/HWM là whole-process observations, không giả là per-query allocation. Model-comparison fresh processes đo initialization/warmup và process peak RSS riêng.

Không có CUDA theo actual inspection; GPU results unavailable. Model/process cold init không là OS/page-cache cold, filesystem cache uncontrolled. Chưa drop OS caches hoặc chứng minh cold HNSW working set. PostgreSQL EXPLAIN ANALYZE/BUFFERS dùng chính repository statements; Qdrant config/point/indexed-vector count và ANN-vs-exact được lưu riêng. Corpus10 có thể dùng seq/plain scans hợp lý; không force indexes hoặc claim large-corpus performance.

Actual values tại [EXPERIMENT_RESULTS](EXPERIMENT_RESULTS.md), raw experiments/CSV/charts; [PERFORMANCE_OPTIMIZATION](PERFORMANCE_OPTIMIZATION.md) ghi controlled config và semantic invariance limits.

Field fast_targets_observed hiện chỉ áp profile fast. Raw image experiment cũ có boolean theo framework ban đầu áp cùng ngưỡng số học; giữ raw immutable và không dùng field đó để chứng minh SLO fast. Phân loại workload trong config cùng số mẫu/lỗi là căn cứ diễn giải.
