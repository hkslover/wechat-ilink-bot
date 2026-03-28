#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[clear_build] Cleaning build artifacts in: $ROOT_DIR"

# Common build/cache outputs at repository root.
ROOT_TARGETS=(
  "build"
  "dist"
  "site"
  ".coverage"
  ".pytest_cache"
  ".ruff_cache"
  ".mypy_cache"
)

for target in "${ROOT_TARGETS[@]}"; do
  if [ -e "$target" ]; then
    rm -rf "$target"
    echo "[clear_build] removed: $target"
  fi
done

# Python cache files/directories.
find . -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
find . -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete 2>/dev/null || true

# Local package metadata directories.
find . -maxdepth 3 -type d -name "*.egg-info" -prune -exec rm -rf {} + 2>/dev/null || true

echo "[clear_build] done"
