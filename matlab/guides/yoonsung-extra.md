# 김윤성 추가 MATLAB 3종 · ART FARM

스크립트와 입력 준비 마감은 **21:00 KST**, 팀원 실행·결과 확인은 **22:00 KST**까지입니다. 서버가 배치한 파일을 열고 **EDITOR → Run ▶**만 누르세요. 코드 수정이나 입력값 입력은 필요 없습니다.

윤성님 브라우저 포트는 **8889** (`http://localhost:8889`), 지민님은 **8890**입니다. 기존 SSH 포워딩과 본인 MathWorks 로그인을 사용합니다. 윤성님 Current Folder는 `~/Documents/MATLAB/work/`입니다. 데이터 경로는 MATLAB 컨테이너 기준입니다. **예상 소요:** 스크립트당 1분 이내(총 약 3분). 이 호스트에서는 MATLAB 실행 시간을 아직 측정하지 못했습니다. 직접 데이터 경로로 열 때는 `/data/processed/v1/matlab/work/yoonsung/`에서도 같은 파일을 찾을 수 있습니다.

## 실행 순서

1. Current Folder에서 `yoonsung_nldas_2012.m`을 더블클릭 → **Run ▶**.
2. `yoonsung_season_anomaly.m`을 열고 **Run ▶**.
3. `yoonsung_s2s_box.m`을 열고 **Run ▶**.
4. 각 실행의 명령 창에 `Saved ...`가 나오면 저장 완료입니다. 그림 창은 뜨지 않습니다. 아래 PNG를 파일 목록에서 열어 확인하세요. 오류가 나면 빨간 오류 전문과 스크립트 이름을 기존 1:1 방에 남기세요.

출력 폴더: `/data/processed/v1/matlab/outputs/yoonsung/`. 재실행하면 해당 스크립트의 기존 결과만 `old/<실행시각>/`에 보관하고 새 결과를 만듭니다. 다른 팀원 결과는 건드리지 않습니다.

| 스크립트 | 결과 |
| --- | --- |
| `yoonsung_nldas_2012.m` | `nldas_vs_engine_2012.png`, `nldas_vs_engine_2012.csv` |
| `yoonsung_season_anomaly.m` | `season_anomaly_1995_2025.png`, `season_anomaly_1995_2025.csv` |
| `yoonsung_s2s_box.m` | `s2s_vs_history_box.png`, `s2s_vs_history_box.csv` |

## 읽는 방법

**NLDAS vs 엔진:** 2012 전략 A 필지 물 부족량(mm)을 카운티별 단순 평균한 뒤, NLDAS MJJAS(5–9월) 근권 토양수분 아노말리(kg/m²)와 비교합니다. 월별 행에 반복된 NLDAS 요약은 카운티당 한 번만 사용합니다. CSV에 유효 필지 수·카운티 상관계수·표본 수가 기록됩니다. 카운티 맥락과 모의 필지 부족량의 일관성 확인이며, 현장 수량 검증이나 필지 정밀 관측이 아닙니다.

**계절 아노말리:** 1995–2025 MJJAS 강수·FAO-56 기준증발산 ET0의 아노말리(mm)를 별도 패널로 표시합니다. 평년은 **1995–2011 + 2013–2024**입니다. 빨간 점은 2012, 검은 사각형은 해당 카운티의 **어느 필지든 연간 엔진 물 부족 P90에 해당한 연도**입니다. 각 필지의 1998–2025 연간 scored deficit에 선형 보간 P90 임계값을 적용하며 `>=`로 동률도 포함합니다. P90은 MJJAS-only 부족량이 아니므로 계절 기후와의 동시 발생 맥락으로 읽습니다. 1995–1997년은 3년 spin-up 부족으로 판정 공백입니다. **1988년은 입력 범위 밖이므로 표시·추정하지 않습니다.** 2025년을 임의로 P90으로 정하지 않습니다.

**GEOS 분포:** 한 PNG에 강수(`pr`, mm/day)·기온(`tas`, °C)의 **아노말리 분포**를 담습니다. 카운티·변수·계절마다 GEOS 10멤버와 POWER 과거 31년(1995–2025)을 비교합니다. `MAM`은 2027년 3–5월, **`JJ`는 2027년 6–7월만**이며 JJA가 아닙니다. 상자는 P25–P75, 가운데 선은 P50, 수염은 P10–P90, 점은 모든 표본입니다. 표본이 부족하면 CSV에 information gap을 남깁니다. 입력의 POWER 평년 기준 아노말리이며, GEOS hindcast 편향보정이나 보장된 예보가 아닙니다. 미래는 가능한 범위(시나리오)로 읽습니다.

## 막힐 때

- `K>>`가 보이면 명령 창에서 `dbquit` 후 다시 Run 하세요.
- 입력 파일 없음·스키마/단위 오류는 오류 전문을 1:1 방에 남기세요. 임의 데이터를 만들거나 코드를 고칠 필요는 없습니다.
- `Archive already exists`이면 잠시 뒤 다시 Run 하세요. 이전 결과를 지우지 않습니다.
- 22:00 KST까지 저장된 PNG/CSV와 핵심 수치 한 줄로 완료를 알려 주세요.

## 입력 (읽기 전용)

모두 `/data/processed/v1/matlab/inputs/` 아래에 있습니다.

- 공통 필지 매핑: `fields_20.csv` (`field_id`, `county_fips`는 문자열).
- NLDAS 대조: `engine_2012_deficit.csv`, `county_nldas_2012.csv`.
- 계절 아노말리: `season_climate_1995_2025.csv`, `engine_p90_years.csv` (필지별 연간 엔진 결과 1998–2025).
- GEOS 비교: `geos_s2s_next_season.csv`, `historical_31yr_distribution.csv`.

입력이 없거나 스키마·단위가 다르면 오류로 알리며 가짜 값을 채우지 않습니다. MATLAB은 오프라인 전용이고 DB에 직접 쓰지 않습니다. 이번 CSV는 분석·발표용이며 고정 DB 적재 테이블을 바꾸지 않습니다.

## 에이전트 검증

호스트에서 실제 입력 계산 확인:

```bash
python -m data_pipeline.matlab_yoonsung_smoke --input-dir /srv/hackathon/data/processed/v1/matlab/inputs --expected-dir /srv/hackathon/data/processed/v1/matlab/outputs/yoonsung/python_smoke
```

Python 기준 CSV 3종은 `python_smoke/`에 저장됩니다. MATLAB 실행 후 같은 명령에 `--output-dir /srv/hackathon/data/processed/v1/matlab/outputs/yoonsung`을 추가하면 MATLAB CSV와 수치도 대조합니다. Python 검사는 MATLAB 실행이나 PNG 렌더링을 대신하지 않습니다.
