# woochan — FieldShift_V8_batch.m 변경 내역

## 2026-11-15 ~20:00 KST — MATLAB-fix 레인 (`fix/matlab-scripts`)

### 실패 (19:23–19:30 KST 실행, `outputs/woochan/v8_failures_20fields.csv`)

- 1번 필지 `171825001292309`: `USGS elevation unavailable … epqs.nationalmap.gov … timed out after 8.000 seconds`.
  브라우저 MATLAB 세션에서 USGS EPQS 응답이 8 s 안에 오지 않음.
- 2–20번 필지 19개: `Open-Meteo climate data unavailable: Open-Meteo daily series is incomplete or invalid`.
  원인: Open-Meteo Climate API의 `MRI_AGCM3_2_S` 모델은 `et0_fao_evapotranspiration`을 **제공하지 않는다**.
  응답의 `daily_units.et0_fao_evapotranspiration = "undefined"`이고 5113일 전부 `null`
  (날짜 5113/5113, 기온·강수는 결측 0). V8 검증기가 `isfinite(etVec)` 전체를 요구해서 모든 필지가 탈락했다.

### 수정

- 서버 사전 수집: `data_pipeline/v8_prefetch.py`가 20필지 × (USGS EPQS 꼭짓점 4개, NASA POWER 2016–2025 일별,
  NWS points+forecast, Open-Meteo climate)를 V8과 같은 URL로 받아
  `inputs/v8_api_cache/<field_id>/{epqs_1..4,power,nws_points,nws_forecast,openmeteo}.json` + `manifest.json`에 저장.
- `cached_webread`: 캐시 JSON(`jsondecode(fileread(...))`)을 먼저 읽고, 파일이 없을 때만 `webread`
  (타임아웃 60 s, 재시도 2회).
- Open-Meteo 검증기: 날짜 완전성, 기온·강수 결측 없음은 그대로 요구. ET0가 **전부** 결측(모델 미제공)이면
  정보 공백으로 처리: 미래 증발량은 V8 자체의 POWER 추세 항만 사용(0.6·모델 + 0.4·추세 → 추세 단독),
  `proj_et0ModelAvailable = 0` 열과 `future_source`에 `INFORMATION GAP` 문구를 남긴다.
  ET0가 일부만 결측이면 여전히 실패 처리. 가짜 ET0 값은 만들지 않는다.
- 덮어쓰기 거부 대신 기존 `v8_cards_20fields.csv`, `v8_failures_20fields.csv`를
  `outputs/woochan/old/<yyyymmdd_HHMMSS>/`로 옮긴 뒤 새로 쓴다.
- 그 밖의 V8 계산식·계수·반올림은 바꾸지 않았다.

### 팀원이 할 일

MATLAB에서 `matlab/FieldShift_V8_batch.m`을 열고 **Run**. 끝.
