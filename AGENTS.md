# AGENTS.md · Codex CLI / agy CLI 규칙

이 저장소에서 도는 코딩 에이전트(Codex CLI, agy CLI, 그 밖의 코딩 어시스턴트)는 사람 기여자와 같은 계약을 따른다. 한국어로 설명하고, 식별자·경로·커밋은 영어를 쓴다.

## 시작하기 전에

1. **먼저 `docs/`를 읽는다.** 필수: [docs/TEAM_SPEC.md](docs/TEAM_SPEC.md), [docs/PRD.md](docs/PRD.md), [docs/SOT.md](docs/SOT.md), [docs/CHECKLIST.md](docs/CHECKLIST.md), [docs/DECISIONS.md](docs/DECISIONS.md), [CONTRIBUTING.md](CONTRIBUTING.md).
2. 맡은 **GitHub 이슈 범위 안에서만** 파일을 바꾼다. 이슈에 없는 리팩터, 의존성 추가, 스키마·API 변경은 하지 않는다.
3. 스키마나 API를 바꿔야 하면 구현 전에 이슈로 제안하고, [docs/SOT.md](docs/SOT.md)를 같은 PR에서 고친다. 예시 JSON과 다른 필드명을 만들지 않는다.
4. 없는 데이터셋, 해상도, 카운티 이름, 라이선스 문장, DOI, 숫자를 **지어내지 않는다.** 모르면 `미확인` 또는 정보 공백으로 남긴다.

## 상태 댓글 (현황 대시보드)

작업을 **시작·막힘·완료**할 때, 그리고 **최소 30분마다** 맡은 이슈에 상태 댓글을 남긴다. 현황판은 이 댓글만 본다. 형식과 명령은 [docs/PROMPTS.md](docs/PROMPTS.md) 0.1절이다. 첫 줄은 `STATUS: 🟢 진행 중` 또는 `🔴 막힘` / `🟡 리뷰 대기` / `✅ 완료`이고, 이어서 `작업:`, `진행률: NN%`, 필요하면 `막힌 점:`, `다음:`을 쓴다. MATLAB 담당도 git 없이 `gh issue comment`로 같은 댓글을 남긴다.

시작 블록과 마무리 블록에도 이 댓글 명령이 들어 있다. 에이전트는 작업을 시작하자마자, PR을 연 뒤, 막히면 즉시 댓글을 작성한다.

## 브랜치와 커밋

- 브랜치: `feat/<issue#>-slug` (예: `feat/12-strategy-cards`). 수정은 `fix/<issue#>-slug`, 문서는 `docs/<issue#>-slug`.
- 커밋 메시지: [Conventional Commits](https://www.conventionalcommits.org/). 예: `feat(model): add CVaR summary to compare response`.
- `main`에 직접 푸시하지 않는다 (문서 동결처럼 저장소 관리자가 명시한 경우만 예외).
- 한 PR은 한 이슈. 작게, 자주.

## 절대 커밋하지 말 것

- `/data/raw`, `/data/processed`, 래스터, shapefile, 대용량 아카이브
- 비밀값: `.env`, Earthdata/QuickStats/OpenET/API 키, 비밀번호, 토큰
- 저작권이 허용되지 않은 문헌 전문 PDF
- NASA 로고, 깃발, 미션 표식

`.gitignore`가 막는 파일을 `git add -f`로 올리지 않는다.

## 코드 규칙

- AI는 4층이다: 비전(Prithvi 추론만) → 예측·시나리오(GEOS-S2S, NEX-GDDP-CMIP6) → 시뮬레이션(MC 물수지 + CVaR + 규칙·지수) → LLM 설명(tool-call) + RAG(인용 전용). RL·미세조정을 추가하지 않는다.
- 미래 기후는 분포로만 반환·표시한다. 결정론적 다년 예보 값을 만들지 않는다.
- MATLAB 코드를 요청 경로의 라이브 런타임에 넣지 않는다. 오프라인 산출은 테이블로 DB에 적재한다.
- LLM은 `model_api` 응답의 숫자만 사용한다. RAG는 인용·DOI 전용이다.
- SMAP·GRACE를 필지 정밀 값처럼 반환하거나 그리지 않는다.
- 전략 비교는 단일 최적해로 줄이지 않는다. 카드 다섯 항목(why, evidence, benefits, info_gaps, local_review_risks)을 생략하지 않는다.
- 단위·CRS·ID는 SOT를 따른다. 저장 EPSG:4326, 분석 EPSG:5070, `field_id` = CSB ID.
- 공개 데모는 로그인 없이 동작해야 한다.

## 테스트

- API를 바꾸면 SOT 예시와 맞는 계약 테스트(스키마 또는 스냅샷)를 넣거나 갱신한다.
- 기존 테스트가 있으면 통과시킨 뒤에 PR을 연다. 테스트가 아직 없으면, 새로 만든 함수의 최소 단위 테스트 또는 `GET /health` 수준의 스모크라도 추가한다.
- 프론트는 데모 시나리오(PRD 8절)를 로컬에서 한 번 클릭해 본다.

## PR

- 템플릿 [`.github/pull_request_template.md`](.github/pull_request_template.md)를 채운다.
- 이슈를 `Closes #N`으로 연결한다.
- SI(코딩 에이전트, LLM)를 썼으면 [docs/si-log.md](docs/si-log.md)에 한 줄을 남긴다.
- 승인 수 0. Hylē(또는 오케스트레이터 리뷰 확인 후 Hylē)가 squash merge. 작성자는 머지하지 않는다. 러너 등록 뒤에는 CI `ci-ok` 통과가 필수다.
- 작업 프롬프트 끝에는 [docs/PROMPTS.md](docs/PROMPTS.md)의 **마무리 블록**을 붙인다(브랜치 → 검사 → 커밋 → 푸시 → `gh pr create` → `PR: <url>` 출력).

## 역할별 규칙

공통: 프롬프트 첫 줄은 “`AGENTS.md`, `docs/SOT.md`, `docs/TEAM_SPEC.md`를 읽고 이슈 #N 범위만 작업해.” 같은 파일을 두 에이전트(Codex, Gemini)가 동시에 고치지 않는다.

### MATLAB (`matlab/`, `area: matlab`)

- 오프라인 전용. 출력은 SOT 4절·TEAM_SPEC 7.4의 **고정 파일 5종**만: `field_dekad.parquet`, `field_season.parquet`, `climate_annual.parquet`, `scenario_climate.parquet`, `calibration_params.csv`.
- Parquet 우선(`parquetwrite`), CSV면 UTF-8·쉼표·헤더 1줄. 결측은 빈 값, 0으로 채우지 않는다.
- 파일마다 `{file}.manifest.json`(`rows`, `sha256`, `schema_version`, `matlab_version`, `script`, `git_commit`, `created_kst`, `sources`).
- 경로는 `FS_DATA_ROOT` 환경 변수. 출력 위치 `/data/processed/v{N}/matlab/`. 같은 버전 덮어쓰기 금지.
- DB에 직접 쓰지 않는다. 적재는 `data_pipeline/load_matlab.py`.
- 컬럼을 추가·변경하려면 SOT PR 먼저.

### 백엔드 (`model_api/`, `data_pipeline/`, `rag/`, `infra/`)

- SOT 6절 계약을 pydantic 모델로 옮기고, `model_api/fixtures/*.json`을 SOT 예시와 같게 유지한다(UI·시뮬이 이걸로 먼저 개발).
- Prithvi 추론은 배치 스크립트(`model_api/vision/` 또는 `notebooks/`)로만, 결과는 `vision_result`. 요청 경로에서 GPU 추론 금지.
- MC는 NumPy. 시드 고정(`run_id`에 기록). CVaR 정의(하위 10 %)를 코드 주석과 응답 `unit`에 남긴다.
- LLM 응답의 숫자는 tool 응답 JSON에 있는 값만. RAG 결과가 없으면 `insufficient_evidence: true`.

### UI/UX (`frontend/`)

- `VITE_API_BASE`가 비면 `frontend/src/fixtures/` 또는 `model_api/fixtures/`를 읽는다.
- `%`에는 항상 “기준 A 대비 상대 지수, 보장 아님” 툴팁과 P10–P90.
- 미래 패널 제목은 “가능한 범위(시나리오)”. 맥락 칸 자료(SMAP, NLDAS, GEOS-S2S, NEX-GDDP)는 해상도 배지.
- 「판단을 대체하지 않음」 문구와 S7 체크리스트를 숨기지 않는다. NASA 로고·미션 표식 금지.

### 복셀 시뮬 (`sim/`, `area: sim`)

- 입력은 `sim_scene.json`(TEAM_SPEC 7.5, SOT `GET /sim/{field_id}/scene`)만. 하드코딩한 가짜 데이터로 사실을 주장하지 않는다(연출 장면은 화면에 “illustrative” 표시).
- 정적 HTML + three.js, 빌드 없이 열리게. 텍스처(NAIP)는 저장소에 대용량으로 커밋하지 않는다.

### 문서·PM (`docs/`)

- 결정은 `docs/DECISIONS.md`에 KST 시각과 함께. 계약 변경은 SOT와 같은 PR.

## 폴더 소유 (2026-11-15 09:30 KST 확정)

에이전트는 이슈가 가리키는 폴더 위주로 수정하고, 계약 파일(`docs/SOT.md`, API 스키마)은 협의된 경우에만 고친다.

| 폴더 | 역할 슬롯 |
| --- | --- |
| `matlab/` | MATLAB A 김윤성(`climate/`), MATLAB B 김우찬(`vegetation/`, `scenario/`) — git 대신 Hylē가 커밋 |
| `data_pipeline/`, `model_api/`, `rag/` | Hylē (풀스택) |
| `frontend/` | UI/UX A 고지은 (S0–S3), UI/UX B 하지민 (S4–S7) |
| `sim/` | 강다은 (확인 필요) |
| `infra/`, `docs/`, `.github/` | Hylē |
| `notebooks/` | 누구나 (EDA) |
