#!/usr/bin/env bash
# ART FARM public web: static frontend + read-only proxy to model_api (127.0.0.1:8095).
# Usage: tmux new -d -s web infra/web/run_web.sh
set -euo pipefail
cd "$(dirname "$0")/../.."
exec /srv/hackathon/venv-api/bin/uvicorn infra.web.app:app --host 127.0.0.1 --port "${WEB_PORT:-8095}" --proxy-headers
