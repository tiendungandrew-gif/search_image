#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -ne 1 ]; then
  printf 'Usage: bash scripts/data/index_sample_dataset.sh INDEX_UUID\n' >&2
  exit 2
fi
docker compose --profile indexing run --rm -T indexing-worker python -m app.cli.indexing dataset --input /datasets/sample --index "$1" --name scikit-image-v0.25.2 --license per-file --rights-ref datasets/sample_manifest.json
