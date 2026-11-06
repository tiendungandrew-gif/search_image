# Indexing worker

Worker Prompt 04 chạy trong process riêng, dùng cùng package backend; durable queue là PostgreSQL. Logic tại `backend/app/services/indexing/worker.py`, CLI `python -m app.cli.indexing worker --index UUID`. Launcher `workers/indexing_worker.py --index UUID` gọi cùng CLI, không là implementation thứ hai.

Compose profile `indexing` thêm service `indexing-worker`; backend API không tải Torch/model. Worker dùng image có optional extra ml, đọc cache pretrained weights qua mount read-only và load một lần/process. Xem [IMAGE_INDEXING](../docs/IMAGE_INDEXING.md) để tải model, register index, nạp dataset, chạy/retry/reconcile và thêm worker replicas. Không dùng FastAPI BackgroundTasks làm queue.
