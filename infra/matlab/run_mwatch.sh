#!/usr/bin/env bash
# Start the MATLAB run-log watcher in tmux "mwatch" (run as hackathon). Log: /srv/hackathon/logs/mwatch.log
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
tmux kill-session -t mwatch 2>/dev/null || true
tmux new-session -d -s mwatch "python3 -u '$HERE/mwatch.py' >> /srv/hackathon/logs/mwatch.log 2>&1"
echo "mwatch started (tmux mwatch, log /srv/hackathon/logs/mwatch.log)"
