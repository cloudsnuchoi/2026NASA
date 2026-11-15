#!/usr/bin/env bash
# Asks for the orchestrator bot's DeepSeek key/model/base URL and writes infra/orchestrator/.env (mode 600).
# Prints nothing secret. Writes LLM_API_KEY, LLM_MODEL, LLM_BASE_URL and removes the old OPENAI_*/ORCH_MODEL lines.
set -u
F=/srv/hackathon/projects/2026NASA/infra/orchestrator/.env
[ -f "$F" ] || { echo "no $F (run infra/chat/provision.sh first)"; exit 1; }
put(){ grep -v "^$1=" "$F" > "$F.tmp"; printf '%s=%s\n' "$1" "$2" >> "$F.tmp"; mv "$F.tmp" "$F"; chmod 600 "$F"; }
cur(){ grep "^$1=" "$F" | tail -1 | cut -d= -f2-; }
read -rsp "DeepSeek API 키 붙여넣기 (화면에 안 보임, Enter=기존 유지): " K; echo
if [ -n "$K" ]; then put LLM_API_KEY "$K"; echo "✅ 키 저장"; unset K
elif [ -z "$(cur LLM_API_KEY)" ]; then echo "⚠️ 키가 아직 없습니다. 다시 실행해서 넣어 주세요."; fi
M0=$(cur LLM_MODEL); M0=${M0:-deepseek-flash}
read -rp "모델 (Enter=$M0): " M; put LLM_MODEL "${M:-$M0}"; echo "✅ 모델: ${M:-$M0}"
U0=$(cur LLM_BASE_URL); U0=${U0:-https://api.deepseek.com}
read -rp "base URL (Enter=$U0): " U; put LLM_BASE_URL "${U:-$U0}"; echo "✅ base URL: ${U:-$U0}"
for old in OPENAI_API_KEY OPENAI_BASE_URL ORCH_MODEL; do grep -v "^$old=" "$F" > "$F.tmp"; mv "$F.tmp" "$F"; done; chmod 600 "$F"
echo "끝. 에이전트에게 '봇 키 넣었어'라고 알려주세요."
