# Kết quả thí nghiệm retrieval và RAG

Số đo từ raw artifacts; latency successful-only đi kèm số lỗi. Không cộng component percentiles hoặc suy SLA từ corpus nhỏ.

| Experiment | Status | N / errors | P90 ms | P95 ms | Success req/s |
| --- | --- | --- | --- | --- | --- |
| agent | measured | 40 / 0 | None | None | None |
| phase08_coco_fast | measured | 500 / 0 | 132.0122450006238 | 137.40654299999733 | 8.003446551976662 |

## Chất lượng và giới hạn

Không tự tạo human judgments; thiếu nhãn phải giữ unavailable. Identity/ANN overlap không thay semantic quality. Không có GPU comparison khi thiếu GPU.

## Provenance

- `20261106T151742_agent_081d6bdb0d` → [raw artifact](../../results/phase09_completion/20261106T151742_agent_081d6bdb0d/result.json)
- `20261106T151820_benchmark_5b73a0ef43` → [raw artifact](../../results/phase09_completion/20261106T151820_benchmark_5b73a0ef43/result.json)

## Agent: thời gian thực thi và abstention, chưa có real-world quality labels

| Nhóm / experiment | N / HTTP errors / insufficient | Client P90 ms | Plan P90 ms | Mean hops / calls |
| --- | --- | --- | --- | --- |
| A1 / 20261106T151742_agent_081d6bdb0d | 10 / 0 / 0 | 127.45 | — | 0.00 / 0.00 |
| A2 / 20261106T151742_agent_081d6bdb0d | 10 / 0 / 0 | 276.82 | 0.5541609998545027 | 3.00 / 4.00 |
| A3 / 20261106T151742_agent_081d6bdb0d | 10 / 0 / 0 | 2014.35 | 1777.285744999972 | 2.40 / 3.20 |
| A4 / 20261106T151742_agent_081d6bdb0d | 10 / 0 / 0 | 1676.77 | 0.11838299997180002 | 1.00 / 2.00 |

A2/A3 dùng quan hệ thật nếu có trong kho; execution success không là relevance accuracy. A1/A4 dùng cùng image query, khác task với A2/A3. Xem agent_cases.csv và raw JSON để giữ mọi failure. Không có human quality bars khi thiếu nhãn.
