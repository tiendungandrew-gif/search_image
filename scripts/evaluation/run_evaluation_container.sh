#!/usr/bin/env bash
# Chạy research model/profile trong data network; không thay active index.
set -euo pipefail
cd "$(dirname "$0")/../.."
case "${1:-}" in
  clip|siglip2) args=(model-comparison --model "$1"); shift ;;
  profile) args=(profile); shift ;;
  *) printf 'Usage: bash scripts/evaluation/run_evaluation_container.sh clip|siglip2|profile [CLI options]\n' >&2; exit 2 ;;
esac
docker compose --profile indexing run --rm --no-deps -T \
  --user "$(id -u):$(id -g)" \
  -v "$PWD/backend/app:/srv/backend/app:ro" \
  -v "$PWD/scripts:/srv/scripts:ro" \
  -v "$PWD/evaluation:/srv/evaluation" \
  -v "$PWD/.cache/evaluation:/srv/.cache/evaluation" \
  -v "$PWD/.cache/siglip2:/models/siglip2:ro" \
  indexing-worker python -m app.cli.evaluation "${args[@]}" "$@"
