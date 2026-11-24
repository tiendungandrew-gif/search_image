# Hiệu năng Agent — hoàn thiện Phase 09

Số đo ngày 06/11/2026. Corpus 513 ảnh, CLIP512 CPU, active index `b4597021-4b91-491d-99ae-0617a6ca389c`, generation 3. Có4 entities/3 relations/3 image links nguồn NPS. Index510 trước đó được giữ; manifest CLIP/preprocessing/locks không đổi. [Audit](../verification/phase09_completion_20261106/final_audit.json), [dataset và giấy phép](PUBLIC_LANDMARK_DATASET.md).

## Fast Search độc lập

500/500 thành công, 0 lỗi. Complete-server P90 **132.01ms**, P95 **137.41ms**; client P90 136.61ms. Target P90≤300ms được quan sát đạt trong lượt local này. Config seed42/warmup12/measured500/concurrency1, cùng profile trước nhưng snapshot tăng từ510 lên513 ảnh; không suy causal speedup từ thay đổi nhỏ giữa các lượt.

[Raw Fast Search](../../evaluation/results/phase09_completion/20261106T151820_benchmark_5b73a0ef43/result.json), snapshot [phase09_public_v1](../../evaluation/datasets/manifests/phase09_public_v1.json). Không có nhãn người đánh giá nên không báo Recall@10 hoặc nDCG.

## A1–A4 có pacing

Run `20261106T163330_agent_e4900bc334`,40 requests,10 mỗi nhóm, concurrency1, tối thiểu5 giây giữa HTTP request starts. Khoảng chờ CLI không được tính vào latency một request; duration_seconds_including_pacing=196.35s được lưu riêng. Điều này kiểm soát offered rate, không thay đổi server deadline để đạt target. Không có workload khác cố ý chạy cùng lúc.

| Nhóm | N | Planning P90 ms | Tools P90 ms | Mean hops/calls | Client P90 ms | Failed/partial/HTTP lỗi |
| --- | --- | --- | --- | --- | --- | --- |
| A1 | 10 | — | — | 0.0/0.0 | 91.46 | 0/0/0 |
| A2 | 10 | 0.53 | 122.03 | 3.0/4.0 | 256.56 | 0/0/0 |
| A3 | 10 | 2225.08 | 131.51 | 3.0/4.0 | 2480.18 | 0/0/0 |
| A4 | 10 | 0.18 | 1684.65 | 1.0/2.0 | 1858.18 | 0/0/0 |

A1 core dog query; A2 deterministic query landmarks in city where Washington Monument is located; A3 cùng relational query với Gemini JSON planner; A4 Agent dog query + RAG. A1/A4 là cùng task ảnh, A2/A3 là task quan hệ khác. A2/A3 chạy trên facts thật, không còn là phép đo chỉ abstention. A3 validated plans 10/10; structural query success 10/10. Những tỷ lệ execution này không là relevance accuracy.

## Generation, failures và target 3s

A4 generated=10/10, có citations=10/10. Provider TTFT P90 **1446.17ms**; Agent-request TTLast P90 **1730.99ms**. Target 3s: 10/10 generated samples đạt, 0 vượt; thiếu timing=0. Không có HTTP/execution/partial failures trong run paced. N=10 mỗi nhóm chỉ là quan sát thăm dò; không cam kết SLA trên mọi query, tải hoặc quota account.

Các bảng zero timeouts bao gồm planner attempt timeout, tool/overall timeout và transport timeout; per-attempt trace lưu lỗi đã phục hồi. Không cộng component percentiles. All-attempt client latency giữ failures trong mẫu số; generation TTFT/TTLast chỉ tính các responses generated và kèm số unavailable.

## Lượt burst được giữ nguyên

Run `20261106T151742_agent_081d6bdb0d` cũng40 requests nhưng không pacing. A3 có2 failures do Gemini429; A4 có2 partial do quota và giữ ảnh. A4 generated8/10; TTLast P90 1666.95ms chỉ trên các lượt generated. Không coi hai lượt unavailable là samples đạt3s. Không gộp burst và paced để che tác động offered rate.

Sau khi quan sát quota, provider và planner đã bỏ immediate retry/replan cho429; vẫn cho bounded retry500/502/503 trong deadline. UI phân biệt quota với thiếu facts; SSE cảnh báo RAG có retrieval_preserved không làm mất terminal partial/images. Các lỗi burst và run cũ đều còn trong raw, không retry tới xanh rồi xóa failures.

## Tối ưu và giới hạn

Prompt planner v2 bỏ full tool schemas lặp trong provider input nhưng server vẫn validate full contracts. Một cặp quan sát provider usage cho thấy prompt từ2422 xuống540 tokens; query/điều kiện của hai lượt khác nhau nên không là controlled causal ablation. Agent RAG compact chỉ gửi fact_id/field/quote, giữ UUID/provenance trên server để kiểm tra citations. Không đổi CLIP/index dimension hoặc áp dụng content cache để che latency.

Chưa đánh giá độ ổn định dài hạn, concurrency cao, nhiều city/domain hoặc human faithfulness. Quota dịch vụ ngoài vẫn có thể gây partial/failure; deterministic workflow không cần LLM. [Raw/CSV/PNG/SVG](../../evaluation/reports/phase09_completion_20261106_final/REPORT.md), [phương pháp](AGENT_EVALUATION.md), [báo cáo nghiệm thu](../archive/PHASE09_TEST_REPORT.md). Các số đo trước 513 ảnh nằm trong [báo cáo cũ](../../evaluation/reports/phase09_20261106/REPORT.md).
