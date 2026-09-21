#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -x .venv/bin/python ]; then
  fea_python="${FEAR_PYTHON:-python3}"
  "$fea_python" -c 'import sys; assert sys.version_info >= (3,12), "OpenFEA requires Python 3.12 or later. Set FEAR_PYTHON to its executable."'
  "$fea_python" -m venv .venv
  .venv/bin/python -m pip install -r requirements.txt
fi
if [ ! -d node_modules ]; then npm ci; fi
npm run build
exec .venv/bin/python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
