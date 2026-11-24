# Dataset và công cụ gán nhãn — Phase 07

Cập nhật06/11/2026: đã có corpus510 ảnh/500 captions; phần mềm đạt152 backend tests,13 frontend unit và16 browser cases. Human quality review chờ xác nhận theo lựa chọn của người dùng. [Báo cáo hiện hành](../archive/PHASE08_COMPLETION_REPORT.md); các số liệu05/11 bên dưới là lịch sử. Không tự chuyển Phase 09.

Corpus đang dùng10 ảnh scikit-image-v0.25.2, license/provenance tại [sample manifest](../../datasets/sample_manifest.json). Không tải COCO/Flickr hoặc corpus lớn trong phase này. Dataset nhỏ chỉ phù hợp functional/research smoke, không đại diện semantic retrieval thực tế. Exact hash dedup không thay perceptual duplicate review; khả năng public sample images xuất hiện trong pretraining chưa được audit.

## Snapshots và query set

[Frozen dataset](../../evaluation/datasets/manifests/phase07_v1.json) ghi actual UUID/SHA256/dimensions/license/content cache và active model/index; private API được dùng kiểm ảnh available/ready/content. CLI verify_index và real integration kiểm vector/object receipts, index/model manifests. Không dùng IDs minh họa làm actual corpus.

[Query set](../../evaluation/queries/phase07_v1.jsonl) có28 cases:12 single-intent EN/VI,10 multi-intent EN/VI gồm2/3/4 conditions, AND/OR/required/optional,4 exact-identity image cases,2 paired text+image EN/VI. Các case là inputs chờ đánh giá, **không là relevance labels** hoặc bảo đảm có đáp án. Một số paired background-edit scenarios có thể không có target trong corpus.

Family split giữ các bản dịch/variations cùng partition: coffee/cat/horse dev, camera/rocket/hubble test. Đây là query-family split, không phải trained-model image split; corpus truy xuất dùng chung và không fine-tune encoder. Chưa có semantic held-out quality claim. Trước nghiên cứu corpus lớn cần annotator review near duplicates, query ambiguity, translation equivalence và coverage.

## Trang gán nhãn local

Đã tạo `.cache/evaluation/annotation.html`:24 semantic queries×10 images, không hiển thị model scores/ranking hoặc tự điền grades. Có query selector, reference preview, grade0/1/2, per-clause true/false/unknown, overall required logic và explicit no-answer. Đầu vào từ actual private image content; thumbnails embedded, không có API token trong HTML. Trang mở offline, không publish dữ liệu hoặc thêm network service.

Xuất bản nháp luôn human_verified=false. Muốn xuất verified phải điền đủ judgments, tên annotator/version, xác nhận no-answer khi không có grade≥2 và tick xác nhận review. Không tự lưu trình duyệt; dùng Xuất bản nháp trước khi đóng, Nạp bản nháp để tiếp tục. Xuất verified từ UI là lời xác nhận của người dùng, không phải chữ ký mật mã. CLI tiếp tục validate snapshot/query hashes và coverage trước đo quality.

```bash
backend/.venv/bin/python scripts/run_local.py --env-file .env -- backend/.venv/bin/python -m app.cli.evaluation prepare
backend/.venv/bin/python -m app.cli.evaluation annotation-pack
backend/.venv/bin/python -m app.cli.evaluation validate-labels --labels PATH_TO_REVIEWED_LABELS.json
```

prepare dùng exclusive outputs: khi snapshot/query files đã tồn tại, chọn --output/--queries phiên bản mới thay vì overwrite. Cache images/HTML chứa dữ liệu private nên bị Git/Docker ignore, HTML mode0600. Fresh clone cần tải/index sample theo Phase 04 trước; .cache không được đóng gói vào source. Mở HTML bằng trình duyệt local, gán nhãn và giữ exported file; không gửi secret hoặc API token vào labels.

## Label schema và trạng thái hiện tại

Nhãn lưu dataset_sha256/query_set_sha256, annotator/label_version/reviewed_at_utc, exhaustive_judgments và human_verified; mỗi semantic query có exhaustive grades trên corpus, optional per-constraint/overall judgments và allow_no_answer. Null human truth là chưa đủ bằng chứng, không được đổi thành negative. Labels thiếu/mismatch/invalid references bị reject; model-independent identity task tách riêng.

Người dùng xác nhận hiện **chưa có bộ nhãn**, yêu cầu tạo công cụ trước. Vì vậy semantic Recall/nDCG/constraint quality còn chờ người đánh giá; software tests/identity checks không đóng quality gate. Hướng dẫn toán và denominators tại [EVALUATION_METHODOLOGY](EVALUATION_METHODOLOGY.md).
