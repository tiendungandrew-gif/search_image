# Kiểm thử và xác minh bản bàn giao

Re-use [TEST_STRATEGY Phase11](../testing/TEST_STRATEGY.md), pytest/Vitest/Playwright và benchmark framework hiện có. Tests có model/provider/corpus/labels được tách khỏi fast PR checks; không cần dataset để build/deploy empty state.

## Các lệnh thực hiện

```bash
backend/.venv/bin/ruff check backend scripts
backend/.venv/bin/ruff format --check backend scripts
backend/.venv/bin/python -m compileall -q backend/app backend/tests scripts
python3 scripts/qa.py fast
python3 scripts/qa.py frontend
python3 scripts/qa.py up --with-model
python3 scripts/qa.py services
python3 scripts/qa.py ai
```

Runner QA tạo namespace riêng; không dùng DB serving cho integration. Docker Snap cần QA_USE_SG=1. `frontend` gồm typecheck/lint/unit/build; `fast` gồm unit/security/reliability. Production image cố ý không có pytest/Ruff/dev source mounts. Backend chưa cấu hình static type checker riêng, không gọi compileall là type check.

## Production-like acceptance

Sau init/build/up theo deployment guide:

```bash
DEPLOY_USE_SG=1 backend/.venv/bin/python scripts/checks/verify_deployment.py --env-file config/environments/deployment.env --expected-images 0
backend/.venv/bin/python scripts/checks/check_deployment_browser.py --env-file config/environments/deployment.env
```

Tên env Phase12 là môi trường kiểm chứng, không phải env serving. HTTP verifier cần HTTPX trên host; dùng backend venv. Browser cần npm dependencies và Playwright browsers. Sáu ảnh thử có thể tạo có chủ đích:

```bash
backend/.venv/bin/python scripts/data/create_deployment_fixtures.py --output .cache/deployment/fixtures/shapes
```

Output chỉ cho phép trong .cache và không ghi đè thư mục có sẵn. Import vào deployment disposable đã cấu hình DATASET_PATH tương ứng; không tự nhập fixture vào dự án serving. Sau import chạy verifier với expected-images đúng và browser thêm --indexed. Không dùng synthetic image top matches làm nhãn relevance.

Verifier kiểm static SPA/deep links, auth, ingress admin restrictions, empty evaluation, actual image bytes/hash/private cache, text/multimodal, disabled RAG và Agent/SSE khi bật. Browser kiểm Chromium desktop/mobile, Firefox, WebKit, keyboard/details, layout và axe trong states chọn. Viewport emulation không phải physical iOS/Android/macOS/Windows certification.

## Failures, skips và quality gates

Artifacts Phase12 nằm [verification/phase12](../verification/phase12); nguyên failed harness runs được giữ. Empty/indexed profiles có skip không áp dụng; không cộng reruns hoặc failed attempts vào pass count. API response NOT_READY khi thiếu index, hoặc RAG generated=false khi provider disabled, là hành vi cần kiểm tra; không gọi chúng là AI generation success.

Human labels vẫn pending theo lựa chọn người dùng. Real-data Recall@K/nDCG/faithfulness cần snapshot/query/verified labels riêng theo [EVALUATION_METHODOLOGY](../research/EVALUATION_METHODOLOGY.md), không tự sinh qrels từ rankings. Benchmark mới vẫn dùng app.cli.evaluation; không so trực tiếp corpus7 ảnh với baseline513 ảnh như một cải thiện thuật toán.

GitHub Actions có job production Docker build/empty deployment/Chromium smoke ngoài các job Phase11. Local checks và actionlint không phải remote CI green; remote workflow execution chờ push và runner thực.
