# Kết quả thí nghiệm retrieval và RAG

Số đo từ raw artifacts; latency successful-only đi kèm số lỗi. Không cộng component percentiles hoặc suy SLA từ corpus nhỏ.

| Experiment | Status | N / errors | P90 ms | P95 ms | Success req/s |
| --- | --- | --- | --- | --- | --- |
| rag | measured | None / None | None | None | None |
| fast_default_head1 | measured | 500 / 0 | 144.58679400013352 | 153.16672700009804 | 8.639774330205965 |
| rag | measured | None / None | None | None | None |

## RAG: số đo thực, tách failures khỏi generated latency

| Run / cấu hình | N / generated / unavailable | Client P90 ms | Provider TTFT P90 ms | Request TTLast P90 ms |
| --- | --- | --- | --- | --- |
| 20261105T042632_rag_37780e9449 / R1 | 5 / 0 / 0 | 103.42 | — | — |
| 20261105T042632_rag_37780e9449 / R2 | 5 / 0 / 0 | 135.88 | — | — |
| 20261105T042632_rag_37780e9449 / R3 | 5 / 3 / 2 | 5261.02 | 4353.80 | 4699.60 |
| 20261105T042632_rag_37780e9449 / R4 | 5 / 0 / 5 | 5207.81 | — | — |
| 20261105T050046_rag_4b6c513c95 / R1 | 5 / 0 / 0 | 87.14 | — | — |
| 20261105T050046_rag_4b6c513c95 / R2 | 5 / 0 / 0 | 142.83 | — | — |
| 20261105T050046_rag_4b6c513c95 / R3 | 5 / 5 / 0 | 2151.82 | 1845.20 | 2122.30 |
| 20261105T050046_rag_4b6c513c95 / R4 | 5 / 5 / 0 | 3673.09 | 3448.03 | 3643.47 |

TTFT/TTLast chỉ trên generated requests; unavailable không bị bỏ khỏi counts. N nhỏ, không là production SLA proof. Xem rag_cases.csv/JSON cho per-case audits.

## Chất lượng và giới hạn

Không tự tạo human judgments; thiếu nhãn phải giữ unavailable. Identity/ANN overlap không thay semantic quality. Không có GPU comparison khi thiếu GPU.

## Provenance

- `20261105T042632_rag_37780e9449` → [raw artifact](../../results/phase08/20261105T042632_rag_37780e9449/result.json)
- `20261105T043305_benchmark_38092a56a4` → [raw artifact](../../results/phase08/20261105T043305_benchmark_38092a56a4/result.json)
- `20261105T050046_rag_4b6c513c95` → [raw artifact](../../results/phase08/20261105T050046_rag_4b6c513c95/result.json)
