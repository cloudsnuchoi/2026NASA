# MATLAB 검증

2026-11-15T19:03:37.846699+09:00

관측 검증과 모델 간 비교를 구분한다. 누락·기간 불일치·API 실패는 not validated.

대상 20/20필지; API 실패 0건.

## V8 물 부족량

V8 행 0건. not validated — V8 ETm_mm(연간 작물 물 요구량)은 engine season_water_deficit_mm(2012 계절 부족량)와 다르며 윤작도 A–D와 일대일 대응하지 않는다. 공통 기후 기간·부족량 정의·승인된 전략 매핑이 필요하다.

## NDVI 맨땅 일수

not validated — outputs/jimin/baresoil_days_20fields.csv 없음.

HLS 관측 기간과 2012가 겹치지 않으면 2012 비교 불가. 전체 연간 bare_days를 겨울 181일 지표와 비교하지 않는다.

## 2012 카운티 가뭄

비교 20/48건; MAE 0.000; 평균 차이 0.000; 제외 0건. 일치 판정 아님(허용 오차 미승인).

위 비교는 같은 POWER 자료의 월 강수 집계 교차 확인이며 독립 관측 검증이 아니다. 가뭄 z-score와 필지 물 부족량(mm)은 동등하지 않다.

## 정보 공백

- MATLAB 실행·V8 출처 검증·NDVI 현장 임계값 보정은 별도 확인 필요.
- coefficients.csv는 변경하지 않는다. 미확인 계수를 운영 보정값으로 승격하지 않는다.
- coefficients_proposed.csv는 헤더만 생성: V8 Kc 1.08/0.86/0.75와 경제·회전 보너스의 문헌 표·단계·가중 근거 미확인으로 제안 행 보류.

<!-- PRE-RUN-CHECK -->
## V8 pre-run check (MATLAB-fix 레인, 2026-11-15 19:55 KST)

`python data_pipeline/v8_precheck.py --all`: Python으로 다시 구현한 V8 경로(USGS→POWER→NWS→Open-Meteo→카드 4개, allocation 제외)를 네트워크 없이 `inputs/v8_api_cache`로 돌렸다.

- 19:23 KST 실행 실패 원인: (1) 1번 필지 USGS EPQS 8 s 타임아웃 (2) 19필지에서 Open-Meteo `MRI_AGCM3_2_S` 응답의 `et0_fao_evapotranspiration`가 5113일 전부 `null`(`daily_units` = `"undefined"`, 이 모델은 ET0를 제공하지 않음). 날짜 5113/5113, 기온·강수 결측은 0.
- 수정한 검증기: 날짜·기온·강수는 전부 있어야 하고, ET0는 전부 없을 때만 정보 공백(`proj_et0ModelAvailable = 0`)으로 받는다. 이때 미래 증발량은 POWER 추세 항만 쓴다. ET0가 일부만 결측이면 계속 실패 처리.
- 결과: **16/20 필지 PASS** (모두 `et0ModelAvailable = False`). 1번 필지 카드: ETm 483.0 / 450.8 / 450.8 / 572.4 mm, 부족률 0.0 %, 유한값.
- 4필지(311825002820374, 311825008109480, 391825000729943, 391825009407249)는 Open-Meteo 429(시간당 요청 한도) 때문에 `openmeteo.json`이 아직 없다. 재시도 중이며, 캐시가 없으면 MATLAB이 `webread`(60 s, 재시도 2회)로 직접 받는다.
- 스크립트 4개 정적 검사 `data_pipeline/tests/test_matlab_static.py`: 20/20 통과. Octave가 없어 MATLAB 파서로는 확인하지 못했다.
