# Phương pháp đánh giá retrieval — Phase 07

Tách năm câu hỏi: relevance của ảnh, chất lượng thứ hạng, thỏa điều kiện, latency và reliability. Một response200, self-match hoặc ANN overlap không chứng minh semantic relevance. [Dataset/labels](DATASET_AND_GROUND_TRUTH.md), [load/latency](LATENCY_BENCHMARK.md), [ablation](ABLATION_STUDY.md) và [test report](../archive/PHASE07_TEST_REPORT.md) ghi scope/evidence.

## Relevance và ranking

Human grades0/1/2 nghĩa không liên quan/một phần/phù hợp rõ. Nhãn phải exhaustive trên frozen corpus; không dùng filename hoặc chính model scores để tạo nhãn. Binary relevant threshold Phase07 mặc địnhgrade≥2, được lưu trong label file; chọn1 nếu protocol yêu cầu và phải ghi rõ. Legacy metric caller mặc địnhgrade≥1 để giữ Phase05–06 tests/contracts. Graded nDCG vẫn dùng cả grade1 dù binary threshold2.

Recall@K=unique relevant hits trong positions1…K / toàn bộ relevant images của query. Precision@K=hits/K kể cả returned<K. Hit@K=1 nếu có ít nhất một relevant hit; không thay Recall khi có nhiều relevant images. MRR@10=1/rank relevant đầu tiên trong depth10,0 nếu không tìm thấy; không gọi unlimited-depth MRR. DCG@K=sum((2^grade−1)/log2(rank+1)); IDCG từ grades giảm dần trên corpus, nDCG=DCG/IDCG. K1/5/10 được triển khai, duplicate chỉ tính lần đầu và không compact positions để tăng điểm.

Strict evaluation reject unjudged IDs, invalid grades/bools/NaN và mismatched corpus/query/label hashes. No-answer phải được annotator xác nhận; không có relevant binary labels thì Recall/Precision/Hit/MRR đểnull và báo denominator riêng. IDCG0→nDCG null, không tự cho1; graded positives vẫn có nDCG dù không đạt binary threshold. Aggregates tách task/query_type/language/executed mode, ghi query_count và evaluated_queries từng metric; không gộp các tasks thành “accuracy” duy nhất.

## Điều kiện và missing evidence

Per-constraint human true/false/null và overall Boolean-query satisfaction là ground truth độc lập model. Model satisfied/violated/unknown được đối chiếu human truth; UNKNOWN là abstention, không success/mismatch. Accuracy trên verified predictions phải kèm verification coverage. Human UNKNOWN cũng không được coi là false: satisfaction denominator chỉ gồm known judgments và phải báo coverage. Top-K clause coverage dùng các clause có human labels; overall success cần một returned image được human xác nhận thỏa logic required. Optional preferences không tự thành mandatory.

Baseline không trả assessments vẫn có thể chấm human satisfaction từ returned IDs; thiếu assessments chỉ làm verification coverage unavailable. Strict semantic queries thiếu verifier vẫn409 theo Phase 06. Không suy điều kiện màu/vị trí/absence từ cosine hoặc parser.

## Identity và ANN là tasks riêng

Bốn image-query cases dùng exact byte identity với UUID/SHA256 trên corpus đã dedup. Có thể đo Hit/Recall/MRR cho **exact instance identity** bằng authoritative hashes mà không gán human semantic labels. Không trình bày các số này như chất lượng image similarity/semantic search. N10/K10 làm Recall@10 dễ bão hòa; không dùng nó để chọn model.

ANN-vs-exact overlap@K so returned IDs với Qdrant exact search trên cùng model/vector/filter. Không là relevance Recall@K. Với corpus10 và indexed_vectors_count nhỏ/0, query có thể dùng plain scan; không coi overlap1 là bằng chứng HNSW recall hoặc scalability.

## Thống kê và reproducibility

Quality comparisons yêu cầu cùng dataset/query/labels/eligible scope và paired query IDs. Seeded paired cluster bootstrap giữ các bản dịch/related queries trong cùng family khi resampling, ghi point delta/95% percentile CI/repetitions/group count. Thiếu independent groups thì unavailable; không bootstrap nhãn không tồn tại. Latency block bootstrap mô tả successful-request P90 và autocorrelation block size, không là production SLA confidence.

Experiment lưu UTC ID, config, source hash/archive, Git commit hoặc lý do unavailable, dataset/query/label SHA, model/index manifest, hardware/runtime/cache/concurrency, warmup/failure counts và raw measurements. Thư mục dùng UUID/exclusive writes, không ghi đè trước đó. Source archive là fallback khi workspace chưa có commit hoặc runtime không cài git. Labels/dev-test split freeze trước tuning; hiện chưa có human semantic labels để tune hoặc claim quality improvement.
