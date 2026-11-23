#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -lt 1 ]; then
  printf 'Usage: bash scripts/evaluation/benchmark_search.sh text|image [benchmark arguments]\n' >&2
  exit 2
fi
modality="$1"
shift
uv run --project backend python scripts/run_local.py --env-file .env -- backend/.venv/bin/python evaluation/scripts/benchmark_search.py --mode "$modality" --output "evaluation/results/${modality}_baseline.json" "$@"
