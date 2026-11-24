# Browser test suites

Các bài kiểm tra browser nằm cùng một nơi, chia theo phạm vi. Thực hiện lệnh từ `frontend/`; mọi suite dùng cấu hình chung `config/shared.ts` cho workers, retries, tắt trace và resolve test directory. Timeout, base URL và project riêng được giữ theo từng suite.

| Thư mục | Mục đích | Config |
| --- | --- | --- |
| `legacy/` | Foundation, search, evaluation và Phase10 | `config/legacy.config.ts` |
| `qa/` | Regression QA thật và mock API | `config/qa.config.ts`, `config/mock.config.ts` |
| `deploy/` | Deployment rỗng/indexed và account smoke | `config/deploy.config.ts` |
| `access/` | Quyền Admin/User | `config/access.config.ts` |
| `quick-login/` | Tài khoản trải nghiệm local | `config/quick-login.config.ts` |
| `consumer/`, `commercial/`, `navbar/`, `travel/`, `usability/` | Các nhóm acceptance của giao diện | Config cùng tên trong `config/` |

```bash
# Liệt kê tests, không gửi request tới ứng dụng
npm exec -- playwright test --config tests/e2e/config/mock.config.ts --list

# Mock API: config tự mở Vite ở 5190
npm exec -- playwright test --config tests/e2e/config/mock.config.ts

# Giữ entrypoint mặc định cho bộ legacy
npm run test:e2e
```

Suite thật cần môi trường, model/dataset, quyền và credential tương ứng; đọc [hướng dẫn kiểm thử](../../../docs/operations/TESTING_AND_VERIFICATION.md). Không chạy acceptance có thao tác ghi trên dữ liệu production. `--list` vẫn nạp module test; suite access cần `ACCESS_LOGIN_FILE` hoặc file QA credential đã được bootstrap.

Fixtures tính từ vị trí file; artifacts/screenshot và reporters vẫn theo working directory `frontend/`. Kết quả sinh ra nằm trong `frontend/test-results/` hoặc các đường dẫn evidence đã quy định. Không bật trace chứa session/diagnostic headers khi chưa xem xét dữ liệu được ghi.
