#!/usr/bin/env bash
# tmux live: regenerate the team status every 5 minutes (VPS, user hackathon).
export PGHOST=127.0.0.1 PGPORT=5433 PGUSER=hk PGDATABASE=fieldshift
while true; do
  timeout 280 python3 -I "$(dirname "$0")/live_status.py" --out /srv/hackathon/state/status || echo "live_status failed $(date)"
  sleep 300
done
