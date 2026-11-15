# infra/orchestrator · 중앙 오케스트레이터

Mattermost 1:1 채널(`1on1-<username>`)과 팀 채널(@orchestrator 멘션)에서 팀원에게 **다음 할 일 → Codex/agy에 붙일 프롬프트 → 완료 기준 → 보고할 것**을 준다. Hylē의 지시가 항상 우선한다.

## 두 가지 선택지

### A. Mattermost 공식 Agents 플러그인 (확인 결과: 이번 용도에는 부족)

2026-11-15 KST 공식 문서 기준.

- 플러그인 `mattermost-ai` v2.x는 서버 12.0.0 이상이 필요하다. 그래서 `docker-compose.yml`을 12.0.2로 고정했다.
- **OpenAI-compatible** 제공자를 지원한다. Team Edition처럼 라이선스가 없으면 "Free" 등급이다.
- Free 등급에서 되는 것: 에이전트 1개, LLM 제공자 1개, **에이전트 DM**, 비전, 개인 프롬프트, Mattermost 내장 도구(**읽기 전용**).
- Free 등급에서 안 되는 것:
  - 채널 안에서 멘션해 쓰는 에이전트(Professional 이상)
  - 원격·외부 MCP 서버(GitHub MCP 같은 것, Enterprise 이상)
  - 쓰기 도구(Enterprise 이상)
  - 채널 자동 응답(Enterprise Advanced)
- 결론: 1on1 비공개 채널에서 답하기, 팀 채널 멘션, GitHub 상태 읽기, `!assign` 같은 푸시는 플러그인만으로 안 된다. **B를 기본으로 쓴다.** A는 팀원이 개인 DM으로 일반 질문할 보조 도구로만 켤 수 있다. 설치 방법: System Console → Plugins에서 릴리스 tar.gz 업로드 → Agents → OpenAI Compatible에 키와 모델 입력.
- 참고(미검증): 문서에는 "라이선스 없이 Enterprise Edition 이미지를 쓰면 Entry 라이선스가 자동 적용되어 Enterprise처럼 동작한다"고 쓰여 있다. 그러면 채널 에이전트와 원격 MCP가 열릴 수 있다. 다만 Entry 등급의 다른 제한은 확인하지 않았다. 이미지를 `mattermost-enterprise-edition:12.0.2`로 바꿀지는 Hylē가 판단한다.
- 출처:
  - <https://docs.mattermost.com/administration-guide/configure/agents-admin-guide> (License requirements 표)
  - <https://github.com/mattermost/mattermost-plugin-agents> (System Requirements)

### B. `bridge.py` (기본)

- Mattermost 웹소켓을 듣는다. 봇 토큰으로 접속하고 `authentication_challenge`를 보낸다.
- 반응하는 곳:
  - `1on1-*` 채널: 팀원 메시지에 답한다.
  - Hylē가 1on1 채널에 그냥 쓴 메시지: 그 팀원의 **우선 지시**로 저장만 하고, 봇은 답하지 않는다.
  - 팀 채널: @orchestrator 멘션이 있을 때만 스레드로 답한다.
- 시스템 컨텍스트:
  - `AGENTS.md`, `docs/CHECKLIST.md`, `docs/PROMPTS.md`, `docs/SOT.md`, `docs/PRD.md`, `docs/TEAM_SPEC.md` (예산 안에서 잘라 넣음)
  - GitHub **읽기 전용** REST: 이슈 본문 `## 제안 담당`에 이름이 있는 열린 이슈, 열린 PR과 CI 상태
- 채널별 대화 기억은 `state/context.json`에 둔다. git에는 올리지 않는다.
- 명령: `!help`, `!status`, `!review <PR#>`, `!reset`. Hylē 전용: `!assign <이름> #<이슈> [지시]`, `!note <이름> <지시>`.
  - Mattermost는 `/`로 시작하는 메시지를 서버 명령으로 가로챈다. 그래서 `!`를 쓴다.
- 봇은 GitHub에 쓰지 않는다. 머지, 이슈 수정, MATLAB 결과 커밋은 Hylē(또는 Hylē의 에이전트)가 한다.


## LLM

제공자는 **DeepSeek**(OpenAI 호환). 베이스 URL과 모델은 `.env`에서 바꾸며, 코드에 고정하지 않는다. `bridge.py`는 `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`을 읽고, 없으면 예전 이름 `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `ORCH_MODEL`을 대체값으로 읽는다. VPS에서는 `setup-bot-key`가 숨김 입력으로 넣어 준다.

| 변수 | 기본·예시 | 설명 |
| --- | --- | --- |
| `LLM_API_KEY` | (비움) | DeepSeek API 키. `.env`에만 두고 커밋하지 않는다. |
| `LLM_BASE_URL` | `https://api.deepseek.com` | OpenAI 호환 엔드포인트. 다른 호환 제공자로 바꿀 수 있다. |
| `LLM_MODEL` | `deepseek-flash` | 모델 id. 현재 DeepSeek-V4.1-Flash(공식 문서 2026-11-15 확인). 레거시 `deepseek-v4-flash`는 쓰지 않는다. |

동작 규칙:
- 일상 대화와 `!assign` 문구: thinking 끔(`extra_body={"thinking":{"type":"disabled"}}`).
- `!review`: thinking 켬(`reasoning_effort="high"`). thinking 모드에서 `temperature`는 무시되므로 보내지 않는다.
- tools를 쓰는 thinking 요청은 assistant 메시지의 `reasoning_content`를 이후 요청에 그대로 다시 보낸다(안 보내면 400). `reasoning_content`는 채팅에 게시하지 않는다.
- 캐시: system 프롬프트+저장소 문서를 매 요청 맨 앞에 같은 순서로 두고, 시각·대화 상대·Hylē 지시·GitHub 상태는 마지막 사용자 메시지 뒤에 붙인다. 로그에 `cache_hit`/`cache_miss`(`prompt_cache_hit_tokens`/`prompt_cache_miss_tokens`)가 남는다.
- 429·5xx는 1초·3초 백오프로 2번 재시도하고, 그래도 실패하면 채팅에 "LLM 응답 지연"만 남긴다.

결정 원문: [docs/DECISIONS.md](../../docs/DECISIONS.md) (2026-11-15 12:28). 옵션 A(공식 Agents 플러그인)를 보조로 켤 때도 같은 OpenAI Compatible 설정(DeepSeek 베이스 URL·모델·키)을 쓰면 된다.

## 실행

```bash
cp .env.example .env    # VPS에서는 setup-bot-key로 LLM_API_KEY·LLM_MODEL·LLM_BASE_URL 입력. MM_BOT_TOKEN은 provision.sh가 넣음
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python bridge.py --dry-run --mock-llm     # 오프라인, 키 없이
.venv/bin/python bridge.py --dry-run                # 오프라인, 실제 LLM
.venv/bin/python bridge.py --no-post                # Mattermost를 듣되 게시 대신 출력
.venv/bin/python bridge.py                          # 운영
```

Docker로 띄우는 방법은 [infra/RUNBOOK.md](../RUNBOOK.md) 6단계를 본다.

## 테스트

```bash
pip install -r requirements-dev.txt && pytest -q tests && ruff check .
```

## 모델 계층화 (2026-11-15)

| 질문 | 모델 순서 | 비고 |
| --- | --- | --- |
| 인사·상태·짧은 질문 | DeepSeek V4.1 Flash (`deepseek-flash`, thinking 끔) | 3~5줄로만 답함 |
| 코드, MATLAB 오류, 데이터·알고리즘·물리 질문, `!deep` | ① Codex `gpt-6.1-sol` → ② Codex `gpt-6.1-terra` → ③ Claude Opus 5.5 → ④ DeepSeek thinking(high) | 실패, 사용량 한도, 120초 초과면 다음 순위 |
| `!review` | DeepSeek V4.1 Flash thinking(high) | 기존 그대로 |

- 판정은 `wants_deep()` 정규식이다. 답변 끝에 실제로 답한 모델이 `— 답변: <모델>`로 붙는다.
- 심화 모델은 모두 VPS headless이고 읽기 전용이다.
  - Codex: `codex exec -m <model> -s read-only --skip-git-repo-check --ephemeral -C <repo> -o <file> -`. `--search`를 주지 않으므로 웹 검색은 꺼져 있다. read-only 샌드박스라 명령 실행 시 네트워크와 쓰기가 막힌다. `shell_environment_policy.inherit="core"`.
  - Claude: `claude -p --model claude-opus-5-5 --allowedTools Read Grep Glob --disallowedTools Bash Edit Write … WebFetch WebSearch`.
  - 둘 다 `CLAUDE_REPO`(기본 `/srv/hackathon/projects/2026NASA-ro`, `.env`·비밀이 없는 main 사본)에서 돈다. 키·토큰처럼 보이는 환경 변수는 지우고 넘긴다.
- 환경 변수: `CODEX_BIN`, `CODEX_MODELS`(기본 `gpt-6.1-sol,gpt-6.1-terra`), `CLAUDE_BIN`, `CLAUDE_MODEL`, `CLAUDE_REPO`, `CLAUDE_TIMEOUT`(초, 각 단계마다). 값을 비우면 그 단계를 끈다.

## 대화 기록과 방 메모

- 대화 기록은 방(채널)마다 하나다. 그 방의 스레드 대화도 모두 같은 기록에 쌓이고, 모든 모델(DeepSeek, Codex, Claude)이 이 기록을 같이 쓴다. 최근 `HISTORY_TURNS`(기본 20)턴을 매 요청에 넣는다. 저장 위치는 `STATE_PATH`(VPS `/srv/hackathon/state/context.json`)이다.
- 방 메모: `MEMORY_DIR/<채널>.md`(VPS `/srv/hackathon/state/memory/`). 담당 이슈, 지금 하는 단계, 막힌 점, 결정된 것, 지난 대화 요약을 적는다.
  - 답할 때마다 DeepSeek Flash가 백그라운드에서 갱신한다.
  - 20턴을 넘어 기록에서 밀려난 대화는 요약에 합친다.
  - 비밀값처럼 보이는 문자열은 지운다. 재시작해도 남는다.
  - 모든 모델의 맥락에 메모가 들어간다.
- 재시작 복구: 마지막으로 처리한 글 시각을 `cursor.json`에 저장한다. 다시 연결되면 봇이 들어 있는 모든 채널에서 그 뒤의 글을 읽어 순서대로 처리한다.
- 봇은 질문 글의 스레드에 답한다. SSH 공개키 글에는 답하지 않는다(VPS keywatch가 처리한다).
