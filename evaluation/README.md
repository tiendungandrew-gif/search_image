# Đánh giá retrieval — Prompt07

Đây là hướng dẫn hiện hành; công cụ Prompt05–06 được giữ bên dưới để bảo toàn khả năng tái lập. Source evaluation dùng chung tại `backend/app/evaluation/`, không tạo framework song song. Chưa có human relevance labels; không đổi templates thành verified để lấy điểm.

## Chuẩn bị và gán nhãn

Cần stack/index/cache thật theo Prompt04–06. Cài `uv sync --project backend --extra dev --extra ml --extra evaluation --frozen`. CLI chạy từ project root; credentials chỉ qua `scripts/run_local.py`, không truyền token trong arguments.

```bash
backend/.venv/bin/python scripts/run_local.py --env-file .env -- backend/.venv/bin/python -m app.cli.evaluation validate-dataset
backend/.venv/bin/python -m app.cli.evaluation annotation-pack
backend/.venv/bin/python -m app.cli.evaluation validate-labels --labels evaluation/relevance_labels/reviewed.json
```

Mở `.cache/evaluation/annotation.html` offline, gán0/1/2 và điều kiện cho24 query×10 ảnh, xuất draft để giữ tiến độ. File reviewed.json chỉ tồn tại sau khi người đánh giá xuất verified. Bản nháp không được chấm semantic quality. Snapshot/query hashes phải trùng với labels. Fresh clone có UUID mới cần `prepare` để freeze phiên bản dataset/query mới; các outputs hiện có không được overwrite. `prepare --output ... --queries ...` chọn tên mới khi cần. Benchmark/evaluate/annotation/model/profile đều hỗ trợ `--snapshot` và `--queries` cho phiên bản khác.

## Quality và ablation

```bash
# Không có labels: chỉ4 exact-identity;24 semantic cases được báo chưa đo.
backend/.venv/bin/python scripts/run_local.py --env-file .env -- backend/.venv/bin/python -m app.cli.evaluation evaluate
# Chỉ chạy sau khi có nhãn được người đánh giá xác nhận.
backend/.venv/bin/python scripts/run_local.py --env-file .env -- backend/.venv/bin/python -m app.cli.evaluation evaluate --labels evaluation/relevance_labels/reviewed.json --split test
backend/.venv/bin/python scripts/run_local.py --env-file .env -- backend/.venv/bin/python -m app.cli.evaluation evaluate --labels evaluation/relevance_labels/reviewed.json --config evaluation/experiments/phase07/A0.json
backend/.venv/bin/python scripts/run_local.py --env-file .env -- backend/.venv/bin/python -m app.cli.evaluation evaluate --labels evaluation/relevance_labels/reviewed.json --config evaluation/experiments/phase07/A4.json
```

A0…A4 lọc cùng multi-intent queries; A5_text/A5_rrf/A5_score lọc cùng paired queries. Quality và latency tái sử dụng chính request_options/config, không so các tập khác nhau như một task. `compare_quality` tính paired cluster bootstrap với same dataset/query/labels hashes; không bootstrap điểm không tồn tại. model-comparison cũng nhận `--labels` để chấm cùng qrels theo model/language/task. Exact identity và ANN overlap luôn tách khỏi relevance.

## Latency, load và profiling

```bash
backend/.venv/bin/python scripts/run_local.py --env-file .env -- backend/.venv/bin/python -m app.cli.evaluation benchmark --config evaluation/experiments/phase07/fast_default.json
backend/.venv/bin/python scripts/run_local.py --env-file .env -- backend/.venv/bin/python -m app.cli.evaluation benchmark --config evaluation/experiments/phase07/load20.json
backend/.venv/bin/python scripts/run_local.py --env-file .env -- backend/.venv/bin/python -m app.cli.evaluation benchmark --config evaluation/experiments/phase07/load_mixed.json
sg docker -c 'backend/.venv/bin/python scripts/run_evaluation_suite.py --optimization --matrix'
backend/.venv/bin/python -m app.cli.evaluation analyze-optimization --suite docs/verification/phase07/suites/20261104T093924_4026c284.json
bash scripts/run_evaluation_container.sh profile
```

Suite thay width1/2 và recreate API khi so ABBA; đợi search-ready, khôi phục width ban đầu rồi chạy matrix. Không chạy tests/inference khác đồng thời với phép đo. `--only NAME...` chọn configs cho matrix; file config chứa requests/concurrency/rate/duration/warmup/timeouts/candidates/fusion/rerank/seed. Kết quả ghi cả lỗi, warmup và sample coverage; successful latency không thay error-rate. Suite mới sinh ID mới, dùng đường dẫn suite mới khi phân tích; `--results PATH` toàn cục đặt trước subcommand để tách nhóm experiments. Fast target chỉ áp fast workload đủ mẫu/không lỗi, không áp advanced/mixed.

## Hai model và báo cáo

```bash
backend/.venv/bin/python -m app.cli.download_evaluation_model --output .cache/siglip2
bash scripts/run_evaluation_container.sh clip
bash scripts/run_evaluation_container.sh siglip2
# Khi có nhãn thật:
# bash scripts/run_evaluation_container.sh siglip2 --labels evaluation/relevance_labels/reviewed.json
MPLCONFIGDIR=.cache/matplotlib backend/.venv/bin/python -m app.cli.evaluation report --output evaluation/reports/new_run
bash scripts/verify_evaluation.sh
```

Docker runner cần quyền socket, current stack và image worker đã build; mount cache model read-only/results writable với UID hiện tại, không expose data ports hoặc đổi active index. SigLIP2 có download receipt pin revision/SHA. Nếu snapshot tham chiếu file `.cache/evaluation/images`, runner mount cùng đường dẫn tương đối dưới `/srv`.

Mỗi experiment có experiment.json/result.json, raw samples/per-query records/source hash/archive và config; không ghi đè run trước. Report tạo summary.json/summary.csv/queries.csv/REPORT.md, PNG/SVG latency/load/model resources. Semantic quality chart chỉ tạo từ human-labeled aggregates; thiếu labels không sinh cột giả. Output directory phải mới. [Báo cáo thực tế](reports/phase07/REPORT.md), [phương pháp](../docs/EVALUATION_METHODOLOGY.md), [nghiệm thu A–M](../docs/PHASE07_TEST_REPORT.md).

---

# Retrieval evaluation và latency — Prompt05–06

Đã có corpus fixture10 ảnh từ Prompt04 và search CLIP thật. **Chưa có human-verified qrels**, vì vậy Recall/MRR/nDCG thực chưa đo; không tự gán labels theo tên file, cosine score hoặc kỳ vọng của model.

## Metric code và labels

Implementation duy nhất tại `backend/app/evaluation/metrics.py`, tests explicit numeric fixtures trong backend unit. Recall@1/5/10 chia tổng relevant images; Precision@10 luôn chia10 kể cả corpus nhỏ/returned<10; MRR@10 theo first relevant rank trong depth10; nDCG@10 dùng gain2^grade−1/log2(rank+1). Duplicate IDs chỉ tính lần đầu, không compact ranking để tăng metric. Query không có relevant/ideal gain được loại khỏi relevance aggregates và báo riêng.

Bắt đầu từ [template](relevance_labels/template.json). Annotator phải review toàn universe, ghi corpus_image_ids thật, human_verified=true và exhaustive_judgments=true sau khi kiểm duyệt. Mỗi query có query_id/query và grades map mọi corpus UUID→grade0…3, hoặc relevant_image_ids cho binary judgments đã xác nhận exhaustive. Không có label không mặc nhiên là nonrelevant. Dùng frozen corpus/index/model/hash, reviewer/provenance/version và dev/test split trước nghiên cứu Prompt07.

```bash
uv run --project backend python scripts/run_local.py --env-file .env -- backend/.venv/bin/python evaluation/scripts/evaluate_search.py --labels evaluation/relevance_labels/verified.json --output evaluation/results/quality.json
```

verified.json phải do người dùng/annotator cung cấp; repo không giả tạo file này. Evaluator từ chối template chưa verified, kiểm actual image availability/index eligibility và universe, sau đó gọi API thật; không dùng fake rankings. CLI metric formulas tested không đồng nghĩa retrieval quality đã được kiểm định.

[Smoke queries](queries/smoke.json) bao gồm object/color+object/scene/action theo fixture. Chúng dùng để kiểm tra luồng, không chứa relevance labels hoặc là held-out benchmark.

## Latency

[benchmark_search.py](scripts/benchmark_search.py) hỗ trợ text/image, request count, warmup, concurrency, per-request records và nearest-rank P50/P90/P95. Join full ASGI samples qua request ID; client duration tách server processing/full response. Token chỉ qua environment, không log query text hoặc headers. Xem [SEARCH_PERFORMANCE](../docs/SEARCH_PERFORMANCE.md) cho commands, boundaries, resource và interpretation; results lưu actual JSON tại evaluation/results.

## Advanced retrieval — Prompt06

[phase06.json](experiments/phase06.json) định nghĩa E1 whole-query, E2 multi-query/whole rescore, E3 RRF hoặc weighted score, E4 constraint rerank, E5 paired fusion. Benchmark hỗ trợ thêm --mode multi_intent|multimodal, --fusion rrf|weighted_score, --rerank và --retrieval-strategy whole_query|multi_query|fused. Advanced workload luân phiên English/Vietnamese AND/OR, giữ subgroup latencies. --mode text/image vẫn giữ workload Prompt05, không gộp advanced latency vào fast latency.

```bash
bash scripts/benchmark_search.sh multi_intent --requests 100 --rerank
bash scripts/benchmark_search.sh multimodal --requests 100 --fusion weighted_score --rerank
uv run --project backend python scripts/run_local.py --env-file .env -- backend/.venv/bin/python evaluation/scripts/evaluate_advanced.py --labels evaluation/relevance_labels/advanced_verified.json --output evaluation/results/advanced_quality.json
```

[advanced_template.json](relevance_labels/advanced_template.json) chưa có human judgments, không được đổi human_verified chỉ để chạy. Mỗi query do annotator tạo cần query_id/language/groups, request(text, optional existing reference image_id, frozen explicit constraints nếu cần), grades map đầy đủ corpus UUID→0…3, constraint_judgments map đầy đủ corpus UUID→{clause_id:true|false|null}, overall_satisfied_image_ids được người đánh giá xác nhận thỏa toàn logic query. Reference UUID phải là image thật; không thay model hoặc corpus giữa experiments. Ghi annotator/provenance/version, actual group coverage và dev/test split; không tune trên held-out test.

Các nhóm cần chú thích riêng: hai/ba/bốn+ conditions, AND/OR, required/optional, tiếng Việt/Anh; paired color edit/object substitution/scene/appearance/background. Corpus10 mẫu hiện không đủ coverage, không tự tạo ground truth cho các scene không có. Không có qrels thì chỉ chạy metrics unit fixtures và functional/latency comparisons; actual quality ghi not_measured.

Advanced metrics tại backend/app/evaluation/advanced_metrics.py: constraint accuracy chỉ trên verified predictions có human true/false labels, báo verification coverage riêng; UNKNOWN là abstention, không success hoặc mismatch. multi_intent_success@10 là có ít nhất một image trong Top10 nằm trong human overall_satisfied set; no-answer queries tách ra, không nhận điểm thành công giả. constraint_satisfaction@10 là tỷ lệ returned images thỏa overall labels; empty results→null. Không suy correctness từ cosine hoặc metadata match score. E1–E5 quality harness kiểm actual corpus availability/index/universe, báo per-query, macro per experiment và language; nDCG dùng human grades. Chưa có adequate data nên ablation/quality improvement chưa được đo.

## RAG Prompt08

Các run mới ghi riêng evaluation/results/phase08. `python -m app.cli.rag --requests 20` qua run_local/.env chạy R1 search-only/R2 metadata baseline/R3 selected context/R4 cap1, dùng API thật. `python -m app.cli.evaluation --results evaluation/results/phase08 report --output evaluation/reports/new_phase08_run` sinh CSV/Markdown/JSON/PNG/SVG từ raw RAG/fast measurements. `python -m app.cli.rag --review REVIEW.json --experiment RESULT.json` validate human review/hash và tổng hợp answer relevance/faithfulness0…2/unsupported claim rate theo VI/EN. Review phải human_verified/annotator/result_sha256 và exhaustive case IDs, không tự tạo nhãn. Citation-ID/exact quote audits không thay visual faithfulness hoặc answer relevance. [Protocol](../docs/RAG_EVALUATION.md), [nghiệm thu](../docs/PHASE08_TEST_REPORT.md).
