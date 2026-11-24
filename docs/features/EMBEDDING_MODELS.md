# Embedding model và preprocessing

Phase 04 dùng pretrained `openai/clip-vit-base-patch32`, immutable revision `3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268`. [Model card](https://huggingface.co/openai/clip-vit-base-patch32/blob/3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268/README.md) ghi mục đích nghiên cứu và giới hạn đánh giá; [upstream license](https://github.com/openai/CLIP/blob/main/LICENSE) là MIT. Đây là fixture pipeline nghiên cứu local, chưa chứng minh chất lượng hoặc tính phù hợp cho deployment.

## Khởi tạo và cache

Downloader explicit `python -m app.cli.download_model --output .cache/clip` tải đúng revision từ model hub, ghi SHA-256 từng config/tokenizer/weights. Upstream revision cung cấp pytorch_model.bin; conversion chỉ dùng `torch.load(weights_only=True)` rồi ghi safetensors. Runtime chỉ load safetensors với `local_files_only=True`, không trust_remote_code hoặc tải lại theo mỗi ảnh. Hash/checkpoint mismatch fail trước index writes. Không commit weights hoặc đưa secrets vào cache receipt.

Một model/process worker, eval và torch.inference_mode, float32, deterministic algorithms, CPU threads4. `EMBEDDING_DEVICE=auto` chọn CUDA nếu runtime có, nếu không CPU; explicit cuda unavailable thì fail rõ, không âm thầm đổi precision/device. Lockfile hiện dùng PyTorch CPU wheel; CUDA cần runtime/lock tương ứng và phải nghiệm thu riêng. CUDA OOM chia đôi batch trên cùng device; một ảnh vẫn OOM thì failed/retry bounded. CUDA chưa có phép đo trên máy nghiệm thu.

## Preprocessing và vectors

Original bytes không thay đổi. Decoder subprocess sửa EXIF orientation, chuyển RGB và composite alpha lên trắng, bỏ metadata trong input dẫn xuất. Official CLIPImageProcessor từ cùng revision quyết định resize/center crop/mean/std; không tự đặt thông số thay processor. Config thực nằm immutable manifest, gồm resolution/crop, weights/tokenizer/processor file hashes, decoder/encoder code hashes, Torch/Transformers versions, device/attention/precision.

Dimension lấy từ loaded `model.config.projection_dim`, thực đo baseline512, rồi assert shape của output. `encode_images(images)` trả numpy float32 shape `[N,D]`; reject NaN/Inf/zero norms và normalize L2. CLIP text branch cùng checkpoint và tokenizer nằm cache để Phase 05 dùng cùng projection space; chưa có text-search API. Vector hash receipt là float32 little-endian của vector đã retrieve sau Qdrant cosine normalization, tránh sai khác bit do storage normalization.

Model ID UUID trỏ immutable manifest SHA-256. Source/preprocessor/inference policy khác tạo manifest mới và collection mới; không overwrite row/space cũ. Registry và ImageEncoder protocol cho phép thêm SigLIP 2 adapter tương lai, với own processor/dimension/manifest. Chưa tải/chạy SigLIP 2.

## Đo lường

Worker ghi model initialization, decode/preprocess, official processor, inference forward, normalization/transfer, upsert+verify và whole batch/worker durations. CUDA synchronize khi đo GPU; CPU số đo chỉ áp dụng CPU. OOM split có metrics của subbatch, không dùng làm full-batch benchmark khi xảy ra fallback. Ghi peak RSS KiB và batch size; không suy ra online P90 hoặc Recall@10 từ indexing throughput. Xem [INDEXING_TEST_REPORT](../archive/INDEXING_TEST_REPORT.md).
