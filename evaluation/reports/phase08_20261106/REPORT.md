# Kết quả thí nghiệm retrieval và RAG

Số đo từ raw artifacts; latency successful-only đi kèm số lỗi. Không cộng component percentiles hoặc suy SLA từ corpus nhỏ.

| Experiment | Status | N / errors | P90 ms | P95 ms | Success req/s |
| --- | --- | --- | --- | --- | --- |
| rag | measured | None / None | None | None | None |
| phase08_coco_fast | measured | 500 / 0 | 142.88863599995238 | 153.56567399976484 | 7.591321217402684 |

## RAG: số đo thực, tách failures khỏi generated latency

| Run / cấu hình | N / generated / unavailable | Client P90 ms | Provider TTFT P90 ms | Request TTLast P90 ms |
| --- | --- | --- | --- | --- |
| 20261106T035619_rag_f1012fd73b / R1 | 8 / 0 / 0 | 140.90 | — | — |
| 20261106T035619_rag_f1012fd73b / R2 | 8 / 0 / 0 | 104.72 | — | — |
| 20261106T035619_rag_f1012fd73b / R3 | 8 / 8 / 0 | 1424.74 | 1158.48 | 1366.70 |
| 20261106T035619_rag_f1012fd73b / R4 | 8 / 8 / 0 | 2059.12 | 1808.86 | 1968.15 |

TTFT/TTLast chỉ trên generated requests; unavailable không bị bỏ khỏi counts. N nhỏ, không là production SLA proof. Xem rag_cases.csv/JSON cho per-case audits.

## Chất lượng và giới hạn

Không tự tạo human judgments; thiếu nhãn phải giữ unavailable. Identity/ANN overlap không thay semantic quality. Không có GPU comparison khi thiếu GPU.

## Provenance

- `20261106T035619_rag_f1012fd73b` → [raw artifact](../../results/phase08_completion/20261106T035619_rag_f1012fd73b/result.json)
- `20261106T040458_benchmark_2dc80f5824` → [raw artifact](../../results/phase08_completion/20261106T040458_benchmark_2dc80f5824/result.json)
