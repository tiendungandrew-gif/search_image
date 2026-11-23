# Indexing worker

Worker chạy trong process riêng, tái sử dụng package backend và durable PostgreSQL jobs/leases. Logic pipeline tại `backend/app/services/indexing/worker.py`.

- Production daemon: `python -m app.cli.worker`, tự chờ jobs và idle khi chưa có index/model/data. Compose production quản lý process này.
- CLI xử lý một index: `python -m app.cli.indexing worker --index UUID`.
- `workers/indexing_worker.py --index UUID` là compatibility launcher cho CLI một index, không chứa bản sao logic.

Worker dùng ML image và model cache read-only. API nạp query encoder khi search được bật; worker nạp encoder để indexing theo vòng đời riêng. [IMAGE_INDEXING](../docs/features/IMAGE_INDEXING.md), [MODEL_MANAGEMENT](../docs/operations/MODEL_MANAGEMENT.md) và [DEPLOYMENT_GUIDE](../docs/operations/DEPLOYMENT_GUIDE.md) mô tả các luồng hiện hành.
