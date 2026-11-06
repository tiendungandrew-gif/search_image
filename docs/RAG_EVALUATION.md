# Đánh giá RAG — Prompt08

R1: API Semantic Search thật không gọi LLM. R2: metadata baseline hiển thị thông tin có thật, không giả thành câu do LLM tạo. R3: Gemini chọn facts trên context bounded. R4: cùng query/task/language nhưng evidence cap1 thay3. R5 vision-grounded chưa triển khai, không có số giả.

Đo độc lập HTTP failures/generation unavailable/insufficient/generated, latency client/provider TTFT/TTLast, citation ID validity và exact quote support. Citation validity chỉ chứng minh ID/field/giá trị tồn tại, không thay faithfulness thị giác hoặc answer relevance. Không ghi100% cho trường không có citations; denominator0→null. Token usage ghi số provider trả; không tính chi phí khi chưa có pricing/version được xác minh.

Các bản ghi đã đóng băng cần người đánh giá chấm answer relevance0/1/2, faithfulness0/1/2 và unsupported_claims/claims; human_verified/annotator bắt buộc. validate_review từ chối nhãn thiếu/invalid counts; không dùng model score hoặc LLM tự chấm làm ground truth. VI/EN được chạy riêng, query-family/label versions phải giữ khi nghiên cứu tiếp. Không có nhãn human nên semantic answer quality/unsupported semantic claim rate để chưa đo. Exact quotes được kiểm bằng code và tests, không gọi đó là human-reviewed quality.

```bash
backend/.venv/bin/python scripts/run_local.py --env-file .env -- backend/.venv/bin/python -m app.cli.rag --requests 20
bash scripts/verify_rag.sh
```

CLI dùng Experiment Prompt07, immutable UTC/UUID dirs/source archive; không ghi đè phase trước. Chỉ gọi API backend, không đọc key LLM ở CLI benchmark. Kết quả có raw responses, settings/model/prompt versions, counts và grouped timing. Sample20 là exploratory, không production confidence/SLA proof; lỗi/timeout đầu và model probes được giữ riêng tại docs/verification/phase08. RAG không thay Recall/MRR/nDCG retrieval; bộ nhãn relevance Prompt07 vẫn chưa có.

Human review chỉ chấm R3/R4, tách theo configuration/language, không gộp search-only R1 hoặc metadata-only R2 vào answer quality. Grade null là chưa có đánh giá, được loại khỏi mean với evaluated_cases riêng; claims/unsupported_claims phải là counts do reviewer kiểm. CLI yêu cầu result_sha256 của frozen output trước validate.

## Artifacts và human review

[Báo cáo tự sinh](../evaluation/reports/phase08_20261105/REPORT.md), rag_cases.csv có40 rows/2 matrices; raw results lưu nguyên. [Template chưa review](../evaluation/rag/reviews/template_phase08_native.json) tham chiếu frozen native experiment `20261105T050046_rag_4b6c513c95`. Người đánh giá phải điền counts/grades và tên/version/time, tự xác nhận human_verified sau review; không đổi cờ để chạy thử. CLI --review yêu cầu result_sha256 trùng đúng raw result, chỉ chấmR3/R4 và báo missing denominators riêng. Template bị từ chối như mong đợi khi chưa có review.
