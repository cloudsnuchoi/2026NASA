# model_api · Field Shift 모델 API

FastAPI 서비스. 계약은 [docs/SOT.md](../docs/SOT.md) 6절이고, 응답에는 SOT 예시 키가 모두 들어간다(키를 더하는 것만 함). DB `fieldshift`는 **읽기 전용**으로 연다. 세션을 `READ ONLY`로 걸어 두므로 API가 데이터 테이블에 쓰지 않는다.

## 실행

```bash
python3 -m venv .venv && .venv/bin/pip install -r model_api/requirements.txt
export PGHOST=127.0.0.1 PGPORT=5433 PGUSER=hk PGDATABASE=fieldshift   # 비밀번호는 ~/.pgpass 또는 PGPASSWORD
.venv/bin/uvicorn model_api.main:app --host 127.0.0.1 --port 8000
# docs: http://127.0.0.1:8000/docs
```

테스트와 린트:

```bash
.venv/bin/ruff check .
.venv/bin/python -m pytest -q model_api/tests      # 단위 테스트는 DB 없이 돈다. DB 통합 테스트는 DB에 닿지 않으면 skip
.venv/bin/python -m model_api.make_fixtures        # model_api/fixtures/*.json 을 실데이터로 다시 만든다
```

### 환경 변수

| 변수 | 기본값 | 용도 |
| --- | --- | --- |
| `PGHOST` `PGPORT` `PGUSER` `PGDATABASE` `PGPASSWORD` | `127.0.0.1` `5433` `hk` `fieldshift` (비밀번호는 `~/.pgpass`) | DB (읽기 전용) |
| `FS_MATLAB_DIR` | `/srv/hackathon/data/processed/v1/matlab` | MATLAB CSV 입력(`field_dekad.csv`, `field_season.csv`, `climate_annual.csv`, `scenario_climate.csv`, `calibration_params.csv`, `coefficients.csv`). 파일이 없으면 그 항목은 건너뛰고 `notes`에 적는다. `calibration_params.csv`와 `coefficients.csv`의 `param,value`는 같은 이름의 기본 계수를 덮어쓴다 |
| `LLM_API_KEY` | 없음 | `/explain`. 없으면 503 `llm_unavailable`. 키는 env에서만 읽고 로그로 남기지 않는다 |
| `LLM_BASE_URL` | `https://api.deepseek.com` | OpenAI 호환 엔드포인트 |
| `LLM_MODEL` | `deepseek-flash` | 모델 id |

## 엔드포인트

| 경로 | 설명 |
| --- | --- |
| `GET /health` | `{status, time, db}` |
| `GET /fields` | Story County 데모 필지 12개(OpenET·HLS 시계열이 있는 CSB 필지). `?all=true&limit=&offset=`이면 6,027개 전체 |
| `GET /field/{id}/profile` | SOT 프로필과 08:20 확장 필드(강수·ET·ET0·NDVI·CDL 이력·SSURGO·비전·`hero_state`) |
| `GET /field/{id}/bare-periods` | HLS NDVI가 임계값(기본 0.35)보다 낮은 기간과 CDL 라벨 |
| `GET /field/{id}/vulnerable-seasons` | POWER 계절 아노말리(최근 연도와 1995–2024 비교), 위험 플래그, SMAP 맥락 칸 아노말리 |
| `GET /field/{id}/climate/history?years=5` | 연도별 강수·기온(POWER), ET(OpenET), NDVI 피크(HLS), CDL |
| `GET /field/{id}/climate/outlook` | GEOS-S2S 다음 시즌 멤버 분포, NEX-GDDP-CMIP6 2030년대 모델 범위 |
| `GET /county/{fips}` · `GET /county/{fips}/vulnerable-seasons` | 1층 카운티 요약(콘벨트 12개 주 1,122개 카운티) |
| `GET /locate?lat=&lon=` | 핀 → CSB 필지. Story 밖이지만 1층 카운티 안이면 `service_tier: "county"` |
| `POST /simulate` | MC 물수지 엔진 전체 출력(지표 분포, 7축, 합성 지수, 시나리오, `assumptions`) |
| `POST /strategies/compare` | SOT 비교 응답. `/simulate`와 같은 엔진·캐시를 쓴다 |
| `POST /rotations/candidates` | 선택 옵션의 부분집합 2ⁿ개(TEAM_SPEC 2.3) |
| `GET /validation/backtest?field_id=&year=` | 그해 실제 POWER 날씨로 돌린 결정론적 1년 물수지(A–D)와 CDL·NASS 카운티 수량(bu/ac) |
| `GET /evidence/search?q=&strategy=` | `evidence_chunk` 전문 검색. 비어 있으면 `insufficient_evidence: true` |
| `GET /glossary` | S6 용어 카드 |
| `POST /explain` | DeepSeek tool-calling 설명(아래 참고) |

오류는 SOT 형식을 따른다: `{"error": {"code": "not_found", "message": "Unknown field_id"}}`. 입력 오류는 `invalid_request`(422), DB 장애는 `db_unavailable`(503)이다.

### `/simulate` 요청

```json
{ "field_id": "191825003869023", "n": 500, "seed": 42,
  "strategies": ["A","B","C","D"],
  "priorities": {"water": 0.3, "soil": 0.4, "stability": 0.2, "income": 0.1},
  "constraints": {"water_limited": false, "water_cap_mm": null}, "scenarios": true }
```

필지 대신 `county_fips`(1층 카운티)를 줄 수 있다. 전략은 `strategies`(A–D)나 `candidate_ids`(`C-S`, `C-S+cover_rye`, `C-S-W`, `C-S-W+cover_rye`, `C-S-Alf`, …)로 고른다. 기준 A(`C-S`)는 항상 들어간다. `%`가 A 대비 값이기 때문이다.

## 엔진 (L3)

- **ET0**: POWER 일 자료(T2M, T2M_MIN, T2M_MAX, RH2M, WS2M, ALLSKY_SFC_SW_DWN)로 FAO-56 Penman–Monteith를 계산한다. 일사가 빠진 날은 Hargreaves로 채운다.
- **물수지**: 토양 프로필 1.5 m를 버킷 하나로 보고 위에서부터 고갈된다고 본다. 작물이 쓸 수 있는 물은 TAW = 1000·AWC(SSURGO)·Zr(작물)이다. Ks는 FAO-56 식 84, ETa는 Ks·Kc·ET0로 구한다. 유출은 SCS-CN(TR-55, HSG B)으로 계산하고, 포장용수량을 넘는 물은 배수로 뺀다.
- **작물 달력**: 아이오와 기본안을 쓴다. 옥수수 5/1–9/28, 대두 5/10–9/22, 겨울밀 10/2–7/15, 호밀 피복은 수확 7일 뒤 파종하고 다음 작물 10일 전에 종료한다. 알팔파는 4/15에 파종하고 둘째 해 10/15에 종료한다. Kc는 FAO-56 Table 12 값이다.
- **MC**: 표본마다 스핀업 1년과 채점 4년을 1995–2025 POWER 연도에서 복원 추출한다. 전략끼리는 같은 난수를 쓴다(common random numbers). 윤작 위상은 전략마다 무작위다. 기본 N=500이고 시드를 고정하며, 시드는 `run_id`에 들어간다(`mc-<hash>-n500-s42`).
- **시나리오**: GEOS-S2S는 멤버별 MAM·6–7월 평균을 POWER 1995–2024 같은 달 평년과 비교해 강수 비율과 기온 이동을 만든다(힌드캐스트 편향 보정 없음, 응답 `notes`에 명시). NEX-GDDP-CMIP6는 모델별 2031–2040과 1985–2014를 비교하는 delta method로 적용한다. 결과는 `scenario_results`에 분포로만 담는다.
- **CVaR**: 표본 중 가장 나쁜 10 %의 평균이다. 지수에서는 하위 꼬리, 물 부족에서는 상위 꼬리다. 응답의 `cvar_definition`에도 적는다.
- **7축(0–1, 높을수록 좋음)**
  - `water_use_index` = 1 − ETa/P
  - `erosion_index` = 1 − 0.6·(겨울 맨땅일/181)·(K/0.28) − 0.4·(유출/(0.1·P))
  - `organic_matter_index` = 0.5·규칙 + 0.5·(생피복일/365)
  - `n_cycle_index` = 0.5·규칙 + 0.5·(1 − 비생육기 배수/250 mm)
  - `pest_break`, `forage`, `market`은 규칙 점수만 쓴다. 팀 기본값이며 `config.RULE_PRIORS`에 있고 `prior_<axis>_<A..D>`로 덮어쓸 수 있다.
- **합성 지수와 순위**: 슬라이더 가중으로 합성 지수를 만든다. 물 = water_use, 토양 = 침식·유기물·N 평균, 안정 = 0.7·(1 − 부족/ETc) + 0.3·병해충 차단, 소득 = 0.8·시장 + 0.2·사료. `rank`는 화면 정렬 순서일 뿐 단일 최적해가 아니다.
- **`display`**: A 대비 상대 변화를 표본마다 짝지어 계산한다. `vegetation_pct`는 Ks로 가중한 생피복일, `water_use_pct`는 연 ETa다. 가격 자료가 없어서 `revenue_pct`는 `null`이다.
- 실측·보정 값이 없어 기본값을 쓴 항목은 응답 `assumptions[]`에 이름·값·단위·출처와 함께 모두 적는다. kg/ha, t/ha 수량은 만들지 않는다. 수량은 NASS 카운티 bu/ac만 맥락으로 보여 준다.

## `/explain` (L4)

OpenAI 호환 클라이언트를 쓴다(`max_retries=2`, 429·5xx 재시도). `extra_body={"thinking":{"type":"disabled"}}`로 thinking을 끈다. 도구는 `get_profile`, `compare_strategies`, `get_climate_history`, `get_outlook`, `get_vulnerable_seasons`, `search_evidence`다. tool call이 오면 assistant 메시지에 `reasoning_content`가 있을 경우 함께 되돌려 준다. 답변 속 숫자는 모두 도구 응답 JSON과 대조해 `tool_calls[].json_paths_used`에 경로로 적고, 대조되지 않은 숫자는 `unverified_numbers`에 넣는다. 인용(`citations`)은 `search_evidence` 결과에서만 가져온다. 결과가 없으면 `insufficient_evidence: true`다.

## 성능 (2026-11-15, VPS)

`/simulate` N=500, A–D 4개 × 시나리오 4개(과거, S2S, SSP2-4.5, SSP5-8.5): 첫 호출은 약 0.5 s, 같은 위치·시드로 다시 부르면 캐시에서 약 30 ms에 돌아온다. 슬라이더를 바꿔도 재가중만 한다.

## 데이터 공백 (2026-11-15 기준 DB)

`climate_daily`, `climate_annual`, `field_season`, `field_dekad`, `scenario_climate`, `calibration_param`, `evidence_chunk`, `vision_result`, `county_imerg_daily`가 비어 있다. 그래서 필지 기후는 카운티 POWER 지점을 쓰고, 근거 검색은 `insufficient_evidence`를 돌려준다. 비전 값은 `null`이고 `info_gaps`에 이유를 적는다. 테이블이 채워지면 코드를 바꾸지 않아도 반영된다(evidence·vision·calibration).
