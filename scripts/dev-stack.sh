#!/usr/bin/env bash
# Starts Django (:8001), realtime (:4000), and Ionic (:8100) detached.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec "$ROOT/.venv/bin/python" "$ROOT/scripts/dev_up.py"
