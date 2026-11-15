# MAT2 추가 오프라인 분석 · ART FARM

준비 마감 **2026-11-15 21:00 KST**, 팀원 실행·결과 공유 **22:00 KST**.
실행 방법: [김윤성](guides/yoonsung-extra.md), [하지민](guides/jimin-extra.md).
공개 서비스의 API/DB 계약을 바꾸지 않는 오프라인 검증 자료다.

입력 위치는 호스트 `/srv/hackathon/data/processed/v1/matlab/inputs/`,
MATLAB 컨테이너 `/data/processed/v1/matlab/inputs/`이다. 기존 파일은 수정하지 않는다.
`python -m data_pipeline.matlab_export --extra`는 새 파일을 배타적으로 생성하며,
이미 있으면 전체 추출 전에 중단한다. 다시 만들려면 별도 버전 루트를 사용한다.

| 추가 입력 | 행 | 해석 |
| --- | ---: | --- |
| `county_nldas_2012.csv` | 1488 | 4카운티 × 372개월(1995–2025), 월평균 `rootmoist_kg_m2`; 2012 MJJAS 평균 및 기준 대비 차이 반복 |
| `season_climate_1995_2025.csv` | 124 | 4카운티 × 31년, May–Sep 강수·ET0 합(mm) 및 차이(mm) |
| `engine_p90_years.csv` | 560 | 20필지 × 1998–2025년 전략 A 백테스트. 필지별 선형 P90 이상인 연도 표시(동률 포함) |
| `geos_s2s_next_season.csv` | 160 | 4카운티 × 2기간 × 10멤버 × 2변수 |
| `historical_31yr_distribution.csv` | 496 | 4카운티 × 2기간 × 31년 × 2변수 |
| `engine_strategyB_assumptions.csv` | 220 | 필지별 API 원문 가정·run_id와 달력의 기계 판독용 파생값 |

`mat2_provenance.json`에 각 파일 SHA256, 실제 API 응답·가정·계산법을 기록한다.
엔진 P90은 `/validation/backtest?field_id=...&year=...`의 실제 연도별 값을 사용한다.
3년 준비기간 때문에 1995–1997은 제외한다. `season_water_deficit_mm`는 엔진의
점수 연도 지표이며 May–Sep 한정 기후량과 구분한다. CDL 이전 작물은 엔진에서 추정될 수 있다.
카운티 그림은 그 카운티 필지들의 P90 연도 합집합을 표시한다.

NLDAS·생육기 이상은 **1995–2011 + 2013–2024 (29시즌)** 기준이다.
ET0는 기존 `model_api.hydro.et0_fao56`의 FAO-56 Penman–Monteith 식을
POWER 일자료·카운티 중심 위도·API 고도 가정 300m로 계산한다.
일사가 결측이면 같은 함수의 Hargreaves 분기가 적용된다. 다른 결측은 채우지 않는다.
엔진과 같이 2월 29일을 제외한다. DB의 `et0_mm`은 전체 결측이어서 사용하지 않는다.

GEOS는 **2027 MAM(3–5월), JJ(6–7월)** 자료만 있다. JJ를 JJA 또는 전체 생육기로
표시하지 않는다. 강수는 `mm/day`, 온도는 `degC`; 월평균을 같은 비중으로 평균한다.
과거 분포와 GEOS 이상은 **1995–2025 POWER 31시즌** 기준이다.
이는 서로 다른 제품의 비교이며 GEOS hindcast 기반 편향 보정 결과가 아니다.
POWER 현지 적재 범위는 1995–2025이므로 **1988을 표시하지 않는다**.
HLS에는 2012 관측이 없고, 제공 입력은 2023–2025다.

호밀 달력은 API의 Iowa 기본 가정이다. 숫자로 바꾼 식재·수확 DOY는 365일
엔진 달력 기준이며 포장 관측값이 아니다. `rye_residue_cover_frac`는 **잔사** 피복
비율로, 살아 있는 피복 일수나 관측 맨땅 일수로 환산하지 않는다.
NDVI 기반 맨땅은 잠정 저NDVI 선별 지표이고 눈·잔사·수분 영향이 남는다.

배치: `python -m data_pipeline.matlab_extra_stage`.
`work/<user>/.agent_sha.json`과 다른 팀원 수정본이 있으면 배치 전체를 중단한다.
원래 팀원 스크립트·체크섬 항목은 보존한다. MATLAB 재실행은 기존 결과를
`outputs/<user>/old/<time>/`에 보관한다. 원시 입력·출력·비밀값은 커밋하지 않는다.

## 검증 결과 (MAT2, 2026-11-15)

Python 참조 CSV는 실제 MATLAB 결과와 구분해
`outputs/yoonsung/python_smoke/`, `outputs/jimin/python_smoke/`에 저장했다.
윤성: 카운티 요약 4행(`r=-0.95780013`, n=4), 기후 이상 124행,
분포 요약 16행, 필지·연도 P90 입력 560행 중 60개 표시.
지민: 60개 필지·연도, 120개 corn/soy 달력 가정 비교;
관측 지원 일수 100–243일. 계절 전환이 양쪽 모두 잡힌 55행,
전환 누락 정보 공백 5행. 누락 날짜를 채워 시즌 길이를 만들지 않았다.

검사 명령:

```bash
python -m pytest -q data_pipeline/tests
python -m ruff check .
python -m data_pipeline.matlab_jimin_smoke
python -m data_pipeline.matlab_yoonsung_smoke \
  --input-dir /srv/hackathon/data/processed/v1/matlab/inputs \
  --expected-dir /srv/hackathon/data/processed/v1/matlab/outputs/yoonsung/python_smoke
```

MATLAB 호스트 실행기가 없어 `.m` 실행·PNG 렌더링은 아직 검증하지 않았다.
Python에서는 명시한 SG 최소제곱과 SciPy를 1e-12 이내로 대조했다.
전체 저장소 pytest도 시도했으나 별도 API 테스트의 `fastapi` 미설치(21 errors),
기존 agent-loop 테스트 임시 git index.lock 충돌(1 failure)로 전체 통과는 아니다
(146 passed, 33 skipped). MAT2 및 data_pipeline 테스트는 **86 passed**였으며 저장소 Ruff와 `git diff --check`도 통과했다.
검증 도구 pytest/ruff는 임시 `/tmp/mat2-tools`에만 설치했으며 프로젝트 의존성은 추가하지 않았다.
이 셸에서 같은 도구를 쓰려면 명령 앞에 `PYTHONPATH=/tmp/mat2-tools:.`를 붙인다.

## Git 인계 제한

현재 세션은 원래 worktree의 공통 Git 경로가 읽기 전용으로 제공되어
`git add`의 `index.lock` 생성이 거부됐다. 원래 브랜치 포인터는 변경하지 못했다.
동일한 부모 커밋과 `feat/matlab-extra` 브랜치를 쓰는 별도 로컬 Git 저장소에
커밋하고 `/tmp/mat2-handoff/mat2.bundle`과 `mat2.patch`를 남긴다.
감독자는 쓰기 가능한 Git 환경에서 bundle 브랜치를 가져와 cherry-pick할 수 있다.
푸시·PR·머지는 하지 않았다.
