#!/usr/bin/env bash
# Point Mattermost SiteURL at the current tunnel URL (needed for links, websockets, plugins).
# Usage: ./set-siteurl.sh [https://xxxx.trycloudflare.com]   (default: latest URL in tunnel log)
set -euo pipefail
URL="${1:-}"
[[ -n "$URL" ]] || URL="$("$(dirname "$0")/tunnel-url.sh")"
[[ "$URL" == https://* ]] || { echo "no tunnel URL found (is tunnel.sh running?)"; exit 1; }
docker exec amolla-mattermost mmctl --local config set ServiceSettings.SiteURL "$URL"
echo "SiteURL = $URL"
