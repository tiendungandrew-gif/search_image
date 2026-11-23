# Quản lý model

Từ 19/11/2026, release mới dùng thêm text encoder đa ngôn ngữ để tìm Việt–Anh
mặc định. `model-prepare` chuẩn bị cả hai model, `model-verify` kiểm tra cả hai
và mã hóa một cặp câu EN/VI. Thư mục `multilingual-text` nằm bên trong model cache.
Xem [chuẩn bị model song ngữ](../features/BILINGUAL_SEARCH.md); bản 8088 đang chạy
release cũ chưa được cập nhật.

Production pipeline hiện dùng **CLIP ViT-B/32 CPU**,512 chiều, float32/L2/Cosine. Model `openai/clip-vit-base-patch32`, revision `3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268`. Manifest còn ghi processor, decoder/encoder code hash, library versions, weights hashes và preprocessing. Kích thước khớp chưa đủ để coi embedding spaces tương thích.

## Chuẩn bị có chủ đích

```bash
python3 scripts/deploy.py model-prepare
python3 scripts/deploy.py model-verify
```

`model-prepare` là command download explicit: dùng pinned Hugging Face snapshot, chuyển weights_only state dict sang safetensors, tạo download.json/hashes và files readable cho runtime UID. Command chạy bằng UID/GID người vận hành trên cache mount writable; API/worker mount cùng cache read-only. Không tải weights khi `up`, không đưa weights hoặc provider keys vào image/repository. Cần Internet chỉ cho command prepare; đã có cache thì verify trước, không tải lại tùy tiện.

Offline: chuyển đầy đủ cache gồm download.json và toàn bộ files nó tham chiếu, giữ revision/permissions, đặt DEPLOY_MODEL_PATH, rồi chạy model-verify. Không chỉ chép model.safetensors. Cache hỏng/thiếu file hoặc revision sai bị từ chối; không thay bằng random vectors.

## Trạng thái

- Process live và infrastructure ready độc lập model/dataset.
- `status` inventory báo not_installed hoặc present_unverified cho artifacts; đó không phải kết quả inference.
- `model-verify` thực sự load/hash model và trả manifest/dimension/device.
- `/system/search-runtime` báo runtime/index/generation khi đã ready; workspace/capabilities tách dataset rỗng và unavailable.
- Worker idle không load model; pending jobs nhưng thiếu model làm worker blocked/unhealthy có heartbeat/error category, không báo indexing succeeded.

Lượt kiểm chứng Phase12 dùng cache đã có và CLIP thật, không download lại. Đã kiểm tra cấu hình cache thiếu: web và readiness hạ tầng vẫn200, search503 NOT_READY. Đây là graceful degradation, không phải search thành công trên index rỗng.

## Thay model hoặc phiên bản

Build release/lock phù hợp, chuẩn bị cache mới, register **collection mới**, re-embed originals và verify trước activation. Không trộn CLIP và SigLIP vectors; không dùng text encoder không cùng shared space. Giữ index cũ để rollback sau compatibility checks. Nếu original mất và không có backup thì không thể cam kết reindex phục hồi đầy đủ.

SigLIP có tooling evaluation từ Phase07, chưa là production ingestion adapter được nghiệm thu trong lượt này. Code CLIP có nhánh cuda nhưng image/lock hiện dùng PyTorch CPU. GPU cần artifact/lock CUDA, driver/runtime, resource và manifest riêng; **GPU production NOT_VERIFIED**, không chỉ đặt EMBEDDING_DEVICE=cuda trong image CPU rồi coi là được hỗ trợ.

RAG/Agent mặc định tắt. Gemini/OpenAI-compatible provider cấu hình server-side theo [CONFIGURATION_REFERENCE](CONFIGURATION_REFERENCE.md); khóa không nằm trong VITE/UI. Provider unavailable giữ Semantic Search; optional status/configured không phải cam kết provider SLA. Human faithfulness/relevance vẫn chờ nhãn, không suy ra từ citation validation.
