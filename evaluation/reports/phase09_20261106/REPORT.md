# Kết quả thí nghiệm retrieval và RAG

Số đo từ raw artifacts; latency successful-only đi kèm số lỗi. Không cộng component percentiles hoặc suy SLA từ corpus nhỏ.

| Experiment | Status | N / errors | P90 ms | P95 ms | Success req/s |
| --- | --- | --- | --- | --- | --- |
| agent | measured | 16 / 0 | None | None | None |
| agent | measured | 16 / 0 | None | None | None |
| phase08_coco_fast | measured | 500 / 0 | 135.03121100006865 | 140.9790879999946 | 7.928088425018527 |

## Chất lượng và giới hạn

Không tự tạo human judgments; thiếu nhãn phải giữ unavailable. Identity/ANN overlap không thay semantic quality. Không có GPU comparison khi thiếu GPU.

## Provenance

- `20261106T051238_agent_62f3a5e779` → [raw artifact](../../results/phase09/20261106T051238_agent_62f3a5e779/result.json)
- `20261106T071208_agent_ff7910da71` → [raw artifact](../../results/phase09/20261106T071208_agent_ff7910da71/result.json)
- `20261106T071236_benchmark_7f9efe9e00` → [raw artifact](../../results/phase09/20261106T071236_benchmark_7f9efe9e00/result.json)

## Agent: thời gian thực thi và abstention, chưa có real-world quality labels

| Nhóm / experiment | N / HTTP errors / insufficient | Client P90 ms | Plan P90 ms | Mean hops / calls |
| --- | --- | --- | --- | --- |
| A1 / 20261106T051238_agent_62f3a5e779 | 4 / 0 / 0 | 140.73 | — | 0.00 / 0.00 |
| A2 / 20261106T051238_agent_62f3a5e779 | 4 / 0 / 4 | 29.33 | 0.6318269988696557 | 0.00 / 1.00 |
| A3 / 20261106T051238_agent_62f3a5e779 | 4 / 0 / 4 | 2389.68 | 2371.3432929998817 | 0.00 / 1.00 |
| A4 / 20261106T051238_agent_62f3a5e779 | 4 / 0 / 0 | 1617.61 | 0.12727000103041064 | 1.00 / 2.00 |
| A1 / 20261106T071208_agent_ff7910da71 | 4 / 0 / 0 | 127.59 | — | 0.00 / 0.00 |
| A2 / 20261106T071208_agent_ff7910da71 | 4 / 0 / 4 | 28.55 | 0.5859010000222042 | 0.00 / 1.00 |
| A3 / 20261106T071208_agent_ff7910da71 | 4 / 0 / 4 | 6540.66 | 6521.363873999917 | 0.00 / 1.00 |
| A4 / 20261106T071208_agent_ff7910da71 | 4 / 0 / 0 | 4513.13 | 0.10945999997602485 | 1.00 / 2.00 |

A2/A3 chưa có quan hệ thật nên trả thiếu bằng chứng; không là multi-hop accuracy. A1/A4 dùng cùng image query, khác task với A2/A3. Xem agent_cases.csv và raw JSON để giữ mọi failure. Không có human quality bars khi thiếu nhãn.
