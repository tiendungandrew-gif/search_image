#!/usr/bin/env bash
set -euo pipefail
python3 scripts/verification/verify_search.py --agent --skip-benchmark "$@"
