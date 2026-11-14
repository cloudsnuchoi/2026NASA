# AGENTS.md · Codex CLI / agy CLI 규칙

이 저장소에서 도는 코딩 에이전트(Codex CLI, agy CLI, 그 밖의 코딩 어시스턴트)는 사람 기여자와 같은 계약을 따른다. 한국어로 설명하고, 식별자·경로·커밋은 영어를 쓴다.

## 시작하기 전에

1. **먼저 `docs/`를 읽는다.** 필수: [docs/PRD.md](docs/PRD.md), [docs/SOT.md](docs/SOT.md), [docs/CHECKLIST.md](docs/CHECKLIST.md), [docs/DECISIONS.md](docs/DECISIONS.md), [CONTRIBUTING.md](CONTRIBUTING.md).
2. 맡은 **GitHub 이슈 범위 안에서만** 파일을 바꾼다. 이슈에 없는 리팩터, 의존성 추가, 스키마·API 변경은 하지 않는다.
3. 스키마나 API를 바꿔야 하면 구현 전에 이슈로 제안하고, [docs/SOT.md](docs/SOT.md)를 같은 PR에서 고친다. 예시 JSON과 다른 필드명을 만들지 않는다.
4. 없는 데이터셋, 해상도, 카운티 이름, 라이선스 문장, DOI, 숫자를 **지어내지 않는다.** 모르면 `미확인` 또는 정보 공백으로 남긴다.

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

- 라이브 엔진은 규칙·지수 스코어링 + 몬테카를로 + CVaR 이다. RL·미세조정을 추가하지 않는다.
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
- 리뷰어 1명의 승인 후 squash merge (CONTRIBUTING).

## 폴더 소유 (권고)

에이전트는 이슈가 가리키는 폴더 위주로 수정하고, 계약 파일(`docs/SOT.md`, API 스키마)은 협의된 경우에만 고친다.

| 폴더 | 주 담당 |
| --- | --- |
| `data_pipeline/`, `notebooks/` | 강다은, 하지민 |
| `model_api/` | 강다은, Hylē |
| `rag/` | 김우찬, Hylē |
| `frontend/` | 고지은, 하지민 |
| `matlab/` | 하지민 |
| `infra/` | Hylē |
| `docs/` | 김우찬, Hylē |
