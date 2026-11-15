# 김윤성 실행본 변경 내역

## 2026-11-15 · MAT2 추가 분석 3종

- `matlab/yoonsung_nldas_2012.m`: 실제 엔진 전략 A의 2012 필지 물 부족량을 4개 카운티 평균으로 집계하고 NLDAS MJJAS 근권 토양수분 아노말리와 상관 비교. 월별 반복 요약을 카운티당 한 번만 사용. 출력 `nldas_vs_engine_2012.png`, `.csv`.
- `matlab/yoonsung_season_anomaly.m`: 실제 POWER/FAO-56의 1995–2025 MJJAS 강수·ET0 아노말리와 2012 표시. **1998–2025** 연간 엔진 scored deficit의 필지별 P90 연도 합집합을 카운티에 표시. 3년 spin-up이 필요한 1995–1997은 판정 공백, 1988은 입력 범위 밖. 2025를 임의로 P90으로 지정하지 않음. 출력 `season_anomaly_1995_2025.png`, `.csv`.
- `matlab/yoonsung_s2s_box.m`: 실제 GEOS 멤버 10개와 POWER 과거 31년의 강수·기온 아노말리 분포를 한 그림에 비교. MAM과 JJ(6–7월만)를 구분하고 편향보정 미수행을 표시. 출력 `s2s_vs_history_box.png`, `.csv`.
- 공통: Base MATLAB, 대화형 입력 없음, 그림 `Visible='off'`, ID 문자열, 컨테이너 `/data/processed/v1/matlab/` 경로. 기존 해당 결과는 `outputs/yoonsung/old/<시각>/`에 보관. 사용자 수정본·다른 팀원 파일을 덮어쓰지 않음.
- `matlab/guides/yoonsung-extra.md`: 포트 8889, `~/Documents/MATLAB/work/`의 Open → Run 실행 순서와 입력·해석·정보 공백 안내.
- `data_pipeline/matlab_yoonsung_smoke.py`: 실제 입력 독립 수치 확인, 선택적 Python 기준 CSV 3종 저장 및 MATLAB 산출 CSV 대조. Python 기준 CSV는 MATLAB 실행 결과로 주장하지 않음.

검증: 윤성 스크립트 정적 검사 18개 통과, Python 스모크에서 4카운티 상관 r=-0.95780013, 계절 124행, P90 560필지·연도(60개 표시), GEOS/과거 분포 32그룹 확인. 호스트 MATLAB 런타임이 없어 Run·PNG 렌더링 검증은 팀원 세션에서 남음. 실제 관측·재분석/모형 자료의 분석이며 현장 검증이나 보장된 미래 예보가 아님.
