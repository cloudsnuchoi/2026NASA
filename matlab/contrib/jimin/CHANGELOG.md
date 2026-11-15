# 하지민 MATLAB 변경 내역

## 2026-11-15 · MAT2 추가 분석

- `jimin_growing_season.m`: 실제 HLS의 QA·최대 20일 보간·구간별 명시적 11점 2차 SG 최소제곱, 필지·연도별 지배 피크 전환 스크리닝. 긴 결측을 건너뛴 전환은 만들지 않습니다.
- `jimin_ndvi_anomaly.m`: 확보 연도 필지 평균 대비 차이 CSV·`ndvi_anomaly.png`. 제목에 `2012 not observable with HLS`와 관측 지원 편향을 표시합니다.
- `jimin_bare_vs_rye.m`: 지원된 저NDVI 일수와 두 작물 달력 가정 시나리오. 원래 윤작·엔진 source/run_id·잔재 가정을 보존하며 연도별 작물을 추정하지 않습니다.
- 출력 이름은 `growing_season_20fields.csv`, `ndvi_anomaly.png`, `bare_vs_strategyB.csv`. 보조 일별·수치·가정 CSV도 남깁니다. 재실행 시 해당 출력만 `old/<시각>/`으로 이동합니다.
- ID·혼합 가정 value는 문자열, NDVI·지원 일별 값·연도는 숫자로 강제해서 전체 결측도 NaN으로 보존합니다. 후속 스크립트는 일별 파일이 없으면 자동 생성합니다.
- Python 스모크는 별도 `outputs/jimin/python_smoke/`에 실제 입력의 수치 CSV만 저장합니다. 시각화 의존성 추가 없음.
- 검증: 실제 60개 필지·연도, 120개 달력 시나리오 통과. 독립 SG 식은 SciPy와 절대오차 1e-12 이내. MATLAB 런타임과 PNG 생성은 호스트 실행 파일 부재로 미확인; 브라우저에서 Run 필요.
- 팀원 수정 사본·기존 원본 스크립트는 수정하지 않았습니다. 실행법: `matlab/guides/jimin-extra.md`.
