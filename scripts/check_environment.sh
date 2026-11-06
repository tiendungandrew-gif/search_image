#!/usr/bin/env bash
set -u
failed=0
check() {
  if command -v "$1" >/dev/null 2>&1; then
    printf '[OK] %s: %s\n' "$1" "$(command -v "$1")"
  else
    printf '[THIẾU] %s — %s\n' "$1" "$2"
    failed=1
  fi
}
check python3 'Cài Python 3.11+ và gói python3-venv của Linux distribution.'
check node 'Cài Node.js theo .nvmrc, xem docs/SETUP.md.'
check npm 'Cài npm 11.21.1, sau khi cài Node.js.'
check git 'Cài Git bằng package manager.'
check docker 'Cài Docker Engine; không tự thay đổi quyền socket hoặc thêm group.'
check make 'Cài GNU Make hoặc dùng các lệnh tương đương trong docs/DEVELOPMENT.md.'
if command -v python3 >/dev/null 2>&1; then
  python3 -c 'import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] < (3,14) else 1)' || { printf '[LỖI] Python cần >=3.11,<3.14.\n'; failed=1; }
fi
if command -v node >/dev/null 2>&1; then
  node -e 'const [a,b]=process.versions.node.split(".").map(Number);process.exit(a===22&&b>=12?0:1)' || { printf '[LỖI] Node cần 22.12+ trong dòng 22.\n'; failed=1; }
fi
if command -v docker >/dev/null 2>&1; then
  docker compose version >/dev/null 2>&1 || { printf '[THIẾU] Docker Compose v2 plugin.\n'; failed=1; }
  docker info >/dev/null 2>&1 || { printf '[LỖI] Docker daemon/socket chưa truy cập được.\n'; failed=1; }
fi
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  printf '[CHƯA CÓ] Git repository hợp lệ; giữ nguyên managed .git, xem SETUP.md.\n'
fi
exit "$failed"
