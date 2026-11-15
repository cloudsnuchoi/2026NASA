# ONBOARDING · 10분 시작 가이드 (팀 아몰라)

> 대상: GitHub·Codex CLI를 처음 쓰는 팀원. 순서대로 따라 하고, 끝나면 **1:1 채널**에 보고한다.
> 시간은 모두 한국 시간(KST). 마감 2026-11-15 23:59.

## 역할표 (2026-11-15 09:30 KST 확정)

| 이름 | Mattermost 아이디 | 역할 | 1:1 채널 | 주로 쓰는 팀 채널 |
| --- | --- | --- | --- | --- |
| Hylē | `hyle` | 풀스택·백엔드·인프라·총괄 | (모든 1on1) | ~backend, ~announce |
| 김윤성 | `yoonsung` | MATLAB A (기후: POWER, SMAP·NLDAS, GEOS-S2S) | `1on1-yoonsung` | ~data-matlab |
| 김우찬 | `woochan` | MATLAB B (식생 HLS NDVI, NEX-GDDP 시나리오) | `1on1-woochan` | ~data-matlab |
| 고지은 | `jieun` | UI/UX A (S0–S3 화면, 디자인 시스템, 지도) | `1on1-jieun` | ~uiux-design |
| 하지민 | `jimin` | UI/UX B (S4–S7 화면, 카드·차트, 발표 슬라이드 디자인) | `1on1-jimin` | ~uiux-design, ~ppt-slides |
| 강다은 | `daeun` | three.js 복셀 시뮬·데모 영상 (**확인 필요**) | `1on1-daeun` | ~sim-voxel, ~demo-video |

## 모두 공통 (3분)

1. **채팅 접속:** Hylē가 ~announce와 카톡으로 준 주소(`https://….trycloudflare.com`)를 연다. 주소는 서버를 다시 켜면 바뀐다. 접속이 안 되면 카톡에서 새 주소를 확인한다.
2. **로그인:** 아이디는 위 표의 Mattermost 아이디, 비밀번호는 Hylē가 1:1로 준 임시 비밀번호. 로그인하면 바로 **프로필 → 보안 → 비밀번호 변경**.
3. **채널 확인:** 왼쪽에 `1:1 <내 이름>`(비공개), ~공지, 내 팀 채널이 보이면 OK.
4. 1:1 채널에 `안녕하세요, 준비 시작합니다`라고 쓴다. **orchestrator 봇**이 첫 할 일을 준다. 팀 채널에서 봇을 부를 때는 `@orchestrator 질문`처럼 쓴다. 명령 목록은 `!help`.

> 규칙: 키·토큰·비밀번호는 채팅에 붙이지 않는다. 막히면 캡처부터 올린다. 30분 넘게 혼자 붙잡지 않는다.

---

## UI/UX (고지은·하지민) · 복셀 시뮬 (강다은): 7분

1. **GitHub 초대 수락:** 메일함에서 "cloudsnuchoi invited you to cloudsnuchoi/2026NASA"를 찾아 **Accept**를 누른다. 메일이 없으면 <https://github.com/cloudsnuchoi/2026NASA/invitations>를 연다. 그래도 없으면 1:1 채널에 GitHub 아이디를 남긴다.
2. **터미널 열기:** macOS는 터미널, Windows는 PowerShell을 연다. `codex --version`을 입력해서 버전이 나오면 OK. agy를 쓰면 `agy --version`.
3. **처음 설정:** 홈 폴더에서 `codex`를 실행한다. [PROMPTS.md 1절 "처음 한 번" 프롬프트](PROMPTS.md#1-처음-한-번-설치로그인클론-프롬프트-git-쓰는-사람-uiux-시뮬-hylē)를 통째로 붙여 넣는다.
   - 브라우저 로그인 안내가 나오면, 화면에 나온 명령(`gh auth login …`)을 **내가 직접** 터미널에 입력한다. 그다음 브라우저에서 코드를 입력한다.
   - Codex가 "명령 실행할까요?"라고 물으면 `git`, `gh`, `npm`, `brew`, `winget`은 허용한다.
4. 마지막에 `SETUP OK: …` 줄이 보이면 캡처해서 1:1 채널에 올린다.
5. **작업 반복 (이게 전부):**
   1. 1:1 채널에서 봇(또는 Hylē)이 준 프롬프트를 복사한다. `[시작 블록]`부터 `[마무리 블록]`까지 전부다.
   2. 터미널에서 `cd ~/2026NASA`를 입력하고 `codex`(또는 `agy`)를 실행한 뒤 붙여 넣는다.
   3. 화면이 생기면 브라우저로 열어 **스크린샷**을 찍는다. 단축키는 macOS `Cmd+Shift+4`, Windows `Win+Shift+S`.
   4. 에이전트가 마지막에 `PR: https://github.com/cloudsnuchoi/2026NASA/pull/…`를 출력하면 끝.
6. **1:1 채널에 보고:** 아래 세 줄과 스크린샷을 올린다.
   ```
   PR: https://github.com/cloudsnuchoi/2026NASA/pull/<번호>
   한 일: <한 줄>
   막힌 점: <없음 또는 내용>
   ```
   봇이 리뷰해서 "머지 가능" 또는 "수정 프롬프트"를 준다. 수정이 필요하면 그 프롬프트를 다시 붙인다. **머지는 Hylē가 한다.** 내가 GitHub에서 Merge 버튼을 누르지 않는다.

**하지 말 것:** main에 직접 푸시, `--force`, 큰 파일(이미지·영상 10MB 이상) 커밋, `.env` 커밋, 남의 폴더 수정(UI는 `frontend/`, 시뮬은 `sim/`만).

---

## MATLAB (김윤성·김우찬): 7분, git 없음

1. **GitHub 초대 수락:** 위와 같다. 이슈를 읽는 데만 쓴다.
2. **브라우저 MATLAB 접속:** Hylē가 1:1로 준 주소로 연다. VPS의 MATLAB R2026b이고, 같은 서버의 데이터 폴더가 보인다.
   - **확인 필요:** 이 MATLAB은 세션이 하나뿐이다. 두 사람이 동시에 쓰면 충돌할 수 있다. Hylē가 시간대를 나누거나, 한 명은 개인 MATLAB(로컬이나 MATLAB Online)에서 작업한 뒤 결과 파일을 1:1 채널에 첨부한다. 그러면 Hylē가 서버로 옮긴다.
3. **노트북에서 Codex/agy 켜기:** 터미널에서 `codex`를 실행한다. 1:1 채널에서 봇이 준 **MATLAB 프롬프트**([PROMPTS.md 4절](PROMPTS.md#4-matlab-역할-김윤성--김우찬-git-없음) 틀)를 붙여 넣는다. 그러면 MATLAB 코드가 나온다.
4. **실행:** 브라우저 MATLAB에서 새 스크립트를 만들고 코드를 붙인다. 저장 위치는 `/srv/hackathon/projects/2026NASA/matlab/<climate|vegetation|scenario>/<이름>.m`이다. 그다음 Run.
5. **산출 확인:** `/srv/hackathon/data/processed/v1/matlab/`에 SOT 파일(예: `climate_annual.parquet`)과 `….manifest.json`, 확인 그림 `.png`가 생겼는지 본다. **같은 파일을 덮어쓰지 않는다.**
6. **1:1 채널에 보고:**
   ```
   스크립트: /srv/hackathon/projects/2026NASA/matlab/climate/power_fetch.m
   산출: /srv/hackathon/data/processed/v1/matlab/climate_annual.parquet (rows=…)
   그림: (캡처 첨부)
   막힌 점: …
   ```
   커밋과 PR은 Hylē(또는 오케스트레이터)가 한다.

---

## Hylē 체크 (운영자)

- 서버 준비: [infra/RUNBOOK.md](../infra/RUNBOOK.md)
- 각자에게 **자기 비밀번호 한 줄만** 1:1로 보낸다(`infra/chat/secrets/initial-passwords.txt`).
- 1:1 채널에 그냥 쓰면 그 사람에게 주는 **우선 지시**로 저장된다(봇은 조용함). 봇의 답을 원하면 `@orchestrator`를 붙인다. `!assign 지은 #12 지도부터`라고 쓰면 그 사람 채널로 작업이 간다.
- PR 머지: CI가 통과하고 스크린샷을 확인한 뒤 **Squash and merge**. 그다음 그 사람에게 다음 이슈를 `!assign`.
