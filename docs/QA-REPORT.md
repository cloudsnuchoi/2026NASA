# QA 보고서 · model_api E2E + DB 점검 (2026-11-15 KST, QA 레인)

대상: `origin/main` 63c6f62의 `model_api/`. 로컬 `uvicorn`(127.0.0.1:8099)으로 띄우고 DB `fieldshift`(127.0.0.1:5433)는 읽기 전용으로만 열었다. 기준 문서: `model_api/README.md`, `docs/SOT.md` 6절, `/srv/hackathon/logs/sup/prd-gap.md`.

## 실행 방법

```bash
PGHOST=127.0.0.1 PGPORT=5433 PGUSER=hk PGDATABASE=fieldshift \
  .venv/bin/uvicorn model_api.main:app --host 127.0.0.1 --port 8099 &
QA_API_BASE=http://127.0.0.1:8099 .venv/bin/python -m pytest -q model_api/tests/test_e2e_live.py -rxs
PGHOST=127.0.0.1 PGPORT=5433 PGUSER=hk PGDATABASE=fieldshift data_pipeline/qa_checks.sh /tmp/qa_checks.txt
```

- `test_e2e_live.py`: 서버나 DB에 닿지 않으면 모듈 전체를 skip한다(CI 녹색 유지). 아래 표에서 열린 결함은 `xfail(strict=False)`로 표시했다.
- 결과: **122 passed, 5 xfailed**. `/explain`은 키를 넣고 한 번 실행해 200을 받았다(약 4.7 s, 답변 속 숫자 14개가 모두 도구 JSON에 있고 `unverified_numbers: []`, `citations: []`, `insufficient_evidence: true`). 키가 없으면 이 테스트는 skip한다.
- `qa_checks.sh`: **PASS 70 · WARN 17 · FAIL 1**. 세션은 `default_transaction_read_only=on`으로 연다. FAIL이 하나라도 있으면 exit 1.

E2E가 확인한 내용: 데모 필지 12개 × 엔드포인트 10개, 1층 카운티 3개(17113 IL, 31109 NE, 18157 IN)의 `/county`, `/county/../vulnerable-seasons`, `/simulate`, `/locate` 3가지 경우(Story 필지 → `field`, 일리노이 → `county`, 덴버 → `null`), 오류 형식. 단언 항목: 상태 200, SOT 6절 키와 단위, NaN/inf 없음(엄격 JSON 파싱), P10≤P50≤P90, min≤p50≤max, CVaR 꼬리 방향(지수는 CVaR≤P10, 물 부족은 CVaR≥P90), 단일 최적해 키 없음과 면책 문구, 카드 5항목과 pros 3개 비중복, 7축 값이 0–1 안, 기본값을 쓰면 `assumptions[]`(item/value/unit/source)가 있는지, `revenue_pct`가 null이면 가격 관련 `info_gaps`가 있는지.

## 결과 표

심각도: P0 = 데모나 제출을 막음, P1 = 심사위원이 보는 화면에서 틀리거나 오해를 부름, P2 = 정리·문서·데이터 위생.

| ID | 점검 | 결과 | 근거 | 심각도 | 제안 수정 | 담당 레인 |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | 엔진이 "County IMERG rows not loaded"를 **무조건** 붙이는가 | **FAIL (주장 확인)** | `model_api/engine.py:392`는 조건 없는 리터럴이다. 같은 문구가 `services.py:161`(프로필 `info_gaps`)과 `services.py:17`(`"not loaded"` 출처 라벨)에도 하드코딩돼 있다. 반면 DB에는 `county_imerg_daily` 1,122개 카운티 행이 있다(점검 중에도 적재가 진행돼 2.36 M → 2.77 M행, 2019-01-01..2025-09-30). `/county/{fips}`만 `repo.imerg_count`로 확인한다(`services.py:435`) | P1 | 세 군데 모두 `repo.imerg_count(fips) == 0`일 때만 붙인다. 적재 뒤에는 "IMERG loaded (2019–2025) for comparison; water balance uses POWER"로 바꾼다. xfail `test_imerg_gap_note_matches_db` | engine |
| E2 | model_api가 NLDAS를 읽지 않는가 | **확인** | `grep -n nldas model_api/*.py`로 나오는 것은 `services.py:117`의 오류 문구("OpenET / NLDAS-2 not loaded") 하나뿐이다. `county_nldas_monthly`를 읽는 쿼리는 없다. 테이블은 1,122개 카운티 × 372개월이 채워져 있고 단위도 정상이다(D5 참고) | P2 | PRD와 사이트에 "NLDAS-2 적재됨, API 미반영"이라고 적는다. stretch로는 `/vulnerable-seasons`에 `rootmoist` 아노말리 칸을 넣는다 | engine / docs |
| E3 | 2012 백테스트 결과가 A–D 모두 같은가 | **FAIL (주장 확인, 범위는 더 넓음)** | 12개 필지 모두 2012년 `season_water_deficit_mm`가 A=B=C=D(예: 344.0)다. 다른 해도 같다: 필지 …869023에서 2005, 2011, 2013, 2018, 2023년 4전략 값이 같고, 2021년만 6 mm 다르다. 원인: `engine.py:469-476`이 전략마다 그해 현금 작물을 관측 CDL에 맞추므로 모든 전략이 같은 작물이 된다. D는 알팔파 해를 한 번도 채점하지 않는다. 부족량은 주 작물 생육일만 센다(`hydro.py:283`). 스핀업은 1년이고 봄비로 버킷이 다시 차서 피복의 이월 효과가 사라진다. `winter_bare_days`, `offseason_drainage_mm`, `eta_mm`은 실제로 다르다 | P1 | (a) 백테스트 카드는 부족량 대신 실제로 다른 지표(맨땅 일수, 비생육기 배수, 유출)를 보여 주고, "같은 날씨·같은 현금 작물이라 생육기 부족량은 같다"고 적는다. (b) 엔진에서는 2009–2012 4년 창으로 채점하고 전략마다 자기 윤작 위상을 쓴다. xfail `test_backtest_2012_differentiates_strategies` | engine / UI B |
| E4 | 데모 필지끼리 결과가 실제로 다른가 | **FAIL (새 발견)** | `/strategies/compare` 기본 요청에서 12개 중 11개 필지의 A–D 합성 P50이 ±0.001 안에서 같다(A 0.503–0.504, B 0.586, C 0.568, D 0.549). …014952만 다르다(AWC 0.207). 엔진에 들어가는 필지 고유 입력은 AWC와 K뿐이다. 그중 9개 필지는 같은 mukey(2922031)이고, 날씨는 카운티 POWER 지점 하나다. OM과 배수등급은 쓰지 않고 HSG는 B로 고정이다 | P1 | 데모 시나리오는 토양이 다른 필지 2–3개(…014952, …869023, …175247)로 고정한다. 화면에서 "Same county weather; field differences come from SSURGO AWC/K only"를 밝힌다. 엔진에서는 `drainagecl`로 HSG를 고르는 정도가 최소 수정이다 | engine / data / UI A |
| A1 | 모든 엔드포인트 × 데모 12필지 SOT 형식·단위·분위 순서·NaN | PASS | `test_e2e_live.py` 엔드포인트별 테스트 108개 | — | — | QA |
| A2 | 단일 최적해 없음, 카드 5항목, pros 3개 비중복, `rank` 1..n | PASS | `check_no_single_optimum`, `check_strategy_cards`. compare와 simulate 모두 해당 | — | — | QA |
| A3 | CVaR 정의와 꼬리 방향 | PASS | 지수(`p10` 등과 `composite`)는 CVaR≤P10, `scenario_results`의 부족량은 CVaR≥P90. `cvar_definition`에 "worst 10 %"가 있다 | — | — | QA |
| A4 | `/locate`에서 Story 안이지만 CSB 필지가 없는 점(에임스 시내) | FAIL | `service_tier:"county"`, `county_fips:"19169"`인데 `message`가 "Outside the field-level service area (Story County, IA)"다. Story 안에 있는데 Story 밖이라고 말한다(`main.py:145`) | P2 | `county_fips == STORY_FIPS`이면 "No CSB crop field at this point; pick a field polygon"을 쓴다. xfail `test_locate_story_non_field_message` | engine |
| A5 | 1층 카운티 3개 `/county` + `/simulate` | PASS | `tier:"county"`, `field_id:null`, "Tier 1 county run … soil defaults used", `assumptions`에 `awc_cm_cm`. NE 31109 기본 결과: A 0.478, B 0.553, C 0.536, D 0.516 | — | — | QA |
| A6 | `/strategies/compare`가 `county_fips`를 받지 않음 | 확인(설계) | `main.py:208` `CompareRequest.field_id: str` | P2 | 카운티 화면은 `/simulate`만 쓴다고 PRD에 적는다 | docs |
| A7 | `goal_label` 배정 | 의심 | 12개 필지 모두 B(호밀 피복)가 "Income / market fit"이다. 그리디 배정(`engine.py` `_goal_labels`)에서 남은 그룹이 B로 간다. 피복작물 탭에 "소득" 라벨이 붙으면 심사위원이 이상하게 볼 수 있다 | P2 | 라벨에 최소 우위 기준을 두고, 못 넘으면 "Balanced"로 둔다. 또는 UI에서 `goal_label` 옆에 `group_scores`를 같이 보여 준다 | engine / UI B |
| A8 | `/vulnerable-seasons`의 `hazards` 의미 | 의심 | `hazards`는 1995–2024 빈도 플래그(`services.py:269-283`)인데 2025년 아노말리 옆에 나온다. 그래서 여름에 강수 +182.5 mm인데도 "drought"가 붙는다 | P2 | 키 이름을 `climatological_hazards`로 바꾸거나 UI 문구를 "historically frequent hazards"로 한다 | UI B / engine |
| A9 | `display.vegetation_pct` 크기 | 주의 | B의 p50이 약 +158 %다. 이 값은 NDVI가 아니라 Ks로 가중한 생피복일이다 | P2 | 라벨을 "Living-cover days vs A"로 한다(gap 문서 제안과 같음) | UI B |
| A10 | `/explain` 숫자 근거 | PASS | 위 실행 결과. 근거 표가 비어 있어 `citations:[]`, `insufficient_evidence:true`가 정상이다 | — | — | QA |
| A11 | 문서 상태 | FAIL | `model_api/README.md:94`는 `county_imerg_daily`가 비어 있다고 적는데 지금은 채워져 있다. outlook의 `period`는 "2027-JJ"인데 SOT 예시는 "2027-JJA"다 | P2 | README 데이터 공백 절과 SOT 예시를 고친다 | docs |
| D1 | NDVI 범위 | **FAIL** | `field_ndvi_hls` 행 하나가 1을 넘는다: …176345, 2023-11-27, HLSS30, ndvi 2.123, valid_frac 0.0026. API는 0..1과 valid_frac≥0.5로 거른다(`services.py:75`, `:193`) | P2 | 적재 단계에서 `ndvi NOT BETWEEN -1 AND 1`이면 NULL로 둔다. CHECK 제약 추가 | data |
| D2 | `county_weather_daily.et0_mm` | WARN | 100 % NULL이다. ET0는 엔진이 FAO-56으로 계산한다 | P2 | 컬럼을 채우거나 "engine-computed"로 문서화한다 | data |
| D3 | 필지 폴리곤 유효성 | WARN | 6,027개 중 180개가 `ST_IsValid` false(Ring Self-intersection)다. centroid 1개(…869041)가 Story 경계 밖이다. `/locate`는 `ST_Contains … LIMIT 1`을 쓰고 ORDER BY가 없다(`repo.py:138`) | P2 | 적재 때 `ST_MakeValid`를 적용하고 `ORDER BY ST_Area`를 넣는다 | data |
| D4 | SSURGO OM | WARN | mukey 411296(14개 필지)이 OM 59.3 %로 유기질(muck) 토양이다. 프로필에는 그대로 표시된다 | P2 | UI에서 "organic soil" 배지를 단다. 엔진은 OM을 쓰지 않는다 | UI A / data |
| D5 | IMERG·NLDAS 단위와 범위 | PASS(주의) | IMERG 0..162.8 mm/day, null 0 %, 카운티당 일수가 모두 같다. 2020–2024 IMERG/POWER 연합계 비는 평균 1.14(0.77–1.67)이고, Story는 4,461 mm 대 3,511 mm(+27 %)다. NLDAS `rainf` 카운티-연도 합은 156–1,990 mm이고 2015–2024 POWER 대비 0.93이다. `evap` 198–863 mm/yr, 토양수분 층별 최댓값이 층 두께 안에 들고, `potevap` −0.47..548 W/m² | P2 | 단위는 문제없다. 다만 물수지 강수(POWER)가 Story에서 IMERG보다 약 20–27 % 낮으므로 부족량이 높게 나올 수 있다. 이 점을 `assumptions` 또는 `info_gaps`에 적는다 | engine / data |
| D6 | 행 수, 중복 키, FIPS 형식·주 접두어, 고아 FIPS, POWER/SMAP/NASS/CDL/OpenET/NEX/S2S 범위 | PASS | `qa_checks.sh` 출력. POWER 카운티당 11,323일, S2S 10멤버, NEX 2모델 × 2 SSP, CDL 점유율 합 1.000 | — | — | QA |
| D7 | 빈 테이블 | WARN(알려짐) | `climate_daily`, `climate_annual`, `field_season`, `field_dekad`, `scenario_climate`, `calibration_param`, `evidence_chunk`, `vision_result`, `strategy_score`, `backtest_result`, `data_source` | P2 | MATLAB 산출, 근거 표, Prithvi 결과가 오면 채운다. 그 전까지 `data_source`라도 채우면 출처 표기 근거가 된다 | data / MATLAB |

## 요약

- **P0: 0건.** 모든 엔드포인트가 실데이터로 200을 돌려주고 계약 형식을 지킨다.
- **P1: 3건.** E1(IMERG 미적재 문구가 틀림), E3(백테스트에서 전략 간 차이가 없음), E4(데모 필지 12개가 사실상 같은 결과).
- **P2: 13건.** E2, A4, A6–A9, A11, D1–D5, D7.
