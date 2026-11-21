#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONUTF8=1

if [ -x "backend/.venv/bin/python" ]; then
    exec "backend/.venv/bin/python" start_demo.py "$@"
elif command -v python3 >/dev/null 2>&1; then
    exec python3 start_demo.py "$@"
elif command -v python >/dev/null 2>&1; then
    exec python start_demo.py "$@"
else
    echo "[ERROR] Python 3 not found. Install Python 3.12 and retry."
    exit 1
fi

