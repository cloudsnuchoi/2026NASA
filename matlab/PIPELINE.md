# L2 오프라인 실행

입력 생성: `python3 data_pipeline/matlab_export.py`. 기본 DB 연결은 run script와 동일한 환경변수이며 비밀번호는 환경 또는 `.pgpass`에서 런타임에 읽는다. 데이터는 Git에 포함하지 않는다. 기존 입력·출력 덮어쓰기는 금지한다.

MATLAB 컨테이너에 `/srv/hackathon/data`를 `/data`로 읽기/쓰기 마운트한 뒤:

```matlab
run('matlab/FieldShift_V8_batch.m')
addpath('matlab'); ndvi_baresoil; slide_figures;
```

`FieldShift_V8_batch.m`은 원본 계산의 정상 경로를 유지하되 UI를 제거하고 API 실패·불완전 입력은 필지별 실패 CSV로 기록한다. 네 윤작별 숫자를 모두 펼친 CSV 열 접두사는 `geo_`, `dem_`, `env_`, `proj_`, `card_`, `allocation_`이다. `card_ETm_mm`은 연간 물 요구량으로 엔진의 부족량이 아니다. 미래 점수·경제·지수는 검증되지 않은 프로토타입 값이며 제품의 미래 분포로 제공하지 않는다. 필지 실패가 있으면 성공 필지만 기록한 뒤 MATLAB 배치 종료를 실패로 표시한다.

`ndvi_baresoil.m`은 QA 통과 관측의 제한된 간격만 보간하고 Savitzky–Golay 평활한다. 0.3 임계값과 윈도는 현장 검증 전 잠정 설정이다. 결측은 0으로 채우지 않는다. HLS 관측 기간 밖인 2012 결과를 만들지 않는다. 부분 관측 일수를 연간 전체 일수로 주장하지 않는다.

`slide_figures.m`은 비교 CSV의 composite_index P10–P90와 2012 모델 부족량을 세 필지에 대해 두 PNG로 만든다. 수익 결측을 임의로 대체하지 않는다. 두 함수의 TODO에서 발표 필지·평활 설정을 조정한다.

검증: `python3 data_pipeline/matlab_validate.py`; 반복: `bash infra/status/run_validate.sh` (2026-11-15 20:30 KST 종료). 결과는 `docs/MATLAB-VALIDATION.md`. 기본 보고서는 주기마다 갱신된다. 허용오차와 동일 기간/전략 매핑을 승인받기 전에는 모델 간 비교를 정확도 검증으로 주장하지 않는다.

호스트에는 MATLAB 실행 파일이 없어 `.m` 수치 실행과 PNG 생성은 확인하지 못했다. Python 단위 테스트·실제 API/DB 추출·집계 교차 확인·Ruff·셸 구문 검사를 수행했다. 출처가 확인되지 않은 V8 계수는 `coefficients_proposed.csv` 헤더만 남기고 보류했다.
