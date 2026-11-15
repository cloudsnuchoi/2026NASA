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

제공자는 **DeepSeek**(OpenAI 호환). 베이스 URL과 모델은 `.env`에서 바꾸며, 코드에 고정하지 않는다. `bridge.py`는 `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `ORCH_MODEL`을 읽는다.

| 변수 | 기본·예시 | 설명 |
| --- | --- | --- |
| `OPENAI_API_KEY` | (비움) | DeepSeek API 키. `.env`에만 두고 커밋하지 않는다. |
| `OPENAI_BASE_URL` | `https://api.deepseek.com` | OpenAI 호환 엔드포인트. 다른 호환 제공자로 바꿀 수 있다. |
| `ORCH_MODEL` | `deepseek-v4.1-flash` | 호출할 모델 이름. **정확한 모델 id는 아직 검증하지 않았다.** 콘솔·문서에서 확인한 뒤 여기만 고친다. |

결정 원문: [docs/DECISIONS.md](../../docs/DECISIONS.md) (2026-11-15 12:28). 옵션 A(공식 Agents 플러그인)를 보조로 켤 때도 같은 OpenAI Compatible 설정(DeepSeek 베이스 URL·모델·키)을 쓰면 된다.

## 실행

```bash
cp .env.example .env    # OPENAI_API_KEY, OPENAI_BASE_URL, ORCH_MODEL 입력. MM_BOT_TOKEN은 provision.sh가 넣음
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
