#!/usr/bin/env bash
# agent-loop 한 줄 설치·실행 (macOS / Linux). 다시 실행하면 업데이트 후 바로 켜져요.
#   bash -c "$(curl -fsSL https://raw.githubusercontent.com/cloudsnuchoi/2026NASA/main/infra/agent-loop/install.sh)"
# 설정 다시 하기: 위 줄 끝에 ' _ --setup' 을 붙이거나 ~/.amolla-agent.json 을 지우고 다시 실행.
set -euo pipefail
REPO="cloudsnuchoi/2026NASA"
DIR="${REPO_DIR:-$HOME/2026NASA}"
VENV="$HOME/.amolla-agent-venv"
say() { printf '\n▶ %s\n' "$*"; }
die() { printf '\n❌ %s\n' "$*"; exit 1; }

say "도구 확인"
command -v python3 >/dev/null || die "python3가 없어요. macOS: xcode-select --install (또는 brew install python)"
command -v git >/dev/null || die "git이 없어요. macOS: xcode-select --install"
command -v gh >/dev/null || die "gh가 없어요. macOS: brew install gh, 그다음 gh auth login"
gh auth status >/dev/null 2>&1 || die "GitHub 로그인이 안 돼 있어요. 터미널에서: gh auth login -h github.com -p https -w"
gh auth setup-git >/dev/null 2>&1 || true
AG=""
command -v codex >/dev/null && AG="codex"
[[ -z "$AG" ]] && command -v agy >/dev/null && AG="agy"
[[ -n "$AG" ]] || echo "⚠ codex 도 agy 도 안 보여요. 설치·로그인 먼저 해 주세요 (설정은 계속 진행)."
echo "python3 · git · gh OK ${AG:+· 에이전트 후보: $AG}"

say "저장소 ($DIR)"
if [[ -d "$DIR/.git" ]]; then
  if [[ -z "$(git -C "$DIR" status --porcelain)" ]]; then
    [[ "$(git -C "$DIR" rev-parse --abbrev-ref HEAD)" == "main" ]] && { git -C "$DIR" pull --ff-only -q || echo "⚠ pull 실패 (계속)"; }
  else echo "⚠ 커밋 안 된 변경이 있어요. 작업은 깨끗한 상태에서만 시작돼요 (git status 확인)"; fi
else
  gh repo clone "$REPO" "$DIR" -- -q
fi
git -C "$DIR" fetch -q origin main || echo "⚠ fetch 실패 (계속)"

say "파이썬 환경 ($VENV)"
[[ -x "$VENV/bin/python" ]] || python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install -q --disable-pip-version-check "requests>=2.31,<3"

# 실행 파일은 저장소 밖에 복사해서 씀 (브랜치를 바꿔도 loop가 안 바뀌게)
LOOP="$VENV/agent_loop.py"
git -C "$DIR" show origin/main:infra/agent-loop/agent_loop.py > "$LOOP.new" && mv "$LOOP.new" "$LOOP"
CFG="${AMOLLA_AGENT_CONFIG:-$HOME/.amolla-agent.json}"
if [[ ! -f "$CFG" || "${1:-}" == "--setup" ]]; then
  say "설정 (채팅 주소·토큰·에이전트)"
  echo "토큰 만드는 법: README 1단계 (Mattermost → 프로필 → 보안 → 개인 액세스 토큰)"
  REPO_DIR="$DIR" AGENT="${AGENT:-${AG:-codex}}" "$VENV/bin/python" "$LOOP" --setup --check < /dev/tty || true
fi

say "연결 확인"
"$VENV/bin/python" "$LOOP" --check || die "연결 실패. 주소가 바뀌었으면: $VENV/bin/python $LOOP --set-url <새주소>"

say "실행 — 이 터미널 창을 닫지 마세요 (끄기: Ctrl+C, 다시 켜기: 같은 한 줄 다시 실행)"
if [[ "$(uname)" == "Darwin" ]] && command -v caffeinate >/dev/null; then
  exec caffeinate -i "$VENV/bin/python" "$LOOP"   # 맥이 잠들지 않게
fi
exec "$VENV/bin/python" "$LOOP"
