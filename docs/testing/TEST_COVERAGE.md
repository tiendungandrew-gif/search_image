# Ma trận coverage — Phase11

Đây là coverage theo hành vi đã kiểm tra, **không phải phần trăm line/branch coverage**. Không cài thêm framework đo coverage để tạo một con số không phản ánh các boundary thực.

| Khu vực | Tập test/bằng chứng | Đã kiểm tra | Còn mở |
| --- | --- | --- | --- |
| Backend API/config | `tests/unit/test_api.py`, `test_config.py`, `test_upload_api.py`, `security/test_request_security.py` | Error envelope, flags, bounds, auth/CORS, JSON/multipart, size/Unicode | Public internet abuse/load dài hạn |
| Schemas/database | `test_schema.py`, service integration | DDL/FK/unique, fresh migrations, repository, idempotent startup | Restore backup production |
| Embeddings | `test_ingestion.py`, `test_qa_ai.py` | Decode, finite/dimension/norm, CLIP load, manifest mismatch | SigLIP regression mới, GPU |
| Ingestion | `test_qa_services.py`, `test_qa_worker_process.py` | 3 formats, duplicate race, zero vector, retry/repair, lease/SIGKILL/cancel | Disk full, long soak |
| Search | `test_search.py`, `test_timing.py`, real model/API/browser | Top-K/rank/dedup/filter, no-match, private content, decoder recovery | Human semantic Recall@10 |
| Multimodal | `test_advanced_search.py`, AI/browser | Fusion/weights/dedup, independent channels, missing inputs | Chất lượng compositional edits |
| Multi-intent | Cùng tập advanced + frontend foundation | AND/OR, required/optional, unknown evidence, fallback/rerank | Verifier ngữ nghĩa tổng quát |
| RAG | `test_rag.py`, frontend ExplanationPanel, live Gemini | Context budgets/provenance, invalid/missing citations, malicious text, provider failure, SSE | Human faithfulness/answer quality |
| Agent | `test_agent.py`, `test_agent_evaluation.py`, real fixture/live NPS | Router, plan/tool validation, dependency/budgets/deadline/partial, empty KB | Entity/relation accuracy đại diện |
| Frontend | 11 Vitest files | State/cancel/stale, upload, private media, decoder, cleanup/ErrorBoundary | Thiết bị vật lý, screen reader thực |
| E2E | QA mock/empty/indexed + serving regression | Luồng chính, details/keyboard/theme/axe/responsive, optional RAG/Agent | Không chạy lại mọi legacy browser spec |
| Security | 28 security cases + unit/browser/integration liên quan | Input, auth, XSS/URL, fixture guard, private bucket, allowlisted tools/logs | Full pentest, Python/container CVE scan |
| Reliability | 4 fast reliability cases + service/fault/browser tests | Lifecycle, monitor cleanup, observability, termination/recovery | Multi-host partitions/host crash |
| Performance | Phase07 harness, frozen snapshot513, Gemini8 requests | Fast500, image24, multi-intent30, multimodal24, C4/100 | Production scale và SLA provider |

## Số lượng nghiệm thu

- Backend fast: **232 pass** =200 unit +28 security +4 reliability.
- Service integration: **11 pass**; AI integration thật: **1 pass**. Tổng backend được chọn: **244 pass**.
- Frontend: **44 pass** trong11 test files; typecheck, ESLint và production build pass.
- Browser mới: **4 mock +4 empty +8 indexed pass**. Hai profile thực loại trừ nhau: empty chạy4/skip8, indexed chạy8/skip4; không cộng skip thành pass.
- Hồi quy browser trên hệ thống phục vụ: **50 pass**, gồm42 ca backend thật và8 ca có route mock. Hai ca RAG thật chấp nhận cả response generated hoặc documented fallback; xem attachment kết quả thực, không suy diễn pass UI thành generation thành công.
- **4 loại fault scenario trên2 trạng thái dataset =8 lượt pass** được báo riêng, không cộng thành pytest tests. Benchmark attempts cũng không cộng vào số test.

Tổng browser đã chọn là66 pass, gồm12 ca có mock và54 ca không dùng backend mock. Con số này không thay thế human accuracy. Các phép chạy lặp lại chỉ dùng để xác nhận bản sửa, không cộng dồn. Chi tiết log và trạng thái failed ban đầu tại [BUG_FIX_REPORT](../archive/BUG_FIX_REPORT.md), chỉ mục cuối tại `verification/phase11/final_audit.json`.
