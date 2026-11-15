# Reboot survival audit (2026-11-15 22:00 KST, FINAL lane, read-only)

Question: if the VPS reboots, do `model_api` (:8090), `web` (:8095), `web-tunnel`, `mm-tunnel`, `bot`, `mwatch`, `mfixq` and `live` come back by themselves?

**Verdict: no.** All eight run only as hand-started tmux sessions. Nothing restarts them.

| Mechanism | Finding (command) |
| --- | --- |
| crontab, user hackathon | none (`crontab -l` → "no crontab for hackathon") |
| systemd --user units | none (`~/.config/systemd/user` does not exist) |
| user lingering | not enabled for hackathon (`/var/lib/systemd/linger/` lists fleetcompute, hyleprod, hylestg, stepdeploy only), so user units would not start at boot anyway |
| tmux-resurrect / continuum | not installed (no `~/.tmux.conf`, no `~/.tmux/plugins`) |
| system services, docker restart policy (PostgreSQL :5433, Mattermost :8065) | **not checked**: `systemctl` and `docker ps` were denied to this lane. If these do not come back, `model_api` and `bot` fail too. |

## Current sessions (from `tmux list-panes -a -F '#S #{pane_start_command}'`)

| Session | Directory | Command |
| --- | --- | --- |
| api | `2026NASA-api` | `/srv/hackathon/logs/run-api.sh` (detached `origin/main`, uvicorn `model_api.main:app` 127.0.0.1:8090; reads the LLM key from the orchestrator `.env`) |
| web | `$HOME` | `2026NASA-main/infra/web/run_web.sh` (uvicorn `infra.web.app:app` 127.0.0.1:8095) |
| web-tunnel | `2026NASA-web` | `infra/web/run_tunnel.sh` (cloudflared quick tunnel → 8095, writes `state/status/demo_url.txt`) |
| mm-tunnel | `2026NASA/infra/chat` | `./tunnel.sh` (cloudflared quick tunnel → Mattermost 8065) |
| bot | `2026NASA-bot/infra/orchestrator` | `bash /srv/hackathon/logs/run-bot.sh` |
| mwatch | `2026NASA-mauto` | `python3 -u infra/matlab/mwatch.py >> logs/mwatch.log` |
| mfixq | `logs/sup` | `/srv/hackathon/logs/run-mfixq.sh` (`2026NASA-main/infra/matlab/fixq_worker.py`) |
| live | `$HOME` | `2026NASA-api/infra/status/run_live.sh` (status every 5 min) |

## Restart script

`infra/ops/start_all.sh` starts each session the way it runs now, in dependency order (waits for :5433 → api → :8090 → web → :8095 → web-tunnel; :8065 → mm-tunnel; then bot, mwatch, mfixq, live). It is idempotent: a session that already exists is skipped. Dry run at 22:00 KST with everything up: all 8 printed `skip … (running)`, nothing was started. It sets an explicit `PATH` (nvm node, `~/.local/bin`, `/srv/hackathon/venv/bin`, `/usr/local/bin` for cloudflared) because cron starts with a minimal PATH. Log: `/srv/hackathon/logs/start_all.log`.

## Proposed @reboot entry (NOT applied)

Add with `crontab -e` as user hackathon, after the script is on `main` in a stable checkout (the path below uses `2026NASA-main`):

```
@reboot sleep 30 && /srv/hackathon/projects/2026NASA-main/infra/ops/start_all.sh >> /srv/hackathon/logs/start_all.log 2>&1
```

## After a restart: the URLs change

Both tunnels are Cloudflare **quick tunnels**, so each restart gives a new random `*.trycloudflare.com` URL.

- Web: `run_tunnel.sh` writes the new URL to `/srv/hackathon/state/status/demo_url.txt`. The `live` loop (`infra/status/live_status.py`, every 5 min) mirrors it to `/srv/hackathon/state/status/live_url.json`, and `tools/update_live_url.py` writes `docs/demo/live_url.json`. Once that file is committed to `main`, the static demo's "Live version →" header link points at the new server. The URL in the submission form (§4, §5) must be updated by hand.
- Mattermost: run `infra/chat/set-siteurl.sh <new url>` and repost the URL (as `tunnel.sh` says).
- The `live` session runs `infra/status/run_live.sh` from the `2026NASA-api` checkout. It only picks up the `live_url.json` mirror after that checkout moves to a `main` containing this change (run-api.sh checks out `origin/main` when api restarts).
