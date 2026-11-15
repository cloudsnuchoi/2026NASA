# 분업표 · 사람 담당 + 에이전트 레인 (2026-11-15 15:00 KST)

상태는 이슈 `STATUS:` 댓글과 [현황판](https://cloudsnuchoi.github.io/2026NASA/dashboard/)이 기준이다. 이 표는 "누가 무엇을 어디서" 하는지만 적는다. 바뀌면 이 파일을 PR로 고친다.

## 사람

| 사람 | 역할 | 담당 이슈 | 입력 | 출력 | 다음 작업 |
| --- | --- | --- | --- | --- | --- |
| Hylē | PM·풀스택·머지 | #16 #17 #8 #15 #22 | 모든 PR, 디자인 채널 결정 | PRD 확정, 머지, 배포 | PRD "확정" → PRD/SOT/사이트 PR |
| 김우찬 | MATLAB B (식생) | #24 | VPS `/data/processed/v1/inputs/` CSV ([TASKS.md](../matlab/TASKS.md)) | `field_dekad.csv`, `field_season.csv`, `coefficients.csv` → `/data/processed/v1/matlab/` | 공개키 등록 → VPS MATLAB 접속 → `coefficients.csv` 먼저 |
| 김윤성 | MATLAB A (기후) | #29 | 같음 | `drought_2012_county.csv`, `climate_annual.csv`, `calibration_params.csv` | VPS MATLAB 접속됨 → `ver` 확인 → 2012 비교 |
| 고지은 | UI/UX A (S0–S3) | #12 | ~uiux-design의 PRD 갭 분석 스레드, `model_api/fixtures/*.json` | `frontend/` S0–S3 | PRD 질문 1·2 답 → S1 3상태(필지/카운티/밖) |
| 하지민 | UI/UX B (S4–S7·슬라이드) | #13 #14 #21 | 같음 | `frontend/` S4–S7, 발표 슬라이드 | PRD 질문 3·4 답 → S4 탭 |
| 강다은 | 복셀 시뮬 | #30 | `sim_scene.json` 계약(TEAM_SPEC 7.5) | `sim/` 정적 데모·영상 | 정적 JSON 1개로 영상 |

## 에이전트 레인 (VPS, 사용자 `hackathon`, tmux)

| tmux | 모델 | 하는 일 | 입력 | 출력 | 다음 작업 |
| --- | --- | --- | --- | --- | --- |
| `imerg` | claude-sonnet-5-5 (headless) | GPM IMERG 일별·NLDAS-2 월별 카운티 적재 | Earthdata(GES DISC), 12주 카운티 | `county_imerg_daily`, `county_nldas_monthly`, `docs/spike-report-imerg.md` (브랜치 `feat/26-imerg`) | 끝나면 PR·머지 → 엔진에 NLDAS 반영 |
| `qa` | claude-opus-5-5 (headless) | QA·E2E·검증 (엔진·데이터 레인이 끝나 전환) | `model_api` 실DB, SOT 6절, PRD 갭 분석 | `model_api/tests/test_e2e_live.py`, `data_pipeline/qa_checks.sql`, `docs/QA-REPORT.md` (브랜치 `feat/qa-e2e`) | P0 버그 → 엔진 수정 레인 |
| `bot` | DeepSeek V4.1 Flash 기본 · 심화 Codex gpt-6.1-sol → gpt-6.1-terra → Claude Opus 5.5 → DeepSeek thinking | Mattermost 오케스트레이터 봇(1:1, DM, ~uiux-design) | 대화, 방 메모 `/srv/hackathon/state/memory/`, GitHub(읽기) | 스레드 답변 | PRD 확정 내용 맥락 반영 |
| `keywatch` (root) | — (규칙 기반) | 1:1 방 SSH 공개키 자동 등록·접속 안내 | 1on1-woochan, 1on1-yoonsung 글 | `authorized_keys`(터널 전용), 안내 글 | 상시 |
| `runner` | — | GitHub Actions self-hosted `amolla-vps` | PR·main push | `ci-ok` | 상시 |
| `mm-tunnel` | — | Mattermost Cloudflare quick tunnel | 127.0.0.1:8065 | trycloudflare 주소 | 주소 바뀌면 ~announce 공지 |
| (끝남) `data` | claude-sonnet-5-5 | 두 층 데이터 적재 | — | PR #36 머지, #26 종료 | `qa`로 전환 |
| (끝남) `engine` | claude-opus-5-5 | model_api 실DB 연결 | — | PR #37 머지 | `qa`로 전환. PRD 확정 뒤 수정 레인 재개 |
| 감독(Mac) | Claude Opus 5.5 | 레인 지휘, PR·머지, 30분 점검, 보고 | 모든 레인 로그 | PR, 이슈 STATUS | 상시 |

규칙: 한 레인 = 한 worktree·한 브랜치. 에이전트는 push하지 않고, 감독이 push·PR·머지한다(CI 초록, 충돌 없음만). 비밀값은 출력·커밋하지 않는다.
