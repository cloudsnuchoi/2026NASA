#!/usr/bin/env bash
# Cloudflare quick tunnel for Mattermost. No account, no domain -> URL is random
# and CHANGES EVERY RESTART. Keep it running in tmux (or the systemd --user unit below).
# After a restart: grab the new URL, then run ./set-siteurl.sh <url> and repost it in ~공지.
set -euo pipefail
PORT="${MM_HOST_PORT:-8065}"
LOG="${TUNNEL_LOG:-/srv/hackathon/db/mattermost/tunnel.log}"
mkdir -p "$(dirname "$LOG")"
echo "Starting quick tunnel -> http://127.0.0.1:${PORT} (log: $LOG)"
cloudflared tunnel --no-autoupdate --url "http://127.0.0.1:${PORT}" 2>&1 | tee -a "$LOG"
