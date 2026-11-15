#!/usr/bin/env bash
# Cloudflare quick tunnel for the ART FARM web; writes the public URL to state/status/demo_url.txt
set -uo pipefail
LOG=/srv/hackathon/logs/web-tunnel.log
OUT=/srv/hackathon/state/status/demo_url.txt
: > "$LOG"
cloudflared tunnel --no-autoupdate --url http://127.0.0.1:8095 >>"$LOG" 2>&1 &
PID=$!
for _ in $(seq 1 60); do
  URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG" | head -1 || true)
  if [ -n "$URL" ]; then echo "$URL" > "$OUT"; echo "public: $URL"; break; fi
  sleep 1
done
wait "$PID"
