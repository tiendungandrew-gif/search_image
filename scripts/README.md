# Các lệnh và công cụ

Chạy từ repository root. Các entrypoints chính được giữ ổn định:

| Lệnh | Mục đích |
| --- | --- |
| `python3 scripts/init_env.py` | Khởi tạo development env, không overwrite |
| `python3 scripts/run_local.py --env-file FILE -- COMMAND` | Truyền env vào child process, không source shell |
| `python3 scripts/deploy.py --help` | Build/deploy/import/backup/restore/update/rollback |
| `python3 scripts/qa.py --help` | Kiểm thử cô lập với credentials và data namespace riêng |

Các công cụ phụ đã được nhóm theo trách nhiệm:

| Thư mục | Nội dung |
| --- | --- |
| `checks/` | Kiểm môi trường, HTTP/services, frontend và production browser |
| `data/` | Chuẩn bị dataset, nhập mẫu và tạo fixtures có chủ đích |
| `evaluation/` | Benchmark/model comparison/suite wrappers |
| `verification/` | Verifiers của các phase trước; có thể thay trạng thái stack được chọn, đọc hướng dẫn trước dùng |
| `deployment/` | Thư viện deployment CLI: config, commands, backup/restore |
| `qa_tools/` | Setup, seed và fault scenarios giới hạn trong QA |
| `runtime/` | Entrypoint backend Docker development |
| `archive/` | Công cụ nghiệm thu riêng Phase10, giữ để đối chiếu lịch sử |

Ví dụ hiện hành:

```bash
bash scripts/checks/check_environment.sh
python3 scripts/qa.py frontend
backend/.venv/bin/python scripts/checks/verify_deployment.py --env-file config/environments/deployment.env --expected-images 7
backend/.venv/bin/python scripts/checks/check_deployment_browser.py --env-file config/environments/deployment.env --indexed
```

Hai lệnh cuối dành bản thử8088 đang có7 synthetic images; dùng số lượng/cấu hình đúng cho môi trường khác. Dependencies và opt-in tests theo [hướng dẫn kiểm thử](../docs/operations/TESTING_AND_VERIFICATION.md). `make` targets đã trỏ tới các vị trí mới. Công cụ `verification/` và `archive/` giữ lịch sử, QA cô lập là luồng regression mặc định.

## Tài khoản

`administration/accounts.py` bootstrap/reset Admin bằng stdin và file credential 0600. `checks/check_access_browser.py` kiểm chứng tài khoản và quyền bằng browser trên QA. Xem [hướng dẫn](../docs/operations/ACCOUNTS.md).
