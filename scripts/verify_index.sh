#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -ne 1 ]; then
  printf 'Usage: bash scripts/verify_index.sh INDEX_UUID\n' >&2
  exit 2
fi
docker compose --profile indexing run --rm -T indexing-worker python -m app.cli.indexing verify --index "$1"
