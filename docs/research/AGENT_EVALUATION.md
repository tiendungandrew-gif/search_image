# Đánh giá Agent

Framework tái sử dụng Experiment, immutable source archive, hardware/config capture, nearest-rank statistics và reporting Phase 07. Implementation ở `backend/app/evaluation/agent.py`; không tạo tracker riêng. Chạy benchmark không đồng nghĩa có nhãn chất lượng.

## Phân loại bằng chứng

| Trạng thái | Cách dùng trong Prompt 09 |
| --- | --- |
| IMPLEMENTED | Code/schema/UI đã có; không tự suy ra đã chạy trên dữ liệu thật |
| TESTED_WITH_MOCKS | Unit doubles hoặc facts hư cấu; fixture chạy real stores vẫn không chứng minh facts/relevance thật |
| VERIFIED_WITH_REAL_DATA | Corpus 510 ảnh, retrieval/RAG/citation IDs và services đã kiểm tra thực thi |
| NOT_VERIFIED | Chất lượng multi-hop địa lý, Recall@10, faithfulness và task success trên nhãn người đánh giá |

Một tính năng có thể có nhiều loại bằng chứng. Báo cáo từng layer, không dùng positive fixture làm real-world search accuracy. Phase 08 human review vẫn chờ theo lựa chọn của người dùng.

## Metrics có nhãn

`evaluate_labeled_cases` yêu cầu labels có `fixture=true`, hoặc `human_verified=true` cùng annotator. Case IDs phải khớp đầy đủ. Ground truth được chuẩn bị từ import manifest/upload receipt trước execution, không rút từ output Agent.

| Metric | Định nghĩa trong evaluator |
| --- | --- |
| Routing accuracy | Tỷ lệ selected search_mode trùng expected mode |
| Tool selection accuracy | Tỷ lệ sequence tools trùng expected sequence |
| Entity resolution accuracy | Tỷ lệ case có tập entity IDs khớp hoàn toàn |
| Relationship resolution accuracy | Tỷ lệ case có tập evidence IDs khớp hoàn toàn |
| Expected image identity match | Tập image IDs đúng fixture/labels; không thay thế relevance |
| Workflow success | Status đúng expected status, bao gồm insufficient-evidence đúng kỳ vọng |

Mẫu số là số cases có expected labels đầy đủ; tập rỗng không chia cho0 mà trả null. Fixture output luôn có `real_world_retrieval_accuracy=null`. Chưa có human labels multi-hop; các metric thật trên chưa được công bố. `query_success` runtime chỉ phản ánh execution structure, không phải evaluator label.

## Benchmark latency A1–A4

| Config | Workload | Mục đích |
| --- | --- | --- |
| A1 | Core text “a dog outdoors”, không Agent | Đối chiếu fast path |
| A2 | Relational Hoan Kiem, deterministic | Đo planning và abstention trên KB thật trống |
| A3 | Cùng relational query, LLM planning | Đo chi phí JSON planning và validate; vẫn thiếu facts |
| A4 | Agent semantic dog + RAG | Đo retrieval + optional generation thật |

CLI `app.cli.agent --requests 16 --include-llm` xen kẽ mỗi config4 lần, concurrency1, giữ mọi HTTP/tool/timeout failure trong raw JSON. A1/A4 có cùng query ảnh, A2/A3 là task quan hệ khác: không xếp hạng chất lượng hoặc tuyên bố A2 nhanh hơn search trên cùng bài toán. N nhỏ và tải provider/network không kiểm soát; percentile chỉ thăm dò.

Lưu raw responses/traces, request config, runtime index/model manifest, source SHA, planner prompt SHA/model/usage, full-client ms. Agent latency decomposition có routing, planning, tools và aggregation; RAG có provider TTFT/TTLast và TTLast tính từ Agent request bằng offset bắt đầu RAG. Timing không quan sát được để null. HTTP sample có timer complete response riêng; không lấy processing_ms làm complete request.

## Tái lập

```bash
# Venv đã sync; Docker/Node/Chromium theo SETUP.
bash scripts/verification/verify_agent.sh --output docs/verification/phase09/new_run
backend/.venv/bin/python scripts/verification/verify_agent_fixtures.py --llm --output docs/verification/phase09/new_fixture
PYTHONPATH=backend backend/.venv/bin/python scripts/run_local.py --env-file .env -- \
  backend/.venv/bin/python -m app.cli.agent --include-llm --requests 16
```

Host imports CLI cần `PYTHONPATH=backend`. Fixture helper cần Docker access và đọc IP network nội bộ, không publish DB ports, không in environment. Bỏ `--llm` để chỉ kiểm thử deterministic; token/provider chỉ lấy từ `.env`, không truyền key trên command line. Thư mục output mới là bắt buộc để bảo toàn bằng chứng trước.

Fast regression dùng frozen `phase08_coco_v2` manifest/queries và config `phase08_coco_fast.json` (500 measured requests, concurrency1); ghi kết quả trong `evaluation/results/phase09`, không ghi đè Phase 08. Báo cáo CSV/Markdown/PNG/SVG ở `evaluation/reports/phase09_20261106`. Đọc [AGENT_PERFORMANCE](AGENT_PERFORMANCE.md) cho kết quả đã đo và [PHASE09_TEST_REPORT](../archive/PHASE09_TEST_REPORT.md) cho danh sách tests thực chạy.

## Bổ sung kiểm chứng với nguồn thật và metrics lỗi

`evaluate_labeled_cases` nhận thêm source_verified với SHA-256 manifest hợp lệ và danh sách HTTPS source URLs. Classification là source_verified_workflow; không chuyển thành human-verified relevance và vẫn để real_world_retrieval_accuracy=null. Helper `scripts/verification/verify_public_agent.py` tạo expected IDs từ catalog/import receipts trước request, kiểm tra bytes ảnh API và chạy English/Vietnamese/alias/missing/filter/LLM/RAG cases. Các metrics exact-ID workflow này không thay Recall@10/nDCG hay human faithfulness.

Benchmark A2/A3 giờ nhận `--relational-query`, để đo workload quan hệ có facts thật thay cho chỉ abstention. Run hoàn thiện dùng Washington Monument; A1/A4 vẫn dùng dog query, nên các nhóm vẫn là hai task khác nhau. `planner_failed_attempts`, `planner_timeout_attempts`, per-attempt latency và transport_timeout được lưu. `generation_target_3s` tách số mẫu đạt/vượt/thiếu timing; `explanations_with_citations` tách khỏi số provider responses generated hợp lệ. Mọi HTTP/timeout/failure vẫn trong raw và client latency denominator. Raw trước ở results/phase09 giữ nguyên; lượt hoàn thiện ghi results/phase09_completion.

Benchmark có --min-interval-seconds (0…30) để hạn chế offered rate khi provider có quota. Khoảng chờ chỉ nằm giữa requests của CLI, không tính vào request latency; duration_seconds_including_pacing và config được lưu. Lượt burst40 đã gặp LLM_RATE_LIMITED, giữ nguyên raw. Lượt paced dùng5 giây giữa HTTP starts, không đảm bảo quota account vì quota tùy dịch vụ. Provider/Planner không retry ngay429; retry cấu hình chỉ dành cho500/502/503, luôn trong request deadline.
