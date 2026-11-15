# 하지민 추가 MATLAB 분석 · ART FARM

스크립트·입력 준비 목표 **21:00 KST**, 실행·결과 확인 **22:00 KST**.
하지민 포트는 **8890** (`http://localhost:8890`), 김윤성 포트는 **8889**입니다.
접속 방법은 [기존 가이드](jimin.md)를 따릅니다. 본인 MathWorks 계정으로 로그인합니다.

**예상 소요: 세 스크립트 전체 약 1–3분**(환경·파일 접근·그림 저장에 따라 달라지는 추정).

## 열기 → Run

1. MATLAB 왼쪽 Current Folder를 `~/Documents/MATLAB/work/`로 엽니다. 아래 세 파일이 같은 폴더에 있어야 합니다.
2. `jimin_growing_season.m`을 더블클릭 → EDITOR의 **Run ▶**.
3. `jimin_ndvi_anomaly.m`을 열고 **Run ▶**.
4. `jimin_bare_vs_rye.m`을 열고 **Run ▶**.
5. 명령 창의 `Saved ...`를 확인하고, 결과 파일과 오류가 있으면 오류 원문을 공유합니다. 스크립트를 직접 수정할 필요는 없습니다.

후속 두 스크립트는 일별 파생 CSV가 없으면 첫 스크립트를 자동 실행합니다. **입력 NDVI를 교체했다면 반드시 2번부터 다시 실행**해야 합니다. 함수 파일 형태라 Run으로 실행하며, 명령 창에서도 `jimin_growing_season; jimin_ndvi_anomaly; jimin_bare_vs_rye;`로 실행할 수 있습니다. 대화형 입력·외부 API 호출·DB 쓰기는 없습니다. 그림은 `Visible='off'`로 저장합니다.

## 입력과 출력

컨테이너 입력: `/data/processed/v1/matlab/inputs/`

- `fields_20.csv`: `field_id`를 문자열로 보존합니다.
- `ndvi_hls_20fields.csv`: `field_id,date,ndvi,valid_frac`와 제품 식별 열. 실제 확보된 연도만 사용합니다. **2012는 HLS로 관측할 수 없습니다.**
- `engine_strategyB_assumptions.csv`: 리더가 내보낸 long form `field_id,item,value,unit,source,run_id`. `value`는 숫자·윤작 문자열이 섞이므로 문자열로 읽습니다. 필지·item은 유일해야 합니다.

출력: `/data/processed/v1/matlab/outputs/jimin/`

| 파일 | 의미 |
| --- | --- |
| `growing_season_20fields.csv` | 필지·연도별 greenup/peak/senescence civil DOY, 시즌 길이, 임계값, 관측 지원 일수·상태 |
| `jimin_supported_daily.csv` | 세 계산이 공유하는 일별 평활 NDVI. 지원되지 않는 날은 빈칸 |
| `ndvi_anomaly.png` | 필지별 확보 연도 평균 대비 NDVI 차이 그림 |
| `jimin_ndvi_anomaly.csv` | 그림 수치, 기준에 실제 포함된 연도 목록·개수, 관측 지원 일수 |
| `bare_vs_strategyB.csv` | 관측 지원 저NDVI 일수와 corn/soy 별 엔진 달력 가정 시나리오 |
| `jimin_strategyB_assumptions_used.csv` | 사용한 가정 입력 전체 사본, 원문·윤작·source·run_id 보존 |

다시 실행하면 해당 스크립트의 기존 출력만 `old/<실행시각>/`으로 이동한 뒤 저장합니다. 다른 팀원의 결과는 이동하지 않습니다. 결측은 CSV 빈칸으로 남깁니다. 이들은 오프라인 보조 분석이며 DB 적재용 SOT 고정 산출물이나 보정계수가 아닙니다.

## 계산 해석

- QA: NDVI [-1,1], valid_frac [0.5,1]. 같은 날 여러 제품은 평균합니다. 연도 안에서 관측 간격 **20일 이하**만 선형 보간합니다. 연도 경계·긴 구름 공백은 연결하지 않습니다.
- 지원된 연속 구간이 11일 이상일 때만 11일 창·2차 Savitzky–Golay 평활합니다. 설정은 기존 `ndvi_baresoil.m`과 같은 **잠정 스크리닝 가정**이며 현장 검증된 기준이 아닙니다.
- greenup/senescence 기준은 해당 필지·연도의 지원된 NDVI 최솟값 + 진폭의 20%입니다(잠정). 연 최대 피크 앞 마지막 상승 교차, 뒤 첫 하강 교차를 택합니다. 교차하는 두 날짜 모두 지원되어야 하며 긴 결측 사이 교차를 만들지 않습니다. 다모작·잡초·관측 창 제한 때문에 실제 파종/수확일로 해석하지 않습니다. 평탄 곡선·누락 전환은 상태와 빈칸으로 표시합니다. 전환 DOY와 길이는 실제 달력 기준이며 윤년이면 윤일을 포함한 날짜 차이입니다.
- 아노말리: 연도별 지원된 일별 NDVI 평균 → 확보 연도 평균을 같은 비중으로 계산 → 그 필지 평균을 뺍니다. 기준 연도가 2개 미만이면 차이는 빈칸입니다. **장기 평년·2012 가뭄 검증이 아닙니다.** 연도별 관측 날짜가 달라 계절 지원 편향이 있습니다.
- `observed_low_ndvi_days`는 지원된 날 중 NDVI <0.3인 날만 셉니다. 맨땅 확정값이 아니며 잔재·눈·물·구름도 낮은 NDVI를 만들 수 있습니다. 전체 연간 맨땅 일수로 확대하지 않습니다. `coverage=supported_days/365`. 모든 일수 집계에서 2월 29일 제외. winter는 엔진과 같은 **Jan–Apr + Nov–Dec**입니다.

## 전략 B 가정 유도와 한계

숫자 item 6개의 실제 단위는 모두 `day (365-day engine calendar)`입니다.
`corn_plant_doy`, `corn_harvest_doy`, `soy_plant_doy`, `soy_harvest_doy`, `rye_plant_after_harvest_days`, `rye_terminate_before_plant_days`를 입력에서 읽습니다. 숫자를 스크립트 안에 대체값으로 넣지 않습니다. 원문 `crop_calendar`의 날짜와 `model_api/hydro.py`의 `PLANT`, `HARVEST`, `_year_arrays`를 리더가 변환한 값이며 **Iowa 기본 달력 가정**입니다. 현지 관측 파종일이 아닙니다.

`_year_arrays`의 양 끝 날짜 포함 규칙에 따라 봄 호밀 `[1, plant-before]`, 본작물 `[plant, harvest]`, 가을 호밀 `[harvest+after,365]`를 살아 있는 피복으로 가정합니다. 따라서 피복 없는 달력 공백은 `(before-1)+(after-1)`일입니다. 예를 들어 현재 입력의 before=10, after=7이면 15일이며 이는 **엔진 가정의 산술 결과**, 관측 결과가 아닙니다. `assumed_no_living_cover_on_supported_days`는 이 가정을 HLS 지원 날짜에만 제한한 값입니다. 봄 호밀은 전년 가을 정착 성공을 가정합니다.

필지별 `baseline_rotation`은 C-S뿐 아니라 반복 옥수수 등을 포함할 수 있습니다. 원문을 보존하지만 **관측 연도의 작물·윤작 위상을 추정하지 않습니다.** 모든 필지·연도에 corn/soy 두 가정 시나리오를 따로 표시합니다. 저NDVI 관측과 피복 없는 달력 가정은 정의가 달라 차이·정확도 점수를 계산하지 않습니다.

`rye_residue_cover_frac=0.5`는 입력의 **종료된 호밀 잔재 표면 피복률 가정**이며 살아 있는 피복률이나 피복 일수로 변환하지 않습니다. 주 비교표에도 `rye_spring_end_doy=plant-before`, `rye_fall_start_doy=harvest+after`, `rye_residue_cover_frac`, `residue_fraction_source`를 직접 표시합니다. 날짜는 윤일 제외 엔진 DOY 가정이며, 피복률은 정확한 `rye_residue_cover_frac` item의 `fraction` 단위 값을 읽습니다. 해당 item이 없으면 피복률은 빈칸입니다. **잔재 피복률은 살아 있는 호밀 피복이 아닙니다.** 전체 입력 사본에도 source·run_id와 함께 남깁니다. 가정이 없으면 해당 비교는 정보 공백, 잘못된 단위·중복 키·잘못된 달력은 오류로 중단합니다.

## 서버 검증

```bash
python data_pipeline/matlab_jimin_smoke.py
python data_pipeline/matlab_jimin_smoke.py --self-test-only
python -m pytest -q data_pipeline/tests/test_matlab_static.py
```

Python 스모크는 실제 입력을 읽어 별도 `outputs/jimin/python_smoke/`에 같은 계산의 CSV를 저장합니다. PNG는 MATLAB 스크립트가 생성하며 Python에는 시각화 의존성을 추가하지 않습니다. 기존 MATLAB 결과는 건드리지 않습니다. 원본 결측, 긴 공백, 윤일, 중복 날짜, 전환 누락, 확보 연도 아노말리, 달력 양 끝 포함·결측 가정을 검사합니다. MATLAB은 기본 연산만으로 각 날 중심 11점 2차 최소제곱을 풉니다. 구간 양끝에서는 첫/마지막 11점 창을 고정합니다. Python은 같은 창 규칙의 SciPy `mode="interp"`를 쓰며, 독립 최소제곱식과 1e-12 허용오차로 대조합니다. MATLAB 런타임 자체의 수치 실행 인증은 아닙니다. 서버 호스트에는 MATLAB 실행 파일이 없으므로 최종 `.m` 실행은 위 브라우저에서 Run으로 확인해야 합니다. 오류가 나면 파일명·오류 원문을 전달하세요.

## 막힐 때

- 명령 창이 `K>>`이면 `dbquit`를 입력해 디버그 모드를 끝낸 뒤 다시 Run합니다.
- 빨간 오류가 나오면 파일명과 오류 원문을 복사해 1:1 방에 보냅니다. 직접 고치지 않아도 됩니다.
- `Missing input`이면 오류에 표시된 입력 경로를 함께 보냅니다. 입력이 없는 경우 가짜 데이터나 0으로 대체하지 않습니다. `jimin_supported_daily.csv`만 없을 때는 자동 생성하지만, 원본 NDVI·필지·엔진 가정 입력은 리더가 준비해야 합니다.
- 결과의 빈칸·`information_gap_*`는 해당 관측이 계산을 지원하지 않는다는 뜻입니다. Run 실패와 구분해 그대로 공유합니다.
- 다시 Run한 이전 결과는 `old/<실행시각>/`에 있으므로 삭제하지 않아도 됩니다.
