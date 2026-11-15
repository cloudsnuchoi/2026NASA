#!/usr/bin/env bash
# Print the latest trycloudflare URL from the tunnel log.
LOG="${TUNNEL_LOG:-/srv/hackathon/db/mattermost/tunnel.log}"
grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG" | tail -1
