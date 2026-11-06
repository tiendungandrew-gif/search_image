#!/usr/bin/env sh
set -eu
python -m alembic -c backend/alembic.ini upgrade head
exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --no-access-log --no-server-header
