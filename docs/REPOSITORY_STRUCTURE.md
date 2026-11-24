# Cấu trúc repository hiện hành

Đã chuẩn hóa sau bàn giao Phase12. Modular monolith, API contracts, DB schema và embedding space tiếp tục dùng thiết kế đã nghiệm thu; đây là việc tổ chức source/config/docs, không phải phase tính năng mới.

```text
backend/
  app/
    api/              # HTTP routes
    core/             # Config, auth, middleware, shared dependency container
    db/               # SQLAlchemy models và DB sessions
    integrations/     # Qdrant/MinIO adapters
    repositories/     # Metadata và knowledge access
    schemas/          # Request/response contracts
    services/         # Ingestion, embedding, indexing, search, RAG, Agent
    cli/              # Backend/worker/operator entrypoints
    evaluation/       # Evaluation framework code
  alembic/
  tests/              # Unit/integration/security/reliability
frontend/
  src/features/       # Search, RAG, Agent, evaluation và system status
  src/services/api/   # Typed API client và media/stream helpers
  tests/e2e/          # Browser suites theo chức năng
    config/           # Shared defaults và config từng suite
    legacy/           # Foundation/search/evaluation/Phase10
    qa/               # Isolated real/mocked QA scenarios
    deploy/           # Static production deployment scenarios
config/environments/  # Private deployment/restore configs, archived envs
infra/                # Docker infrastructure images và Nginx
scripts/              # Stable entrypoints, tools chia theo chức năng
evaluation/           # Queries, snapshots, labels, configs và experiment outputs
datasets/             # Hướng dẫn/catalogs; corpus và artifacts nhập liệu local bị ignore
backups/              # Backup private, không commit
docs/                 # Architecture/operations/features/research/testing/archive
workers/              # Compatibility launcher, tái dùng backend worker code
```

## Quy tắc đường dẫn và tương thích

- `.env` development và `.env.qa` vẫn ở root để giữ Compose/QA workflows. Private env nghiệm thu chuyển vào `config/environments/`; nội dung/credentials/project IDs giữ nguyên.
- `scripts/deploy.py`, `qa.py`, `run_local.py`, `init_env.py`, Make targets và lệnh Docker chạy frontend/backend tiếp tục là entrypoints chính. Công cụ phụ dùng vị trí mới trong [scripts/README](../scripts/README.md).
- `--env-file .env.phase12` và các alias cũ được host helper ánh xạ sang vị trí mới; Docker Compose trực tiếp dùng canonical path. Không tạo bản sao credentials giữa environments.
- Shared dependency lifecycle chuyển sang `app.core.container`; `app.services.health` giữ re-exports cho code/script cũ.
- Vector byte fingerprint chuyển sang `services/embeddings/vector_utils.py`; worker giữ re-export. Hàm và canonical float32 little-endian format giữ nguyên để không thay receipts.
- CLIP encoder và image decoder được giữ nguyên byte/hash; không reindex hoặc thay manifest vì việc sắp xếp thư mục này.
- Raw verification logs/JSON/source archives/experiment outputs giữ nguyên. Docs/code đang dùng đã cập nhật links và script paths; frozen artifacts có thể vẫn chứa tên cũ.

Mapping files và kết quả checks tại [verification/restructure](verification/restructure/). Tài liệu Phase12 là snapshot nghiệm thu trước tái cấu trúc; các giới hạn quality/public deployment vẫn được ghi ở [FINAL_HANDOVER](bao_cao_nghiem_thu/FINAL_HANDOVER.md).

## Docker images và release

Production-like8088 tiếp tục dùng immutable release `phase12-final` đã nghiệm thu trước refactor; development/QA sử dụng source hiện hành, QA image đã được build lại khi kiểm tra. Việc sắp xếp source không tự publish hoặc thay image của deployment đang phục vụ. Khi muốn phát hành source mới, build bằng một tag mới rồi dùng `update --release TAG`; không build đè `phase12-final`. Xem [update/rollback](operations/OPERATIONS_RUNBOOK.md).

Phần quyền mới: `backend/app/core/{auth,access,passwords}.py`, `db/models/access.py`, `api/v1/{authentication,admin_accounts,admin_content}.py`; frontend `features/{auth,admin,operator}`. Operator là giao diện tương thích cần bật legacy. Công cụ tạo tài khoản nằm ở `scripts/administration/`.

## Chuẩn hóa ngày 24/11/2026

- Tài liệu thiết kế hiện hành bắt đầu từ [PRD](architecture/PRD.md) và [SAD](architecture/SAD.md); baseline/spec cũ chuyển vào [architecture/archive](architecture/archive/README.md). Báo cáo/bằng chứng nghiệm thu giữ nguyên để đối chiếu lịch sử.
- Browser suites và cấu hình được gom tại `frontend/tests/e2e/`; `frontend/playwright.config.ts` giữ entrypoint mặc định cho legacy suite. Xem [browser test layout](../frontend/tests/e2e/README.md). Scripts QA, browser helpers và CI dùng config mới.
- `datasets/approved_csv_v1/` giữ nguyên local nhưng không theo dõi bằng Git/build context; snapshot tổng hợp ở `datasets/catalogs/approved_csv_v1.json`. Clone mới cần nguồn dữ liệu hoặc backup riêng.
- Helpers bulk import lưu ở `scripts/archive/approved_csv_v1/`. File terminal output có tên sai ở root được lưu local trong `.cache/restructure/accidental-git-stat.txt` rồi bỏ khỏi source.
- Không xóa volumes/database, đổi index hoặc rewrite Git history. Các file bỏ theo dõi xuất hiện là staged deletions trong commit dọn dữ liệu; file local vẫn còn.
