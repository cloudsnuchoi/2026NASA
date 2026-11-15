#!/usr/bin/env bash
# Start the ART FARM runtime tmux sessions after a reboot (user hackathon). Idempotent: a session that
# already exists is left alone, so it is safe to run by hand at any time.
# Commands copied from the running sessions on 2026-11-15 22:00 KST
# (`tmux list-panes -a -F '#S #{pane_start_command}'` and /srv/hackathon/logs/run-*.sh). Not installed anywhere;
# the proposed @reboot line is in docs/OPS-REBOOT.md. Secrets stay in the run-*.sh / .env files; none here.
# Assumes PostgreSQL (127.0.0.1:5433) and Mattermost (127.0.0.1:8065) come back on their own (docker restart
# policy not verified, see docs/OPS-REBOOT.md); the script only waits for them.
set -uo pipefail
export PATH="/home/hackathon/.nvm/versions/node/v26.13.1/bin:/home/hackathon/.local/bin:/srv/hackathon/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin"
export HOME="${HOME:-/home/hackathon}"
P=/srv/hackathon/projects
L=/srv/hackathon/logs
LOG=$L/start_all.log

say() { echo "$(date '+%F %T %Z') $*" | tee -a "$LOG"; }

start() {  # start <session> <dir> <command>
  if tmux has-session -t "=$1" 2>/dev/null; then say "skip $1 (running)"; return; fi
  tmux new-session -d -s "$1" -c "$2" "$3" && say "started $1" || say "FAILED $1"
}

wait_port() {  # wait_port <port> <seconds>
  for _ in $(seq 1 "$2"); do (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null && return 0; sleep 1; done
  say "port $1 not up after $2 s (continuing)"; return 1
}

say "start_all begin"
wait_port 5433 120   # PostgreSQL for model_api
start api        "$P/2026NASA-api"  "$L/run-api.sh"
wait_port 8090 90
start web        "$HOME"            "bash -c '$P/2026NASA-main/infra/web/run_web.sh 2>&1 | tee -a $L/web.log'"
wait_port 8095 60
start web-tunnel "$P/2026NASA-web"  "infra/web/run_tunnel.sh"          # writes a NEW demo_url.txt (quick tunnel)
wait_port 8065 120   # Mattermost
start mm-tunnel  "$P/2026NASA/infra/chat" "./tunnel.sh"                # new Mattermost URL: run ./set-siteurl.sh <url> by hand
start bot        "$P/2026NASA-bot/infra/orchestrator" "bash $L/run-bot.sh"
start mwatch     "$P/2026NASA-mauto" "bash -c \"python3 -u '$P/2026NASA-mauto/infra/matlab/mwatch.py' >> $L/mwatch.log 2>&1\""
start mfixq      "$L/sup"           "$L/run-mfixq.sh"
start live       "$HOME"            "$P/2026NASA-api/infra/status/run_live.sh 2>&1 | tee -a $L/live.log"
say "start_all end"
