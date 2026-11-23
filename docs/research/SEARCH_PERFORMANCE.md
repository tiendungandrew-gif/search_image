# Search latency và baseline benchmark

Cập nhật Prompt06: advanced latency đo tách single-intent baseline; [ADVANCED_SEARCH_TEST_REPORT](../archive/ADVANCED_SEARCH_TEST_REPORT.md) là evidence hiện hành cho E1–E5, before/after và quality chưa đo. Các số đo Prompt05 dưới đây giữ làm historical baseline.

Mục tiêu nghiên cứu fast Semantic Search: P90≤300ms, secondary P95≤500ms. Targets chưa được coi đạt nếu chỉ có component timings hoặc mẫu smoke; [SEARCH_TEST_REPORT](../archive/SEARCH_TEST_REPORT.md) ghi actual results và giới hạn.

## 1. Measurement boundaries

- Server full response: monotonic ASGI scope receipt trước đọc body, đến khi final response-body send hoàn tất. Gồm auth/parse/decode, queue/inference, network dependency calls, batch metadata/object checks, DTO serialization/send. Không cộng post-response background work hoặc transit ngoài ASGI/socket queue trước app.
- Processing response: endpoint input parsing tới result DTO trước serialization; latency.processing_ms/latency_ms chỉ có boundary này. server_response_ms trong chính response vẫnnull; không nhét pre-send timer rồi gọi đó complete API duration.
- Bounded server samples được ghi sau final send, join X-Request-ID. serialization_send_ms từ DTO ready tới final send, không tính browser render.
- Client latency: HTTP initiate tới nhận/parse full body trên client; khác clock/perspective với server. Browser image download/render đo riêng, không trộn vào search response.

Stages thực: input_validation, compatibility checks, text preprocessing/tokenization, text inference/embedding, image preprocessing/embedding, reference-vector lookup khi dùng image_id, Qdrant retrieval, batch metadata, ranking, eligibility/object HEAD/URL construction. Stage có thể bao gồm queue wait tại embedding operation; không suy ra percentile tổng bằng cộng component percentiles.

## 2. Reproduction

Cần API đã load matching model/active index, chuẩn bị10 sample images, host backend venv có HTTPX và app package. Secrets lấy từ env file cho child, không CLI token arguments:

```bash
uv sync --project backend --extra dev --frozen
uv run --project backend python scripts/run_local.py --env-file .env -- backend/.venv/bin/python evaluation/scripts/benchmark_search.py --mode text --requests 100 --warmup 5 --concurrency 1 --output evaluation/results/text_baseline.json
uv run --project backend python scripts/run_local.py --env-file .env -- backend/.venv/bin/python evaluation/scripts/benchmark_search.py --mode image --image datasets/sample/coffee.png --requests 100 --warmup 5 --concurrency 1 --output evaluation/results/image_baseline.json
```

Wrapper: `bash scripts/evaluation/benchmark_search.sh text` hoặc `image`, thêm flags như --requests/--concurrency/--warmup. Index report mặc định docs/verification/phase04/index.json, phải khớp active index; khi đổi corpus, truyền --index-report từ verified index snapshot mới.

Report giữ per-request IDs/outcomes/actual result IDs/stages/client+server timings, P50/P90/P95 nearest-rank sorted index ceil(p*n), throughput, error rate và counts. Warmup không vào measurement window. Generator dùng số workers cố định, drain hết outstanding, không trộn local generator queue wait vào HTTP start. Failed samples giữ riêng, gồm transport/client timeout; error rate=unsuccessful/all attempted, không chỉ HTTP5xx. Percentiles successful-only phải kèm success/error counts và server join coverage.

Hardware/runtime provenance, collection exact count, active model/revision, dataset size, cache state, concurrency và source snapshot được ghi kèm artifacts. Lượt100 requests/modality một concurrency chỉ là Phase05 baseline, chưa phải full stress/steady-state confidence intervals của Prompt07. Corpus10 ảnh không đại diện large HNSW/index working set. Quality metrics cần human qrels, không suy ra từ latency hoặc image self-match.

## 3. Resource và tối ưu hiện có

Preload/warmup model trước ready, reuse SDK/pools, batch PG metadata/tags, query-point candidate cap50/default, một inference slot/API process, queue8/50ms. Compute cancellation giữ slot đến thread completion; không dùng timeout để giả capacity trống. Reference image_id dùng stored compatible vector; upload image vẫn decode/infer thật mỗi request. Không query-result cache, không fake nearest-neighbor search hoặc filename matching.

Qdrant transport timeout từ SEARCH_VECTOR_TIMEOUT_SECONDS, default1s; outer REQUEST_TIMEOUT_SECONDS default2s vẫn cap toàn request. Body/image/decode bounds giữ nguyên. Metadata HEAD checks và decoder subprocess có overhead thực, không bỏ privacy/eligibility checks để làm số đẹp. Sau baseline đã tối ưu decoder process reuse và RGB IPC, giữ chính hàm decode/memory/CPU/deadline bounds. Files *_before_decoder_reuse.json giữ số đo trước; *_baseline.json là số đo sau trong lượt final verifier đã pass. Thumbnail path/payload indexes chưa được tối ưu. Chỉ kết luận improvement trong đúng workload/corpus/hardware đã đo, không suy ra large-corpus gain.

CUDA và mixed search+indexing load chưa có số đo. CPU inference threads/device/model copies theo process cần profiling khi scale Uvicorn hoặc worker. Nếu một modality không đạt target, ghi rõ và dùng breakdown để lên kế hoạch Prompt07; không thay target hoặc chỉ báo mode nhanh hơn.
