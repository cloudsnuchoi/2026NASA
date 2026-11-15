#!/usr/bin/env bash
# Read-only snapshots every 10 minutes, through 2026-11-15 20:30 Asia/Seoul.
set -u
export PGHOST="${PGHOST:-127.0.0.1}" PGPORT="${PGPORT:-5433}"
export PGUSER="${PGUSER:-hk}" PGDATABASE="${PGDATABASE:-fieldshift}"
repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
deadline="$(TZ=Asia/Seoul date -d '2026-11-15 20:30:00' +%s)"
while (( $(date +%s) <= deadline )); do
  timeout 480 python3 "$repo_root/data_pipeline/matlab_validate.py" || echo 'MATLAB validation failed; retry next interval' >&2
  remaining=$(( deadline - $(date +%s) ))
  (( remaining <= 0 )) && break
  (( remaining > 600 )) && remaining=600
  sleep "$remaining"
done
