# Constraint-aware reranking — Prompt 06

Đã có protocol Reranker và LightweightReranker trong `backend/app/services/search/reranker.py`. Không tải thêm model hoặc gọi vision-language/LLM provider. Rerank off mặc định/request; chỉ chạy khi enabled và server RERANKING_ENABLED=true.

## Scoring đã triển khai

Batch retrieve stored vectors cho selected candidates, verify mỗi vector SHA với ready image_embedding receipt, dimension/finite/L2 theo pinned index. Tính actual dot cosine với whole-query và tất cả semantic clause vectors đã batch encode. Không dùng cosine thiếu ở retrieval branch làm0 rồi giả là actual similarity.

Mỗi cosine đổi thang `[−1,1]→[0,1]` bằng `(clip(c,-1,1)+1)/2`. Với paired query, whole signal là text/image cosine mean theo normalized modality weights; giữ riêng branch contributions nên image signal vẫn tham gia khi bật rerank. Đây là comparable ordering signals cùng space, không calibration.

Required semantic leaf dùng changed-scale cosine; negated leaf dùng1−value như **soft penalty**, evidence vẫn UNKNOWN. Theo AST: AND relevance=(minimum+weighted mean)/2, OR relevance=maximum; metadata leaves không giả thành cosine. Leaf weight cấu hình trong AST áp dụng mean. Optional semantic preferences weighted mean riêng, blend vào constraint score theo RERANK_OPTIONAL_WEIGHT(default0.1). Không có required semantic signal thì dùng whole signal làm nền.

Verified metadata component là fraction assessments metadata satisfied; UNKNOWN không thành false negative hoặc verified mismatch, chỉ không nhận positive reward. Required penalties: min(1, unknown_count×0.02 + violated_count×0.25) mặc định. Hard required Boolean gate đã chạy độc lập trước scoring; OR có nhánh mismatch vẫn có thể hợp lệ khi nhánh khác satisfied.

Final ordering score: `max(0,(w_whole*whole + w_constraint*constraint + w_metadata*metadata)/sum(weights) - penalty)`, weights mặc định0.4/0.4/0.2, typed/configurable, tổng phải>0. Các weights/penalties chưa được tune bằng human labels. Không quảng bá là relevance probability hoặc chất lượng cải thiện đã chứng minh. Response có score_components, score_type=reranker, version constraint-linear-v1, assessments và contributing branches.

## Bounds và failure policy

Rerank candidate limit mặc định50, server range1…100; request có thể giảm nhưng không tăng vượt server, và phải≥K. Chỉ selected prefix được rerank rồi trả, không trộn raw RRF và rerank score trong cùng response. Pool/candidate limits và rerank_applied được báo trong effective_settings. Budget mặc định200ms, request1…1.000ms; timeout bao gồm stored vector fetch và local scoring. Full ASGI deadline2s vẫn cao nhất.

Rerank local scoring nhỏ/bounded và có deadline checkpoint trước publish. Successful result chỉ được publish sau complete scoring, không để partial mutation đổi baseline khi fallback. Digest/model mismatch409 không fallback; dependency/runtime/timeout lỗi theo rerank.on_failure: error(default)→503 RERANK_FAILED, skip→baseline fusion/rescore + RERANK_SKIPPED warning. Basic single-vector search không gọi reranker, nên reranker lỗi không làm basic search unavailable. Cancellation/inference slot policy Prompt05 giữ nguyên.

## Evidence và evaluation

Không có detector hoặc exhaustive object annotations, nên object/color/action/spatial/absence constraints đều UNKNOWN kể cả cosine cao. Metadata chỉ verify predicate trên metadata, không tự chứng minh toàn bộ nội dung thị giác. Strict required semantic constraints bị từ chối409 VERIFIER_UNAVAILABLE; optional unknown vẫn được ghi rõ.

Quality cần human exhaustive corpus judgments, per-constraint true/false/unknown và overall logical-query satisfaction; không sinh label từ CLIP scores hoặc filenames. [Evaluation README](../../evaluation/README.md) mô tả accuracy với abstention coverage và E1–E5. Không có qrels nên chưa thể kết luận Recall/nDCG hoặc lợi ích rerank. [Báo cáo](../archive/ADVANCED_SEARCH_TEST_REPORT.md) ghi latency thực, tests và bottlenecks; không so RRF numeric score trực tiếp với cosine hay reranker score để suy quality.
