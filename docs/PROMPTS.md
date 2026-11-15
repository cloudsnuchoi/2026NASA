# PROMPTS · Codex CLI / agy CLI에 붙여 넣는 프롬프트

> 팀원은 git 명령을 외우지 않는다. **프롬프트를 통째로 복사해서 붙여 넣으면** 에이전트가 브랜치·커밋·PR까지 한다.
> 오케스트레이터 봇(Mattermost `1on1-<이름>`)이 이 파일의 틀에 이슈 번호와 할 일을 채워서 준다.
> 기준 문서: [AGENTS.md](../AGENTS.md), [SOT.md](SOT.md), [TEAM_SPEC.md](TEAM_SPEC.md), [CHECKLIST.md](CHECKLIST.md).

## 0. 공통 규칙 (에이전트가 물어볼 때)

- Codex나 agy가 **"이 명령 실행해도 돼요?"** 하고 물으면 `git`, `gh`, `npm`, `pip`, `ruff`, `pytest`는 허용한다. 처음 보는 `rm -rf`, `sudo`, 키·비밀번호 입력 요청은 **거절**하고 1:1 채널에 캡처를 올린다.
- 키, 토큰, 비밀번호는 프롬프트나 채팅에 절대 붙이지 않는다.
- 막히면 에러 화면을 캡처해 1:1 채널에 올린다. 혼자 30분 이상 붙잡지 않는다.

---

## 1. 처음 한 번: 설치·로그인·클론 프롬프트 (git 쓰는 사람: UI/UX, 시뮬, Hylē)

먼저 GitHub 메일함에서 **`cloudsnuchoi/2026NASA` 초대 수락**을 누른다. 그다음 터미널에서 빈 폴더(예: 홈)를 열고 `codex`(또는 `agy`)를 실행한 뒤 아래를 통째로 붙인다.

```text
나는 git과 GitHub를 처음 쓴다. 아래를 순서대로 해 주고, 각 단계가 끝날 때마다 한국어 한 줄로 결과를 알려줘. 실패하면 멈추고 원인과 해결 방법을 쉽게 설명해.
1. 내 OS(macOS / Windows / Linux)를 확인해.
2. git이 없으면 설치해. macOS: `xcode-select --install` 또는 `brew install git`. Windows: `winget install --id Git.Git -e`. Linux: 패키지 관리자.
3. GitHub CLI(gh)가 없으면 설치해. macOS: `brew install gh`. Windows: `winget install --id GitHub.cli -e`. Linux: https://github.com/cli/cli/blob/trunk/docs/install_linux.md 방법.
4. `gh auth status`로 로그인 상태를 확인해. 로그인이 안 돼 있으면 내가 직접 할 수 있게, 터미널에 입력할 명령 `gh auth login -h github.com -p https -w`를 보여주고 "브라우저에서 코드 입력 후 엔터"라고 안내한 뒤 기다려. 나 대신 토큰을 만들거나 붙여 넣지 마.
5. `gh auth setup-git`을 실행해.
6. git 이름과 이메일이 비어 있으면 `gh api user`로 내 GitHub 아이디를 확인해. 그다음 `git config --global user.name "<아이디>"`, `git config --global user.email "<아이디>@users.noreply.github.com"`으로 설정해.
7. `gh repo clone cloudsnuchoi/2026NASA ~/2026NASA`로 저장소를 받고(이미 있으면 그 폴더에서 `git pull`), 그 폴더 경로를 알려줘.
8. `~/2026NASA/AGENTS.md`와 `~/2026NASA/docs/ONBOARDING.md`를 읽고 내 역할에 해당하는 부분을 다섯 줄로 요약해.
9. 마지막 줄에 `SETUP OK: <폴더경로> <GitHub아이디>`를 출력해.
```

끝나면 `SETUP OK` 줄을 캡처해서 1:1 채널에 올린다. 그다음부터는 **항상 `~/2026NASA` 폴더에서** `codex` 또는 `agy`를 실행한다.

---

## 2. 마무리 블록 (git 쓰는 역할 공통, 모든 작업 프롬프트 맨 끝에 그대로 붙임)

```text
[마무리 블록 — 작업이 끝나면 그대로 실행]
아래를 순서대로 실행하고 단계마다 결과를 한 줄로 보여줘. 실패하면 멈추고 에러 원문과 해결책을 한국어로 설명해. 강제 푸시(--force), main 직접 푸시, git add -f는 절대 하지 마.
1. `git status`로 바뀐 파일을 보여줘. .env, 키·토큰·비밀번호, data/ 아래 파일, 10MB 넘는 파일, *.tif/*.nc/*.zip이 있으면 커밋하지 말고 나에게 물어봐.
2. 지금 브랜치가 main이면 `git checkout -b feat/<이슈번호>-<짧은-영문-slug>`로 새 브랜치를 만들어(작업 내용은 그대로 따라온다). 이미 feat/<이슈번호>-… 브랜치면 그대로 써.
3. 검사:
   - .py를 바꿨으면 저장소 루트에서 `ruff check .`와 `python -m pytest -q`를 돌려(없으면 `pip install ruff pytest`). 테스트 폴더가 없으면 pytest는 건너뛰어.
   - frontend/ 또는 sim/에 package.json이 있고 그 폴더를 바꿨으면, 그 폴더에서 `npm install`, `npm run lint --if-present`, `npm run build --if-present`를 돌려.
   - 실패하면 고치고 다시 돌려. 세 번 실패하면 멈추고 보고해.
4. 내가 바꾼 파일만 `git add <파일들>` 하고 `git commit -m "<type>(<scope>): <영문 요약>"` 해. Conventional Commits 형식: type은 feat|fix|docs|test|chore, scope는 frontend|sim|model|data|rag|infra|docs|matlab.
5. `git fetch origin`과 `git rebase origin/main`을 실행해. 충돌이 나면 `git rebase --abort` 하고 멈춘 뒤 충돌 파일 목록을 보여줘.
6. `git push -u origin HEAD`.
7. PR이 없으면 `gh pr create --base main --title "<커밋 메시지와 같게>" --body-file <임시파일>`로 만들어. 본문은 다음과 같아:
   Closes #<이슈번호>

   ## 무엇을
   (한국어 2~3줄)
   ## 확인 방법
   (명령 또는 클릭 순서)
   ## 스크린샷
   1:1 채널에 올림
   ## SI
   Codex/agy CLI 사용 (docs/si-log.md 참고)
   이미 PR이 있으면 푸시만 하면 된다. `gh pr view --json url -q .url`로 주소를 확인해.
8. 마지막 줄에 정확히 `PR: <PR 주소>` 한 줄만 출력해.
머지는 하지 마. 머지는 Hylē가 한다.
```

> 같은 이슈를 이어서 하는 두 번째 PR부터는 같은 브랜치에서 위 블록을 다시 붙이면 된다. 다음 이슈를 시작할 때는 아래 **시작 블록**부터 붙인다.

### 시작 블록 (새 이슈 시작할 때 프롬프트 맨 앞)

```text
[시작 블록] 먼저 `git status`를 확인해. 커밋 안 된 변경이 있으면 멈추고 나에게 물어봐. 깨끗하면 `git checkout main`, `git pull --ff-only`, `git checkout -b feat/<이슈번호>-<짧은-영문-slug>`를 실행해.
그다음 AGENTS.md, docs/SOT.md, docs/TEAM_SPEC.md를 읽고 이슈 #<이슈번호> 범위만 작업해. `gh issue view <이슈번호>`로 이슈 본문을 읽어.
```

---

## 3. 역할별 작업 프롬프트 틀

`<…>`는 봇 또는 Hylē가 채운다. 구조는 **[시작 블록] + 할 일 + 제약 + [마무리 블록]** 이다.

### 3.1 UI/UX A · 고지은 (S0–S3, `frontend/`)

```text
[시작 블록] (이슈 #<N>, slug <slug>)
할 일: <예: frontend/에 Vite+React+TypeScript 앱을 만들고 S1 지도 화면을 구현해. MapLibre GL, 아이오와 본편 카운티 중심, 서비스 지역 밖 클릭 시 빨간 오버레이와 안내 문구.>
제약:
- API가 없으면 `VITE_API_BASE`가 빈 값일 때 frontend/src/fixtures/*.json(=SOT 6절 예시와 같은 필드)을 읽어.
- 화면 문구는 TEAM_SPEC 2.2 규칙. 「판단을 대체하지 않음」 문구를 숨기지 마. NASA 로고 금지.
- 새 라이브러리는 꼭 필요한 것만. package-lock.json도 커밋.
- 완료 후 `npm run dev`로 띄운 화면 주소를 알려줘. 내가 스크린샷을 찍어 1:1 채널에 올린다.
완료 기준: <봇이 채움, 3~5개>
[마무리 블록]
```

### 3.2 UI/UX B · 하지민 (S4–S7·슬라이드 디자인, `frontend/`, `pitch/`)

```text
[시작 블록] (이슈 #<N>, slug <slug>)
할 일: <예: S4 전략 탭 4개와 카드(순위, 목표 라벨, 기준 A 대비 % 3개 + P10–P90 막대, 장점 3·단점, unique_feature, 카드 5항목 접기)를 frontend/src/screens/Strategies.tsx에 구현해.>
제약:
- 데이터는 SOT `/strategies/compare` 예시 JSON(fixtures)만 사용. 필드명을 새로 만들지 마.
- 모든 %에 툴팁 "기준 A 대비 상대 지수, 보장 아님". 미래 패널 제목은 "가능한 범위(시나리오)".
- 단일 '최적' 배지 금지. 카드 5항목(why, evidence, benefits, info_gaps, local_review_risks) 생략 금지.
완료 기준: <봇이 채움>
[마무리 블록]
```

### 3.3 복셀 시뮬 · 강다은 (확인 필요) (`sim/`)

```text
[시작 블록] (이슈 #<N>, slug <slug>)
할 일: <예: sim/index.html 하나로 three.js(CDN import map) 복셀 필지를 그려. 입력은 sim/fixtures/sim_scene.example.json (TEAM_SPEC 7.5 스키마). 전략 A vs B 분할 화면, 프레임 재생 슬라이더.>
제약:
- 빌드 없이 브라우저로 열려야 함. 큰 텍스처·영상 파일은 커밋하지 마(10MB 이상 금지).
- 데이터에 없는 사실을 연출할 때는 화면 구석에 "illustrative" 표시.
- 녹화용으로 1920×1080 고정 모드(URL ?record=1)를 넣어.
완료 기준: <봇이 채움>
[마무리 블록]
```

### 3.4 백엔드·인프라 · Hylē (`model_api/`, `data_pipeline/`, `rag/`, `infra/`)

```text
[시작 블록] (이슈 #<N>, slug <slug>)
할 일: <예: model_api/에 FastAPI 앱, SOT 6절 pydantic 모델, GET /health, /strategies/compare를 fixtures로 응답. 계약 테스트 tests/test_contract.py.>
제약: AGENTS.md 백엔드 규칙(숫자는 tool 응답만, MC 시드 고정, CVaR 하위 10 %, RAG 결과 없으면 insufficient_evidence).
완료 기준: <…>
[마무리 블록]
```

---

## 4. MATLAB 역할 (김윤성 · 김우찬): git 없음

MATLAB 담당은 **git과 PR을 쓰지 않는다.** 노트북의 Codex/agy로 MATLAB 코드를 만든다. 그 코드를 VPS의 **브라우저 MATLAB**에 붙여 실행하고, 결과 파일을 정해진 곳에 저장한다. 커밋은 Hylē(또는 오케스트레이터)가 한다.

- 스크립트 저장 위치: `/srv/hackathon/projects/2026NASA/matlab/<climate|vegetation|scenario>/<이름>.m`
- 산출 위치: `/srv/hackathon/data/processed/v1/matlab/`. SOT 4절의 고정 파일 5종(`field_dekad.parquet`, `field_season.parquet`, `climate_annual.parquet`, `scenario_climate.parquet`, `calibration_params.csv`)과 각 `{file}.manifest.json`만 둔다. 스키마를 바꾸면 v2 폴더를 쓰고, v1을 덮어쓰지 않는다.
- 브라우저 MATLAB 안에서 보이는 경로가 위와 다르면 Hylē에게 묻는다(컨테이너 마운트 경로, **확인 필요**).

### MATLAB 작업 프롬프트 틀 (Codex/agy에 붙임)

```text
너는 MATLAB R2026b 코드를 쓰는 도우미야. git은 쓰지 않는다. 결과는 내가 브라우저 MATLAB에 붙여 실행한다.
먼저 저장소 문서를 읽어: https://github.com/cloudsnuchoi/2026NASA 의 AGENTS.md(MATLAB 절), docs/SOT.md 4절, docs/TEAM_SPEC.md 7.4. (로컬에 ~/2026NASA가 있으면 그 파일을 읽어.) 이슈는 `gh issue view <N> -R cloudsnuchoi/2026NASA` 또는 웹으로 읽어.
할 일(이슈 #<N>): <예: NASA POWER daily point API로 1991–2025 T2M, T2M_MAX, T2M_MIN, PRECTOTCORR, ALLSKY_SFC_SW_DWN을 받아 climate_annual 스키마로 만들기>
[MATLAB 마무리 블록]
- 스크립트 맨 위에 DATA_ROOT = getenv("FS_DATA_ROOT"); if isempty(DATA_ROOT), DATA_ROOT = "/srv/hackathon/data"; end 를 둬.
- 출력은 fullfile(DATA_ROOT,"processed","v1","matlab",<SOT 파일명>)에 parquetwrite(CSV면 UTF-8·쉼표·헤더 1줄). 결측은 missing/NaN으로 두고 0으로 채우지 마. 컬럼 이름은 SOT와 정확히 같게 snake_case로 써.
- 같은 폴더에 <파일>.manifest.json을 jsonencode로 써. 필드: rows, sha256(가능하면, 안 되면 "미계산"), schema_version, matlab_version(version), script, git_commit("n/a"), created_kst, sources(URL 목록).
- 이미 같은 파일이 있으면 덮어쓰지 말고 멈추고 경고를 출력해.
- 끝에서 height(T), 컬럼 목록, 처음 5행을 출력하고 확인용 그림 1장(<이름>.png)을 같은 폴더에 저장해.
- 내가 저장할 스크립트 경로 `/srv/hackathon/projects/2026NASA/matlab/<폴더>/<이름>.m`을 알려주고, 전체 코드를 한 블록으로 줘.
```

**보고(1:1 채널):** 스크립트 경로, 산출 파일 경로, `rows`, 그림 캡처, 막힌 점.

---

## 5. 리뷰·수정 요청 프롬프트 (봇이 `!review` 결과로 줄 때)

```text
[시작 블록 생략 — 지금 브랜치 feat/<N>-<slug>에서 계속]
PR #<P> 리뷰에서 아래를 고쳐 줘: <봇이 채운 목록>
고친 뒤 [마무리 블록]을 다시 실행해. 새 PR은 만들지 말고 같은 브랜치에 푸시만 해.
```

## 6. Hylē용: MATLAB 산출 커밋 프롬프트 (VPS에서)

```text
/srv/hackathon/projects/2026NASA에서 matlab/ 아래 새 .m 파일만 확인해(데이터 파일은 커밋 금지).
`git checkout -b feat/<N>-matlab-<slug>`를 실행하고, `git add matlab/`과 `git commit -m "feat(matlab): <요약>"`을 실행해.
`git push -u origin HEAD`를 실행한 뒤, `gh pr create`로 PR을 만들어. 본문에는 "Closes #<N>"과 산출 경로, manifest 내용을 넣어. 마지막에 `PR: <url>`을 출력해.
```
