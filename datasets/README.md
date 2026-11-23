# Dataset nghiệm thu indexing

Prompt 04 dùng 10 ảnh thật từ scikit-image v0.25.2, gồm camera, brick, grass, gravel, coffee, chelsea, horse, rocket, clock_motion và hubble_deep_field. Từng ảnh có CC0/public-domain được ghi rõ trong upstream `_fetchers.py`; xem [manifest](sample_manifest.json) cho URL, SHA-256 và rights reference từng file. Không tạo caption hoặc tags giả; đây là fixtures kỹ thuật, chưa là corpus đánh giá retrieval.

Tải có chủ đích từ project root: `python3 scripts/download_sample_dataset.py`. Script kiểm tra SHA-256 từ registry upstream và từ chối overwrite file khác bytes. File ảnh nằm `datasets/sample/`, được ignore; model weights nằm `.cache/clip/`, cũng được ignore. Tests không tự tải mạng. Không có dataset thì cài theo bước trên hoặc cung cấp dữ liệu local có quyền sử dụng.

Dataset riêng phải nằm trong DATASET_ROOT allowlist của CLI, tối đa 1.000 ảnh/lượt. CLI duyệt recursive JPEG/PNG/WebP, không theo symlink và không nhận URL fetch tùy ý. `metadata.jsonl` optional dùng mỗi dòng `{filename,source_dataset,source_uri?,license,rights_ref,title?,description?,caption?,tags?}`; filename tương đối trong dataset. License/provenance phải được operator xác nhận; không dùng user data chưa xác nhận privacy.

Ảnh gốc giữ nguyên bytes/EXIF trong bucket private. Content proxy có thể trả original có EXIF; không đưa ảnh chứa thông tin nhạy cảm vào fixture này. Processor strip metadata và không thay bản gốc.

Prompt08 bổ sung downloader COCO500 có caption/provenance và collection mới; hướng dẫn tại [RAG_DATASET](../docs/RAG_DATASET.md). JPEG/raw annotations không đưa lên Git.

## Địa danh NPS Prompt09

`landmarks_phase09_v1/` chứa ba JPEG từ NPS và manifest/metadata có checksum, credit, URL nguồn và rendition policy. Raw ảnh ignored, catalog/provenance công khai nằm evaluation/agent/datasets. [PUBLIC_LANDMARK_DATASET](../docs/PUBLIC_LANDMARK_DATASET.md) ghi giấy phép và quan hệ nguồn. Không dùng fixture hay metadata labels như human relevance judgments.
