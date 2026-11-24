# Kết quả thí nghiệm Phase 07

Số đo từ raw artifacts; latency successful-only đi kèm số lỗi. Không cộng component percentiles hoặc suy SLA từ corpus nhỏ.

| Experiment | Status | N / errors | P90 ms | P95 ms | Success req/s |
| --- | --- | --- | --- | --- | --- |
| rag | measured | None / None | None | None | None |
| fast_default_head1 | measured | 500 / 0 | 144.58679400013352 | 153.16672700009804 | 8.639774330205965 |
| rag | measured | None / None | None | None | None |

## Chất lượng và giới hạn

Không tự tạo human judgments; thiếu nhãn phải giữ unavailable. Identity/ANN overlap không thay semantic quality. Không có GPU comparison khi thiếu GPU.

## Provenance

- `20261105T042632_rag_37780e9449` → [raw artifact](../../results/phase08/20261105T042632_rag_37780e9449/result.json)
- `20261105T043305_benchmark_38092a56a4` → [raw artifact](../../results/phase08/20261105T043305_benchmark_38092a56a4/result.json)
- `20261105T050046_rag_4b6c513c95` → [raw artifact](../../results/phase08/20261105T050046_rag_4b6c513c95/result.json)
