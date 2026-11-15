#!/usr/bin/env bash
# MATLAB result batching (VPS, tmux "rbatch" as hackathon). Every 30 min: copy new/changed csv/png/json (<5 MB)
# from outputs/<name>/ (top level only; old/ and python_smoke/ are skipped) into docs/matlab-results/<name>/ of the
# worktree /srv/hackathon/projects/2026NASA-mres (branch feat/matlab-results, created from origin/main if missing)
# and commit "chore(matlab-results): batch HH:MM" when anything changed. Never pushes.
#   bash results_batch.sh          # loop
#   bash results_batch.sh --once   # one batch
set -euo pipefail
SRC=${MRES_SRC:-/srv/hackathon/data/processed/v1/matlab/outputs}
WT=${MRES_WT:-/srv/hackathon/projects/2026NASA-mres}
BASE=${MRES_BASE:-/srv/hackathon/projects/2026NASA-mauto}
INTERVAL=${MRES_INTERVAL:-1800}
MAX_BYTES=$((5 * 1024 * 1024))

ensure_worktree() {
  [ -e "$WT/.git" ] && return 0
  git -C "$BASE" fetch -q origin main || true
  if git -C "$BASE" show-ref -q --verify refs/heads/feat/matlab-results; then
    git -C "$BASE" worktree add -q "$WT" feat/matlab-results
  else
    git -C "$BASE" worktree add -q -b feat/matlab-results "$WT" origin/main
  fi
}

batch() {
  ensure_worktree
  local n=0
  for dir in "$SRC"/*/; do
    [ -d "$dir" ] || continue
    local name dest
    name=$(basename "$dir")
    dest="$WT/docs/matlab-results/$name"
    for f in "$dir"*.csv "$dir"*.png "$dir"*.json; do
      [ -f "$f" ] || continue
      [ "$(stat -c %s "$f")" -lt "$MAX_BYTES" ] || continue
      mkdir -p "$dest"
      if ! cmp -s "$f" "$dest/$(basename "$f")"; then
        cp -p "$f" "$dest/"
        n=$((n + 1))
      fi
    done
  done
  git -C "$WT" add -A docs/matlab-results 2>/dev/null || true
  if ! git -C "$WT" diff --cached --quiet; then
    git -C "$WT" commit -q -m "chore(matlab-results): batch $(TZ=Asia/Seoul date +%H:%M)"
    echo "$(TZ=Asia/Seoul date +%H:%M:%S) committed ($n file(s) copied) $(git -C "$WT" rev-parse --short HEAD)"
  else
    echo "$(TZ=Asia/Seoul date +%H:%M:%S) no change"
  fi
}

if [ "${1:-}" = "--once" ]; then
  batch
  exit 0
fi
while true; do
  batch || echo "$(TZ=Asia/Seoul date +%H:%M:%S) batch failed"
  sleep "$INTERVAL"
done
