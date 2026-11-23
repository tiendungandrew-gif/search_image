# Báo cáo chuẩn hóa repository

Ngày08/11/2026. Phạm vi được yêu cầu: tổ chức lại cấu hình, tài liệu, scripts và các dependency dùng chung; giữ luồng chạy frontend/backend. Không mở phase tính năng mới hoặc triển khai public.

## Thay đổi

- Chuyển85 tài liệu vào architecture/operations/features/research/testing/archive; README root rút gọn, có danh mục docs và snapshot README trước sửa. Báo cáo lịch sử giữ cách viết commands cũ, links điều hướng theo vị trí mới.
- Chuyển32 scripts phụ vào checks/data/evaluation/verification/qa_tools/runtime/archive; Make, CI, Docker CMD và các subprocess/import paths đã cập nhật. Entrypoints deploy.py/qa.py/run_local.py/init_env.py giữ ở scripts root.
- Chuyển4 env nghiệm thu/native sang config/environments; giữ nguyên bytes/0600/credentials/project IDs. `.env` chính và `.env.qa` giữ ở root. Host helpers hỗ trợ tên env cũ; explicit external files không bị redirect sang credentials local.
- Dependency lifecycle ở app.core.container, health.py giữ compatibility exports. Vector fingerprint dùng chung ở embeddings/vector_utils.py, worker giữ re-export.
- CLIP encoder/image decoder giữ nguyên hash, không sửa migrations/models, active pointer hoặc reindex dữ liệu chính. Raw JSON/log/source archives/experiment results giữ lại; không stage/commit/push.

Mapping đầy đủ tại [moves.json](moves.json), [baseline](baseline.json) và [cấu trúc hiện hành](../../REPOSITORY_STRUCTURE.md).

## Kiểm chứng thực thi

| Kiểm tra | Kết quả | Bằng chứng |
| --- | --- | --- |
| Ruff lint/format |PASS,194 Python files format check |summary.json |
| Python compileall |PASS; không phải static type check |summary.json |
| Backend unit/security/reliability |249 pass |[QA fast](qa/fast.json), [log](qa/fast.log) |
| Real service integration |11 pass |[QA services](qa/services.json), [log](qa/services.log) |
| CLIP ingestion/search/Agent/RAG fixture |1 pass |[QA AI](qa/ai.json), [log](qa/ai.log) |
| Frontend type/lint/unit/build |PASS,44 unit tests |[QA frontend](qa/frontend.json), [log](qa/frontend.log) |
| CLI --help/shell syntax |28 checks pass |[cli_checks.json](cli_checks.json) |
| Deployment HTTP/media/multimodal/SSE |PASS trên8088 |HTTP JSON trong thư mục này |
| Browser desktop qua entrypoint mới/alias cũ |2 pass |[browser.json](browser.json), [log](browser.log) |
| Compose dev/prod validate, actionlint, Make dry-run |PASS; không chạy CI remote |summary.json, runs/ |
| Main/deployment data và frontend |513/gen3 và7/gen2, ports5173/8088 trả200 |[runtime.json](runtime.json) |
| Env bytes/mode/Git ignore, model code hashes |PASS |[secret_check.json](secret_check.json) |
| Known secret-value scan |0 matches; không phải pattern/CVE scan toàn lịch sử |[secret_check.json](secret_check.json) |
| Markdown links |Không có missing links trong phạm vi được quét |[document_checks.json](document_checks.json) |

Tổng backend selected261 pass, không cộng reruns. Browser2 là smoke của lượt tái cấu trúc, không cộng lại12 successful executions lịch sử Phase12. Warnings Qdrant HTTP nội bộ và NO_COLOR/FORCE_COLOR vẫn được giữ trong logs, không gọi là production TLS/security sign-off.

## Các attempt chưa pass và cách xử lý

Lượt pytest host trong sandbox dừng ở trạng thái chưa hoàn tất và được interrupt(exit130); không tính vào pass. Bộ Docker QA có timeout đã hoàn tất249 tests. Lần AI integration đầu không collect được vì `from seed_qa` còn trỏ tên cũ; đã đổi sang qa_tools.seed_qa và rerun1 pass. Các artifacts gốc của QA runner giữ trong docs/verification/phase11/runs theo timestamp; bản pass cuối được copy vào qa/ ở đây.

## Trạng thái bàn giao

QA được dọn sau tests, chỉ containers/volumes thuộc namespace QA. Development5173/8000 và production-like8088 tiếp tục hoạt động. Source mới có hash riêng tại [source.json](source.json); production-like vẫn dùng immutable phase12-final trước refactor. Build/deploy source mới phải chọn tag mới, theo [quy tắc release](../../REPOSITORY_STRUCTURE.md#docker-images-và-release).

Human quality labels, public hosting/TLS/least privilege, capacity và GPU/SigLIP production vẫn là các giới hạn đã công bố ở Phase12; việc sắp xếp repository không đóng các gate đó.
