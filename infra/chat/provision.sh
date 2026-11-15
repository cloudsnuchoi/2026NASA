#!/usr/bin/env bash
# Provision team "amolla" on the local Mattermost (idempotent-ish; safe to re-run).
#  - team, public channels, 6 users (temp passwords -> secrets/initial-passwords.txt, git-ignored)
#  - bot "orchestrator" + access token -> ../orchestrator/.env (git-ignored)
#  - private channels 1on1-<username> = member + hyle + orchestrator
# Requires: container amolla-mattermost running with local mode (docker-compose.yml), curl, python3, openssl.
set -euo pipefail
cd "$(dirname "$0")"
TEAM="${TEAM:-amolla}"
TEAM_DISPLAY="${TEAM_DISPLAY:-아몰라 (NASA Space Apps 2026)}"
MM="${MM_LOCAL_URL:-http://127.0.0.1:${MM_HOST_PORT:-8065}}"
ADMIN="hyle"
SECRETS="secrets"; PWFILE="$SECRETS/initial-passwords.txt"
ORCH_ENV="../orchestrator/.env"
mkdir -p "$SECRETS"; chmod 700 "$SECRETS"; touch "$PWFILE"; chmod 600 "$PWFILE"

mmctl() { docker exec amolla-mattermost mmctl --local --suppress-warnings "$@"; }
jsonget() { python3 -c "import json,sys; d=json.load(sys.stdin); print(eval(sys.argv[1]))" "$1" 2>/dev/null; }
genpw() { echo "Am$(openssl rand -base64 18 | tr -dc 'A-Za-z0-9' | head -c 14)!7"; }
say() { printf '\n== %s\n' "$*"; }

say "server ping"
curl -fsS "$MM/api/v4/system/ping" >/dev/null && echo ok

say "users"
existing="$(mmctl --json user list --all 2>/dev/null | python3 -c 'import json,sys
try: print(" ".join(u["username"] for u in json.load(sys.stdin)))
except Exception: print("")')"
grep -v '^#' members.tsv | while IFS=$'\t' read -r user name role area admin; do
  [[ -z "$user" ]] && continue
  if [[ " $existing " == *" $user "* ]]; then echo "skip $user (exists)"; continue; fi
  pw="$(genpw)"
  extra=(); [[ "$admin" == yes ]] && extra+=(--system-admin)
  mmctl user create --username "$user" --email "${user}@amolla.local" --password "$pw" \
    --nickname "$name" --firstname "$name" --locale ko --email-verified --disable-welcome-email "${extra[@]}" >/dev/null
  printf '%s\t%s\t%s\n' "$user" "$name" "$pw" >> "$PWFILE"
  echo "created $user ($name)"
done

say "team $TEAM"
mmctl team create --name "$TEAM" --display-name "$TEAM_DISPLAY" --email "${ADMIN}@amolla.local" --private >/dev/null 2>&1 \
  && echo created || echo "exists (ok)"
users_all="$(grep -v '^#' members.tsv | cut -f1 | xargs)"
mmctl team users add "$TEAM" $users_all >/dev/null 2>&1 || true
echo "members: $users_all"

say "public channels"
while IFS='|' read -r ch disp purpose; do
  mmctl channel create --team "$TEAM" --name "$ch" --display-name "$disp" --purpose "$purpose" >/dev/null 2>&1 \
    && echo "created ~$ch" || echo "~$ch exists (ok)"
  mmctl channel users add "$TEAM:$ch" $users_all >/dev/null 2>&1 || true
done <<'CH'
announce|📢 공지|Hylē 공지 전용. 일정·결정·터널 URL 변경
uiux-design|UI·UX·디자인|고지은·하지민 화면/디자인 (frontend/)
demo-video|데모 영상|영상 콘티·녹화·편집
ppt-slides|발표 슬라이드|슬라이드·제출 페이지 문구
data-matlab|데이터·MATLAB|김윤성·김우찬 MATLAB 산출 (SOT 4절 5종 파일)
backend|백엔드·API·RAG|model_api, data_pipeline, rag, infra
sim-voxel|복셀 시뮬|three.js 복셀 시뮬 (sim/)
random|잡담|아무 이야기
CH

say "bot orchestrator (REST, as $ADMIN)"
admin_pw="$(awk -F'\t' -v u="$ADMIN" '$1==u{print $3}' "$PWFILE" | tail -1)"
[[ -n "$admin_pw" ]] || { echo "need $ADMIN password in $PWFILE (or set ADMIN_PW env)"; admin_pw="${ADMIN_PW:?}"; }
login_hdr="$(curl -fsS -D - -o /dev/null -H 'Content-Type: application/json' \
  -d "{\"login_id\":\"$ADMIN\",\"password\":\"$admin_pw\"}" "$MM/api/v4/users/login" | tr -d '\r' | awk -F': ' 'tolower($1)=="token"{print $2}')"
[[ -n "$login_hdr" ]] || { echo "admin login failed"; exit 1; }
AUTH=(-H "Authorization: Bearer $login_hdr" -H 'Content-Type: application/json')
bot_id="$(curl -fsS "${AUTH[@]}" "$MM/api/v4/users/username/orchestrator" 2>/dev/null | jsonget 'd["id"]' || true)"
if [[ -z "$bot_id" ]]; then
  bot_id="$(curl -fsS "${AUTH[@]}" -d '{"username":"orchestrator","display_name":"Orchestrator","description":"아몰라 중앙 에이전트 (infra/orchestrator/bridge.py)"}' \
    "$MM/api/v4/bots" | jsonget 'd["user_id"]')"
  echo "created bot $bot_id"
else echo "bot exists $bot_id"; fi
if ! grep -q '^MM_BOT_TOKEN=.\+' "$ORCH_ENV" 2>/dev/null; then
  tok="$(curl -fsS "${AUTH[@]}" -d '{"description":"bridge.py"}' "$MM/api/v4/users/$bot_id/tokens" | jsonget 'd["token"]')"
  [[ -f "$ORCH_ENV" ]] || cp ../orchestrator/.env.example "$ORCH_ENV"
  sed -i '/^MM_BOT_TOKEN=/d' "$ORCH_ENV"; echo "MM_BOT_TOKEN=$tok" >> "$ORCH_ENV"; chmod 600 "$ORCH_ENV"
  echo "token written to $ORCH_ENV"
else echo "token already in $ORCH_ENV"; fi
mmctl team users add "$TEAM" orchestrator >/dev/null 2>&1 || true
for ch in announce uiux-design demo-video ppt-slides data-matlab backend sim-voxel random; do
  mmctl channel users add "$TEAM:$ch" orchestrator >/dev/null 2>&1 || true
done

say "private 1on1 channels"
grep -v '^#' members.tsv | while IFS=$'\t' read -r user name role area admin; do
  [[ -z "$user" || "$user" == "$ADMIN" ]] && continue
  ch="1on1-$user"
  mmctl channel create --team "$TEAM" --name "$ch" --display-name "1:1 $name" --private \
    --purpose "$name ↔ Hylē + orchestrator. 할 일·프롬프트·피드백" >/dev/null 2>&1 && echo "created $ch" || echo "$ch exists (ok)"
  mmctl channel users add "$TEAM:$ch" "$user" "$ADMIN" orchestrator >/dev/null
done

say "done"
echo "passwords: $(realpath "$PWFILE")  (send each person ONLY their own line, via 1:1 DM/카톡; ask them to change it)"
echo "bot token: $(realpath "$ORCH_ENV")"
