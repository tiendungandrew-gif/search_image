# Chiến lược kiểm thử — Phase11

Mục tiêu là kiểm chứng phần mềm với dataset rỗng, fixture có kiểm soát và dịch vụ thật; đánh giá AI thực tế là một gate riêng. Tái sử dụng pytest, Vitest/Testing Library, Playwright và framework benchmark Phase07.

## Profile độc lập

| Profile | Lệnh từ repository root | Điều kiện |
| --- | --- | --- |
| Khởi tạo QA | `python3 scripts/qa.py init` | Sinh `.env.qa` riêng mode0600; không đọc `.env` |
| Dịch vụ QA rỗng | `python3 scripts/qa.py up` | Docker/Compose, build locked dependencies; không tải model |
| Backend fast | `python3 scripts/qa.py fast` | QA test image; tests dùng doubles, không cần dữ liệu dịch vụ |
| Frontend fast | `python3 scripts/qa.py frontend` | Node/npm, `npm --prefix frontend ci` |
| Service integration | `python3 scripts/qa.py services` | PostgreSQL, Qdrant, MinIO QA đang chạy |
| Empty browser | `python3 scripts/qa.py browser` | Trước seed; Playwright browsers |
| Browser mock | `python3 scripts/qa.py mock-browser` | Dev server tạm port5190; backend mock |
| Model thật | `python3 scripts/qa.py up --with-model` rồi `python3 scripts/qa.py ai` | CLIP cache đã tải có chủ đích; không tự download |
| Empty → indexed | `python3 scripts/qa.py seed` | Chỉ QA, sáu ảnh tổng hợp, quan hệ hư cấu có guard |
| Indexed browser | `QA_INDEXED=1 python3 scripts/qa.py browser` | Sau seed |
| Fault/recovery | `python3 scripts/qa.py faults` | HTTPX trong backend venv hoặc system Python; chạy riêng, SIGKILL chỉ QA |
| Dọn QA | `python3 scripts/qa.py down` | Xóa volumes của đúng project QA đã sinh |

Trên máy Docker Snap hiện tại thêm `QA_USE_SG=1` trước lệnh QA. Trên Docker thông thường không cần. Các lệnh cần browser/socket Docker phải chạy ngoài sandbox chặn IPC; không tắt kiểm tra để né lỗi môi trường. Host pytest trong sandbox từng treo ở executor; kết quả nghiệm thu backend lấy từ Docker có deadline.

Có thể chạy fast tests trực tiếp sau `uv sync --project backend --frozen --extra dev --extra evaluation`:

```bash
PYTHONPATH=backend:scripts DEBUG=false backend/.venv/bin/pytest backend/tests/unit backend/tests/security backend/tests/reliability -q
backend/.venv/bin/ruff check backend scripts
backend/.venv/bin/ruff format --check backend scripts
backend/.venv/bin/python -m compileall -q backend/app backend/tests scripts
```

Backend chưa cấu hình mypy/pyright: type checking Python riêng ghi **NOT_CONFIGURED**; không dùng compileall thay cho type checker. Frontend chạy `tsc -b`, gồm cả Playwright configs và tests.

## Quy tắc cô lập và bằng chứng

`compose.qa.yaml` dùng project `phase11-qa-<random>`, mạng/volumes riêng, ports8011/5175. Mỗi integration fixture tạo database `image_search_qa_<uuid>`, bucket `qa-suite-<uuid>`, collections `images_qa_*`. Guard yêu cầu APP_ENV=test, QA_ISOLATED=1 và host qa-postgres. Cleanup chỉ xử lý tài nguyên đã sở hữu; không dùng các script mutating cũ trên DB phục vụ.

Ảnh/vector/LLM/knowledge fixtures đều được đánh dấu. Model thật không biến ảnh tổng hợp thành benchmark ngữ nghĩa. Skip theo profile được báo riêng; không cộng repeated runs vào tổng số test. Runner lưu command, exit code và log thật tại [runs](../verification/phase11/runs), deadline test240s/browser240s và timeout orchestration hữu hạn. Traces tắt để tránh lưu Bearer headers.

## Performance và nhãn thật

Lệnh benchmark vẫn là `app.cli.evaluation benchmark`, cấu hình trong `evaluation/experiments/phase11_*.json`; xem [PERFORMANCE_REGRESSION](../archive/PERFORMANCE_REGRESSION.md). Đây là profile manual, không bắt mọi PR tải model/chạy load. Real dataset evaluation dùng `validate-dataset`, `validate-labels`, `evaluate` với snapshot/query/qrels được cung cấp riêng; [EVALUATION_METHODOLOGY](../research/EVALUATION_METHODOLOGY.md) và [RAG_EVALUATION](../research/RAG_EVALUATION.md) quy định nhãn. Thiếu nhãn thì **chờ xác nhận**, không tự chấm để đóng gate.

CI tách backend-fast, frontend-fast/mock browser, services/empty browser/faults và optional-real-model. Real-dataset evaluation và load là manual profiles; chưa có job GitHub tự provision corpus/nhãn production. Các PR không cần production secrets.
