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
