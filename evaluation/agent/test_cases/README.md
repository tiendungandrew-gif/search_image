# Các nhóm ca kiểm tra Agent

Ca tự động nằm tại `backend/tests/unit/test_agent.py`, `backend/tests/integration/test_real_agent.py` và `frontend/e2e/agent.spec.ts`. Facts fixture ở `../fixtures/fictional_knowledge.json` là hư cấu. Không nhập vào database ứng dụng.

| Nhóm | Expected behavior |
| --- | --- |
| Query đơn giản | Semantic tool, không LLM planner, IDs trùng core search |
| Multi-intent / multimodal | Adapter sang Phase06, không tạo retrieval engine khác |
| Quan hệ fixture đủ nguồn | 4 calls/3 logical hops, đúng IDs từ manifest/receipt |
| Alias / không entity | Alias đúng hoặc dừng insufficient sau lookup |
| Thiếu relation / conflict | Insufficient evidence, không tạo city hoặc image |
| Empty PG/Qdrant/MinIO | App/registry khởi tạo, no fake results |
| Invalid tool/ref/cycle/budget | Reject trước execution |
| Timeout/cancel/RAG disabled | Nhả admission, giữ ảnh đã revalidate nếu có |
| ID giả / stale evidence | Loại khỏi final results |
| JSON LLM thực | Validate plan trước chạy, cùng guard/dependencies |
| Corpus510 thật + RAG | Kiểm tra storage IDs và citations, chưa chấm relevance |

Labels fixture được chuẩn bị độc lập từ payload nhập và upload receipt trước request. Human real-world labels chưa có; xem `docs/research/AGENT_EVALUATION.md` để biết schema và mẫu số metrics. Không suy ra Recall@10 hoặc task accuracy từ các ca correctness này.
