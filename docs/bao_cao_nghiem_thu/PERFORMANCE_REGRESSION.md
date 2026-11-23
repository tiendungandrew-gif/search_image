# Hồi quy hiệu năng — Phase11

> Tài liệu lịch sử theo phase; lệnh trong nội dung giữ tên đường dẫn cũ. Hướng dẫn hiện hành tại [danh mục tài liệu](../README.md) và [scripts](../../scripts/README.md).

Tái sử dụng `app.evaluation.benchmark` và `app.evaluation.agent` từ Phase07/09, không tạo load framework khác. Artifacts: [performance.json](../verification/phase11/performance.json) và [evaluation/results/phase11](../../evaluation/results/phase11), có source archive/hash, query/dataset hash, config, runtime, raw samples và failures.

## Môi trường và workload

CPU Intel Core7 240H/16 logical CPUs, RAM khoảng15GiB, CLIP ViT-B/32 CPU4 threads, dimension512; active generation3 giữ nguyên513 ảnh. Model revision `3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268`, manifest `7f843c0bf81c571eee3b12621fc41811cea174113e6802684e9063b447e707dc`.

Frozen snapshot `phase09_public_v1`, query hash `fcbc3c2ac9979f7db8222b28dbe314d75ab8f50c6ee138d466a23785eb3b5dfe`; dataset hash `780aa0b608938c0e1724dc28a370807f0ec47200183d22e0d32756631945b93a`. TopK10/candidates50/seed42, warm model/pools, không query-result cache; OS cache và tải provider không kiểm soát. Latency dưới đây là server ASGI complete của **request thành công**, failures được ghi cạnh mẫu số.

| Workload | Thành công/tổng | P50 ms | P90 ms | P95 ms | Success req/s |
| --- | ---: | ---: | ---: | ---: | ---: |
| Fast C1, warmup12 | 500/500 | 87,33 | 128,55 | 135,45 | 11,10 |
| Image C1, warmup4 | 24/24 | 129,38 | 139,19 | 141,28 | 7,50 |
| Multi-intent C1, warmup4 | 30/30 | 94,62 | 144,89 | 180,47 | 9,36 |
| Multimodal C1, warmup4 | 24/24 | 146,31 | 184,81 | 216,30 | 6,42 |
| Fast C4, warmup8 | 97/100 | 122,65 | 150,67 | 159,22 | 30,34 |

Fast C4 có **3 HTTP503 INFERENCE_BUSY /100**, error rate3%; không timeout. Hàng chờ có deadline50ms và chỉ một inference thread; đây là backpressure đang cấu hình, không phải100% availability ở C4. Không báo latency của97 successes là latency của toàn bộ100 requests. Cần capacity/load profile đại diện trước production.

Fast C1 baseline Phase09 cùng corpus/query/config/hardware: server P90132,01/P95137,41ms; Phase11 tương ứng128,55/135,45ms, không thấy hồi quy ở phép đo này. Source khác và tải OS không khóa nên không kết luận cải thiện có ý nghĩa thống kê từ một cặp run. Baseline `20261106T151820_benchmark_5b73a0ef43`, run hiện tại `20261107T143422_benchmark_5578dfc6d7`. Target P90≤300/P95≤500ms được quan sát trên workload513 ảnh/C1 này; **production retrieval performance NOT_VERIFIED**. Image/advanced có N nhỏ, chỉ thăm dò.

## Agent và Gemini thật

Run `20261107T143609_agent_b1bc6010eb`:8 requests, C1, mỗi request cách tối thiểu5s,2 mẫu/mode. Gemini `gemini-3.5-flash-lite`, native provider, output budget128, minimal thinking. A1/A4 dùng cùng image query; A2/A3 dùng quan hệ Washington Monument→city→landmarks, không so trực tiếp như cùng một task.

| Mode | Kết quả thực | Client range ms | Thành phần đáng chú ý |
| --- | --- | ---: | --- |
| A1 fast trực tiếp | 2/2 HTTP thành công | 38,76–77,79 | Không planner/LLM |
| A2 deterministic multi-hop | 2/2 query_success | 210,13–222,86 | 4 tools/3 logical hops; tools88,55–101,27ms |
| A3 LLM multi-hop | 2/2 query_success sau retry | 5734,03–7097,95 | 4 planner attempts,2 attempt timeout; planning5510,44–6888,31ms |
| A4 Agent+RAG | 2/2 generated/citations | 6498,25–6874,50 | TTFT6015,89–6420,04ms; request TTLast6367,66–6744,84ms |

**Generation target3s:0/2 đạt,2/2 vượt.** Không bỏ hai planner first-attempt timeouts vì HTTP cuối200. N=2/mode không đủ làm percentile/SLA; số đo chỉ chứng minh integration và giới hạn quan sát. Không tự nới deadline/model để làm báo cáo xanh. Human relevance/faithfulness vẫn chưa được chấm; exact citation audit không thay cho độ đúng ngữ nghĩa.

## Chạy lại

Với API và frozen corpus tương ứng đang chạy, token chỉ được nạp trong child environment:

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/run_local.py --env-file .env -- backend/.venv/bin/python -m app.cli.evaluation --results evaluation/results/phase11 benchmark --snapshot evaluation/datasets/manifests/phase09_public_v1.json --queries evaluation/queries/phase09_public_v1.jsonl --config evaluation/experiments/phase08_coco_fast.json
```

Thay config bằng `phase11_image.json`, `phase11_multi_intent.json`, `phase11_multimodal.json`, `phase11_fast_c4.json` cho workload riêng. Không chạy các phép đo đồng thời. CLI tạo run directory mới, không ghi đè artifacts. Nếu corpus/index đã đổi cần snapshot mới; không dùng số này cho index khác. Frontend Phase10 performance artifacts được giữ làm lịch sử; Phase11 đã build/type/unit/E2E nhưng không chạy lại UI percentile20samples.
