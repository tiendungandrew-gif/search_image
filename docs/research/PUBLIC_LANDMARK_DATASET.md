# Bộ địa danh công khai — hoàn thiện Prompt 09

Ngày 06/11/2026. Người dùng chọn chuẩn bị bộ địa danh có trích nguồn. Bộ đầu tiên gồm ba ảnh NPS và các facts vị trí tại Washington, D.C.; dùng để kiểm chứng workflow quan hệ trên dữ liệu thật. Không dùng bộ này thay cho nhãn relevance/faithfulness của người đánh giá.

## Nguồn, giấy phép và ranh giới

| Entity / ảnh | Nguồn mô tả và credit | Nguồn quan hệ located_in |
| --- | --- | --- |
| Washington Monument | [NPS, ảnh dusk, credit NPS Photo](https://www.nps.gov/wamo/index.htm) | Trang NPS nêu địa danh tại Washington, D.C. |
| Lincoln Memorial | [NPS, ảnh dusk, credit NPS Photo](https://www.nps.gov/linc/index.htm) | [Địa chỉ địa danh tại Washington, DC](https://www.nps.gov/linc/planyourvisit/directions.htm) |
| Thomas Jefferson Memorial | [NPS, ảnh có cây hoa, credit NPS / Mike Litterst](https://www.nps.gov/thje/index.htm) | [Vị trí và chỉ dẫn của NPS](https://www.nps.gov/thje/planyourvisit/directions.htm) |

Theo [chính sách NPS](https://www.nps.gov/aboutus/disclaimer.htm), các tác phẩm do NPS tạo trong công vụ nhìn chung thuộc public domain, trừ nội dung được chỉ rõ khác. Catalog này chỉ chọn ảnh có credit NPS, không có ký hiệu copyright; không chọn ảnh đầu trang Jefferson có credit bên thứ ba. Lưu credit, URL ảnh, trang chứng cứ, quyền sử dụng và thông tin rendition trong metadata. Ảnh tải là JPEG rendition do NPS cung cấp với maxWidth1200/maxHeight800; không chỉnh sửa bằng công cụ local.

Nguồn Hà Nội đã được đối chiếu tại [Vietnam Tourism](https://vietnam.travel/things-to-do/11-must-see-attractions-ha-noi/), nhưng Wikimedia API trả403 và đường tải ảnh trả429 trong môi trường này. Không vượt giới hạn truy cập hoặc dùng ảnh không rõ quyền để lấp dữ liệu. Mẫu Hồ Hoàn Kiếm vẫn trả thiếu evidence trong kho hiện tại; bộ NPS kiểm chứng khả năng nhận dữ liệu thật mà không thay kiến trúc.

## Gói dữ liệu và provenance

- [Catalog cố định](../../evaluation/agent/datasets/nps_v1.json): ba URL nguồn/ảnh allowlist và credit đã đối chiếu.
- [Manifest tải, SHA-256 và kích thước](../verification/phase09_completion_20261106/public_download_manifest.json): checksum ảnh, metadata và trang mô tả tại thời điểm tải.
- [Gói import có IDs ổn định](../../evaluation/agent/datasets/nps_v1_knowledge.json):4 entities,3 relationships,3 image links. IDs entity/relation dùng UUID5, image IDs lấy từ upload receipt đã verify.
- [Kết quả indexing](../verification/phase09_completion_20261106/corpus/summary.json): index mới513 ảnh, giữ nguyên index cũ510 ảnh.
- [Kiểm chứng workflow](../verification/phase09_completion_20261106/public/result.json): query Anh/Việt, alias, missing entity, hard filter, Gemini planner và RAG thật.

`verified_at` ở relations và `verified=true` ở links thể hiện attestation theo nguồn NPS và receipts đã kiểm tra. Không ghi `human_verified=true` hoặc tự tạo điểm relevance. Bộ labels kiểm tra exact IDs lấy từ import manifest trước query, có classification `source_verified_workflow`; `real_world_retrieval_accuracy=null`.

## Tái lập trên một môi trường mới

```bash
PYTHONPATH=backend backend/.venv/bin/python -m app.cli.download_landmarks

# Tạo collection mới; baseline phải là index hiện có đã được kiểm chứng.
backend/.venv/bin/python scripts/data/prepare_rag_corpus.py \
  --dataset datasets/landmarks_phase09_v1 \
  --baseline evaluation/datasets/manifests/phase08_coco_v2.json \
  --version clip_landmarks_phase09_v1 \
  --output docs/verification/phase09_new/corpus --activate
```

Downloader không overwrite thư mục đã có, không follow redirect và không tự retry khi rate limited. Thay output/version để chạy một lần mới. Dùng CLI `app.cli.prepare_landmark_knowledge` ghép catalog, manifest, ingestion receipt và verification report, sau đó validate/import bằng `app.cli.knowledge`. Cập nhật `INGESTION_INDEX_ID` theo index đã verify và restart backend/worker để dùng active pointer mới. [KNOWLEDGE_BASE_DESIGN](../features/KNOWLEDGE_BASE_DESIGN.md) ghi contract import và cách copy file vào container.

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/verification/verify_public_agent.py \
  --llm --rag --output docs/verification/phase09_new/public
```

Helper hiện dùng catalog/receipts của bộ NPS đầu tiên trong repository và workspace đã chuẩn bị. Cần Docker access, model cache và stack đã sẵn sàng theo [SETUP](../operations/SETUP.md). API key chỉ đọc từ `.env`, không đưa vào catalog hoặc source URLs. Files ảnh raw nằm trong thư mục dataset ignored; không commit ảnh/weights vào Git.

## Thử trong ứng dụng

Chọn Agent, nhập `Find landmarks in the city where Washington Monument is located` hoặc `Tìm ảnh địa danh ở thành phố nơi Washington Monument tọa lạc`. Kết quả có ba ảnh và bốn bước đã chạy; mở “Nguồn quan hệ” để xem các trang NPS. Có thể bật giải thích sau retrieval. Semantic Search thông thường vẫn chạy độc lập với Agent/LLM.
