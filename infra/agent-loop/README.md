# agent-loop — 노트북에 켜두는 내 에이전트

노트북에서 **터미널 창 하나만 켜두면** 끝이에요.
중앙 에이전트(`orchestrator` 봇)나 Hylē가 내 1:1 채널(`~1on1-<내아이디>`)에 `!task …`를 쓰면, 내 노트북의 Codex나 agy가 그 일을 해요.
일이 끝나면 PR이 열리고, 같은 스레드에 결과가 올라와요. 프롬프트를 복사해서 붙여넣을 필요가 없어요.

```text
Hylē / 중앙 봇 ──"!task #12 지도 화면"──▶ ~1on1-jieun (Mattermost)
                                            │  (5초마다 확인)
                                내 노트북 agent-loop ──▶ codex / agy 실행 (저장소 폴더 안)
                                            │
     스레드에 진행·결과 ◀──────────────────┤  커밋 → push → PR "Closes #12" → 이슈에 STATUS 댓글
```

- **3분마다 중앙 에이전트에 check-in** 해요: 지금 작업, 브랜치, 마지막 커밋, 커밋 안 된 파일 수, 바쁨/쉼. 한 사람당 글 하나를 계속 고쳐 써서 채팅이 시끄럽지 않아요.
- 봇이나 Hylē가 1:1 채널에 쓴 피드백(`!task`가 아닌 글)은 터미널에 `📩`로 보이고(삑 소리), **다음 작업 프롬프트에 자동으로 붙어요**.
- 내 노트북에서, **내 Codex·agy 계정**과 **내 GitHub 로그인**으로 돌아가요.
- 한 번에 한 작업만 해요. 그동안 온 `!task`는 줄을 서요.
- 바쁠 때와 끝났을 때는 `STATUS busy/idle/error`를 1:1 채널에 올려요.
- **머지는 안 해요.** 머지는 Hylē가 해요.

---

## 0. 전체 순서 (이 순서를 지켜야 해요)

| # | 누가 | 어디서 | 무엇을 | 끝난 표시 |
| --- | --- | --- | --- | --- |
| 1 | Hylē | VPS의 Claude Code | `infra/RUNBOOK.md` 0–5단계: Mattermost 기동 → 터널 주소 → `provision.sh` (팀·채널·계정·`orchestrator` 봇·`1on1-*` 채널·`~agent-status`) | 채팅 주소로 로그인됨 |
| 2 | Hylē | VPS의 Claude Code | RUNBOOK 6단계: 오케스트레이터 `bridge.py` 실행 (이 커밋 버전) | `docker logs` 에 `websocket connected as @orchestrator` |
| 3 | Hylē | Mattermost System Console | RUNBOOK 10단계 1번: 5명에게 **개인 액세스 토큰 권한** | 팀원 프로필 → 보안에 "개인 액세스 토큰" 메뉴가 보임 |
| 4 | Hylē | ~announce + 카톡 | 채팅 주소, 각자 임시 비밀번호(개인 DM), 아래 한 줄 설치 명령 공지 | – |
| 5 | 팀원 5명 | 각자 노트북 | 아래 1단계(토큰) → 2단계(한 줄 설치) → 터미널 켜두기 | 내 1:1 채널에 `🟢 @내아이디 agent-loop …` 글, 3분마다 시각이 바뀜 |
| 6 | Hylē | 아무 채널 | `!status` 로 5명 모두 🟢인지 확인 → `!assign 지은 #12` 처럼 첫 작업 배정 | 노트북이 `📥 받음 → ▶️ 시작 → ✅ 완료 · PR` 스레드를 올림 |

> 1–2가 안 끝났는데 5를 하면 "채팅 연결 실패"가 나요. 채팅 주소(quick tunnel)는 VPS에서 터널을 다시 켤 때마다 바뀌어요. 바뀌면 4. 문제 해결의 `--set-url`을 쓰세요.
> MATLAB 담당(윤성·우찬)도 설치는 똑같이 해요 (check-in·피드백용). 다만 `!assign`은 MATLAB 담당에게 `!task`를 자동으로 보내지 않아요.

## 1. Mattermost에서 개인 액세스 토큰 만들기 (처음 한 번, 2분)

1. 채팅 주소(공지·카톡으로 받은 `https://….trycloudflare.com`)로 로그인해요.
2. 오른쪽 위 **내 프로필 사진 → 프로필 → 보안(Security) → 개인 액세스 토큰(Personal Access Tokens) → 토큰 만들기(Create Token)**를 눌러요.
   - 이 메뉴가 안 보이면 Hylē에게 "토큰 권한 켜 주세요"라고 말해요 (아래 [Hylē가 할 일](#hylē가-할-일-한-번)).
3. 설명에 `agent-loop`이라고 쓰고 저장해요.
4. 화면에 나온 **Access Token** 값을 복사해요. 이 값은 **한 번만 보여요**. 설치할 때 한 번 붙여넣고 끝이에요.
   - ⚠️ 이 값은 비밀번호와 같아요. 채팅·카톡·GitHub에 절대 붙이지 마세요.

## 2. 한 줄 설치 (처음 한 번)

미리 필요한 것: `git`, `gh`(`gh auth login` 완료), Python 3, 그리고 `codex`나 `agy` 중 하나(로그인 완료).

**Windows** — PowerShell을 열고:

```powershell
irm https://raw.githubusercontent.com/cloudsnuchoi/2026NASA/main/infra/agent-loop/install.ps1 | iex
```

**macOS** — 터미널을 열고:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/cloudsnuchoi/2026NASA/main/infra/agent-loop/install.sh)"
```

설치하면서 세 가지를 물어요.
- **채팅 주소**: `https://xxxx.trycloudflare.com` (끝에 `/` 없이)
- **토큰**: 1단계에서 복사한 값. 붙여넣어도 화면에 안 보이는 게 정상이에요.
- **에이전트**: `codex` 또는 `agy`. 설치돼 있는 쪽이 기본값이에요.

마지막에 `연결 OK: @내아이디 · ~1on1-내아이디 · 지시 허용: orchestrator, hyle`가 나오면 성공이에요.
설정은 `~/.amolla-agent.json`(Windows는 `C:\Users\<나>\.amolla-agent.json`)에 저장돼요.

## 3. 켜두기

- 설치가 끝나면 바로 켜져요. **그 터미널 창을 닫지 마세요.** 최소화는 괜찮아요.
- 노트북이 잠들면 멈춰요. 충전기를 꽂고, 절전 모드를 꺼 두세요. 맥은 설치 스크립트가 `caffeinate`로 잠들기를 막아요.
- 끄기는 `Ctrl+C`예요. **다시 켤 때는 2단계 한 줄을 그대로 다시 실행**하면 돼요. 업데이트도 같이 돼요.
- 채팅에서 `!agent`라고 쓰면 지금 상태를 알려줘요.
- 직접 일을 시키고 싶으면, 1:1 채널에서 Hylē나 봇이 쓴 것처럼 `!task #이슈번호 할 일`을 쓰면 돼요. 기본 설정은 봇과 Hylē의 지시만 받아요. 나도 지시하고 싶으면 `~/.amolla-agent.json`의 `ALLOW_USERS`에 내 아이디를 더해요.

> 작업 전에 저장소에 커밋 안 된 변경이 있으면 agent-loop는 **작업을 시작하지 않고** 스레드에 알려줘요. 내 손으로 고친 게 있다면 먼저 Codex에게 "이 변경 커밋하고 PR 올려줘"라고 하거나 Hylē에게 물어보세요.

## 4. 문제 해결

| 증상 | 해결 |
| --- | --- |
| 봇이 "⚠️ 소식이 10분째 없어요" | 노트북이 잠들었거나 창이 닫힌 거예요. 2단계 한 줄을 다시 실행 |
| `채팅 서버 연결 실패` 반복 | 채팅 주소가 바뀌었을 수 있어요 (quick tunnel은 재시작마다 바뀜). ~announce에서 새 주소를 확인하고: macOS `~/.amolla-agent-venv/bin/python ~/.amolla-agent-venv/agent_loop.py --set-url https://새주소` / Windows `& "$HOME\.amolla-agent-venv\Scripts\python.exe" "$HOME\.amolla-agent-venv\agent_loop.py" --set-url https://새주소` 그다음 한 줄 설치를 다시 실행 |
| `토큰이 틀렸거나 만료됐어요 (401)` | 1단계로 새 토큰을 만들고, Windows는 `$env:AMOLLA_SETUP=1` 입력 후 / macOS는 `~/.amolla-agent.json`을 지우고 한 줄 설치를 다시 실행 |
| `채널을 못 찾음`·404 | 내 1:1 채널 이름이 `1on1-<내아이디>`가 아니면 설정 파일의 `CHANNEL`을 실제 이름으로 고쳐요 (채널 URL 끝부분) |
| `codex 명령을 찾을 수 없어요` | 새 터미널에서 `codex --version` / `agy --version`이 되는지 확인. 안 되면 설치·로그인부터 |
| ❌ 실패 (exit …) | 스레드의 마지막 줄들을 보고, 그대로 Hylē에게 보여주세요. 로그인 만료면 터미널에서 `codex` 또는 `agy`를 한 번 직접 실행해 로그인해요 |
| 변경 없음 — PR 안 만듦 | 에이전트가 파일을 못 고친 거예요. agy는 기본 설정에서 일부 명령이 자동 거절될 수 있어요 (아래 "에이전트 명령" 참고) |
| `git push` 실패 | `gh auth status`, `gh auth setup-git` 실행. GitHub 초대를 수락했는지 확인 |

---

## 설정 항목 (`~/.amolla-agent.json`, 같은 이름의 환경변수가 이기는 순서)

| 키 | 기본값 | 설명 |
| --- | --- | --- |
| `MM_URL` | – | 채팅 주소 |
| `MM_TOKEN` | – | 내 개인 액세스 토큰 (화면·채팅에 절대 출력 안 함) |
| `MM_TEAM` | `amolla` | 팀 이름 |
| `CHANNEL` | `1on1-<내아이디>` | 지켜볼 채널 |
| `AGENT` | `codex` | `codex` · `agy` (테스트용 `echo`) |
| `AGENT_CMD` | – | 명령 직접 지정, 예: `["agy","-p","{prompt}","--mode","accept-edits"]`. `{prompt}`가 없으면 프롬프트를 stdin으로 보내요 |
| `REPO_DIR` | `~/2026NASA` | 저장소 폴더 |
| `ALLOW_USERS` | `["orchestrator","hyle"]` | 지시를 받아들일 Mattermost 아이디 |
| `TRIGGER` | `!task` | 시작 단어 |
| `GIT_MODE` | `loop` | `loop`: agent-loop가 브랜치·커밋·push·PR·STATUS를 함. `agent`: 에이전트에게 맡김. `off`: git 안 건드림 |
| `HEARTBEAT_MIN` | `3` | 중앙 에이전트 check-in 주기(분). 3–5 권장. 봇은 10분 넘게 소식이 없으면 ⚠️ |
| `STATUS_CHANNEL` | (빈 값 = 내 1:1 채널) | check-in 글을 올릴 채널. `agent-status` 로 하면 모두의 현황이 한 채널에 모여요 |
| `PROGRESS_SEC` / `TIMEOUT_MIN` | 90 / 60 | 작업 중 진행 메시지 간격, 작업 제한 시간 |

### 에이전트 명령 (기본값과 이유)

- **Codex**: `codex exec --sandbox workspace-write -` (프롬프트는 stdin).
  `codex exec`는 기본이 읽기 전용이라 파일을 고치려면 `workspace-write`가 필요해요. 이 모드는 샌드박스 안에서 네트워크가 꺼져 있어요. 그래서 push·PR·STATUS는 agent-loop가 직접 해요 (`GIT_MODE=loop`).
- **agy (Antigravity CLI)**: `agy -p "<프롬프트>"` (headless).
  저장소 안 파일 읽기·쓰기는 자동 허용이에요. 승인이 필요한 셸 명령은 묻지 않고 **거절된 채로 계속**돼요 (종료 코드 0). 테스트 실행 같은 걸 허용하려면 본인이 agy 설정(`permissions.allow`)이나 `--mode`로 정해요. Windows에서 `agy`가 `.cmd`이면 긴 프롬프트는 `.git/amolla-task.md`에 쓰고, 그 파일을 읽으라고만 넘겨요.
- agent-loop는 `--dangerously-*`, `--yolo`, `danger-full-access`, `bypass` 플래그를 **거부**해요. 정말 필요하면 본인이 `AGENT_ALLOW_DANGEROUS=1`을 직접 설정해야 해요 (권장 안 함).
- 에이전트 앞에는 고정 지시가 붙어요: 이슈 범위만 작업, 브랜치 유지, 비밀값·대용량 파일 금지, 되돌리기 어려운 일은 "확인 필요"로 남기기, `SUMMARY:` 한 줄 출력. agent-loop는 `.env`·`*.pem`·`secrets/` 같은 파일이 커밋에 들어가면 커밋을 멈춰요.

---

## 봇·Hylē 쪽 (bridge.py와의 약속)

**메시지 형식** — 1:1 채널 `1on1-<username>`에 루트 메시지로 쓴다:

```text
!task #12 S1 지도 화면을 MapLibre로 만들고, fixtures로 동작하게 해.
(여러 줄 가능. 첫 줄 맨 앞이 반드시 !task. #번호는 선택)
```

- 보내는 사람이 `ALLOW_USERS`(기본 `orchestrator`, `hyle`)에 있어야 실행된다.
- `!task #N` → 브랜치 `feat/N-<slug>` (그 이슈 브랜치가 이미 있으면 재사용), PR 본문 `Closes #N`, 이슈에 `STATUS:` 댓글(🟢 진행 중 → 🟡 리뷰 대기, 실패 시 🔴 막힘). 형식은 `docs/PROMPTS.md`의 STATUS와 같다.
- agent-loop의 글에는 `props.amolla_agent` 값이 붙는다: `heartbeat`(check-in, 한 글을 `HEARTBEAT_MIN`마다 고쳐 씀), `status`(상태 바뀔 때 새 글), `reply`(스레드 답글).
- check-in `props`(모두 문자열): `member`, `state`(idle/busy/error/offline), `task`, `branch`, `commit`(`<sha> <제목> (<얼마 전>)`), `dirty`(커밋 안 된 파일 수), `queue`, `agent`, `notes`(받은 피드백 수), `every_min`, `ts`.
- 피드백: 허용된 사람(봇·Hylē)이 1:1 채널에 쓴 `!task`가 아닌 글은 모두 피드백으로 받는다 (최근 3개, 각 500자). 봇의 일반 답변도 포함된다.

**bridge.py가 하는 일 (이 커밋에서 추가)**
- `!assign 지은 #12 …` → 지금처럼 설명 메시지를 보내고, git 쓰는 팀원이면 LLM 답의 첫 코드블록(복사-붙여넣기 프롬프트)을 `!task #12 <프롬프트>`로 **같은 채널에 한 번 더** 보낸다. MATLAB 담당(git 안 씀)에게는 안 보낸다. 끄려면 `.env`에 `AUTO_DISPATCH=0`.
- `!task`, `!agent`로 시작하는 글과 `props.amolla_agent`가 붙은 글에는 **대답하지 않는다** (팀원 본인 계정으로 올라오지만 사람 말이 아니므로).
- check-in을 사람별로 모아 `!status`에 붙인다: `고지은 (@jieun): 🟡 busy · 작업 #12 … · \`feat/12-s1\` · abc1234 … · 변경 0 · 1분 전`. 1:1 채널에서는 그 사람만, 다른 채널에서는 전원.
  10분(`AGENT_SILENT_MIN`) 넘게 소식이 없으면 `⚠️ 응답 없음`, Ctrl+C로 끄면 `⚫ 꺼짐`, 한 번도 없으면 `⚪ 기록 없음`. bridge를 재시작하면 다음 check-in(최대 3분)까지 "기록 없음".
- **피드백 (LLM 안 씀, 규칙 기반, 같은 종류는 30분에 1번)**: 그 사람 1:1 채널에
  - check-in이 10분 넘게 끊기면 ⚠️ "다시 실행해 주세요 @hyle" (끊길 때마다 1번), 다시 들어오면 🟢 "다시 연결됐어요"
  - 작업 실패(`error`)로 바뀌면 🔴 "스레드 마지막 줄 보고 물어보세요 @hyle"
  - 쉬는 중인데 커밋 안 된 파일이 15분 넘게 남아 있으면 🟡 "커밋하고 PR 올리라고 하세요"
  - 그 밖의 내용 피드백(코드 리뷰 등)은 기존처럼 `!review`, 1:1 대화, `!assign`으로 한다.
- Hylē가 1:1 채널에 직접 `!task …`를 써도 된다. 봇은 조용히 있고 노트북이 실행한다.

## Hylē가 할 일 (한 번)

1. **개인 액세스 토큰 켜기**: `infra/chat/docker-compose.yml`에 `MM_SERVICESETTINGS_ENABLEUSERACCESSTOKENS: "true"`가 이미 있다. System Console → Integrations → Integration Management → *Enable Personal Access Tokens* 가 켜져 있는지만 확인.
2. **팀원에게 토큰 권한 주기** (일반 사용자는 기본으로 토큰을 못 만든다). 둘 중 하나:
   - System Console → User Management → Users → 사람 선택 → **Manage Roles** → *Allow this account to generate personal access tokens* 체크 → Save. 5명 반복.
   - 또는 VPS에서 `docker exec amolla-mattermost mmctl --local permissions role assign system_user_access_token yoonsung woochan jieun jimin daeun` (형식은 Mattermost 공식 문서 기준. 이 역할에 쓰는 건 **미검증** — 실패하면 위 UI로).
3. **봇 계정**: `infra/chat/provision.sh`가 만든 `orchestrator` 봇이 각 `1on1-*` 채널에 이미 들어가 있어야 한다 (provision.sh가 처리). 새로 할 일 없음. bridge.py를 이 커밋 버전으로 재시작.
4. 채팅 주소가 바뀌면 ~announce에 새 주소를 올린다. 팀원은 `--set-url`로 바꾼다 (4. 문제 해결).
