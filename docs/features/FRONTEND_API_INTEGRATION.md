# Tích hợp frontend–backend — Phase 10

Base URL mặc định `/api/v1`; Vite proxy giữ browser cùng origin. `VITE_API_BASE_URL` chỉ là địa chỉ API, không chứa credential. Với môi trường khác cần cấu hình proxy/CORS tương ứng. Thay base không đổi contract đường dẫn media do backend trả về.

## Các endpoint được UI sử dụng

| Endpoint | Đầu vào chính | Đầu ra / cách dùng |
|---|---|---|
| `GET /health` | Public liveness | Capabilities ban đầu; không kết luận dataset từ endpoint này |
| `GET /health/live` | Public | Nghiệm thu process liveness |
| `GET /health/ready` | Bearer token | PostgreSQL/Qdrant/MinIO; body hợp lệ cả khi HTTP 503 |
| `GET /system/workspace` | Bearer token | Dataset state, counts, active index/generation, capabilities, limits |
| `POST /search` | JSON mode/text/top_k/filters/rerank/fusion khi phù hợp | SearchResponse, query_analysis AST, warnings, latency |
| `POST /search/multimodal` | Multipart `image` và JSON string `options` | Image-only, auto-image hoặc text+image; browser tự tạo boundary |
| `GET /images/{id}` | Bearer token, UUID | Metadata, indexing state, private content URLs |
| `GET /images/{id}/content?variant=...` | Bearer token | JPEG/PNG/WebP private, blob hiển thị local |
| `POST /rag/explain` | question/language/image_ids/expected_index_id | Explain-existing, fallback khi streaming tắt |
| `POST /rag/explain/stream` | Cùng request như JSON | Public progress và terminal `generation_completed` |
| `POST /search/agent/stream` | query/top_k/mode/planning_mode/include_explanation/rerank | Public progress và terminal `agent_completed`/`agent_partial` |
| `GET /system/evaluation` | Bearer token | Chỉ số tổng hợp được allowlist từ artifact đã lưu |

Tất cả endpoint ngoài public health dùng `Authorization: Bearer …`. Media không có presigned/public fallback. UI chỉ nhận đường dẫn khớp đúng image ID và variant; không gửi token đến nguồn ảnh tùy ý. Có timeout, MIME/size guard, abort và blob cleanup. Caption/metadata/answer render bằng React text, không `dangerouslySetInnerHTML`.

## Snapshot workspace bổ sung

```json
{
  "dataset": {
    "state": "ready", "images": 513, "available_images": 513,
    "indexed_images": 513, "vectors": 513,
    "index_id": "b4597021-4b91-491d-99ae-0617a6ca389c",
    "index_status": "ready", "generation": 3
  },
  "dependencies": {"postgresql": "healthy", "qdrant": "healthy", "minio": "healthy"},
  "capabilities": {"text_search": true, "image_search": true, "multimodal": true, "multi_intent": true, "rerank": true, "explanations": true, "agent": true},
  "rag": {"enabled": true, "configured": true, "streaming": true},
  "agent": {"enabled": true, "llm_planning": true},
  "limits": {"top_k": 50, "image_bytes": 20971520}
}
```

Đây là hình dạng snapshot của corpus nghiệm thu; số lượng không được hardcode trong app. Counts có thể null khi không quan sát được; vector count là số quan sát từ Qdrant collection active, không phải kết quả audit mọi vector. Không có active index thì không suy đoán vector count bằng 0. Query lỗi hoặc dependency lỗi không trở thành `empty_dataset`. `rag.configured` phản ánh provider được cấu hình, không phải phép thử online/quota của provider; UI xử lý lỗi thực sau khi người dùng yêu cầu generation.

Snapshot tự đọc sau khi token ổn định 800 ms, cập nhật mỗi 30 giây khi tab hiện và có nút refresh. Không gọi model/provider trong polling. Endpoint có server auth và không trả connection string, secret hoặc prompt.

## Dashboard

`EVALUATION_RESULTS_DIR` mặc định `evaluation/results`; Compose mount read-only tại `/evaluation/results`. Reader đọc layout tracker `phase/run/result.json`, tối đa 200 artifact, mỗi file tối đa 16 MiB; bỏ file lỗi và symlink thoát root. Response: `state = available | empty | not_available`, `skipped`, `experiments[]`. Mỗi row chỉ gồm id/phase/kind/status, attempted/successful/failed, client-success P90/P95, `recall_at_10=null`, `quality_status=not_published`. Không expose samples/query/key/path nội bộ. Cột successful/failed là trạng thái HTTP của artifact; không suy ra Agent task success hoặc faithfulness. Không công bố Recall@10 khi chưa có quy trình nhãn được xác nhận cho dashboard.

## Lỗi và streaming

JSON client bảo toàn code, HTTP status, request ID và retryable; không tự retry. HTTP 400/401/403/404/408/422/429/500/503 có test, kể cả proxy trả HTML; timeout, network, cancellation và invalid response được phân biệt. Decoder kiểm tra các trường được render, metadata, media URL, constraints, warnings và citations.

SSE POST fetch hỗ trợ chunk UTF-8/CRLF, nhiều frame, deadline 65 s và giới hạn 2 MiB. Chỉ public event allowlist cập nhật progress. Không render token chưa được xác nhận hoặc chain-of-thought. EOF thiếu terminal là lỗi. `error` của Agent với `retrieval_preserved=true` chờ terminal partial để giữ ảnh; fatal error vẫn dừng. RAG terminal chỉ chấp nhận citations thuộc bộ image_ids đã chọn. Các request mới, đổi token/route hoặc đóng panel sẽ hủy request cũ phù hợp vòng đời.

Chi tiết contract AI tiếp tục ở [RAG_API.md](RAG_API.md), [AGENT_API.md](AGENT_API.md) và [API_SPECIFICATION.md](../architecture/API_SPECIFICATION.md). Phase 10 không thay hành vi established search endpoints.
