# MATLAB 작업 명세 (김우찬 · 김윤성)

서버 MATLAB 접속은 [infra/matlab/REMOTE.md](../infra/matlab/REMOTE.md)를 봅니다.
열 이름·단위는 [docs/SOT.md](../docs/SOT.md) 2절(단위)·5절(DDL)과 [docs/TEAM_SPEC.md](../docs/TEAM_SPEC.md) 7.4를 따릅니다. 여기 없는 열은 만들지 말고 1:1 채널에 먼저 물어봅니다.

## 공통 규칙

- **입력**: `/data/processed/v1/inputs/` (읽기 전용, 서버가 DB에서 뽑아 둔 CSV).
- **출력**: `/data/processed/v1/matlab/` 에 **CSV**(UTF-8, 쉼표, 헤더 1줄, 소수점 `.`). 같은 파일을 덮어쓰지 말고, 형식을 바꾸면 Hylē에게 알립니다.
- 결측은 **빈칸**. 0으로 채우지 않습니다. 날짜는 `YYYY-MM-DD`. `field_id`·`county_fips`는 **문자열**(앞자리 0 유지: `readtable(..., "TextType","string")` 후 `field_id`를 string으로).
- 파일마다 옆에 `{파일}.manifest.json`: `{"file","rows","sha256","schema_version":"1","matlab_version","script","git_commit":"","created_kst","sources":[...]}`. `sha256`은 비워도 됩니다(Hylē가 채움).
- 스크립트는 `projects/2026NASA/matlab/vegetation/`(우찬), `matlab/climate/`(윤성)에 저장합니다.
- 엔진(`model_api`)은 이 폴더의 CSV를 읽습니다. 파일이 없으면 그 항목만 건너뛰므로, **완성된 것부터** 올리면 됩니다.

### 입력 파일 (서버 준비 완료, 2026-11-15)

| 파일 | 행 | 열 (단위) | 비고 |
| --- | --- | --- | --- |
| `story_fields_ndvi_hls.csv` | 3,024 | `field_id`, `date`, `product`(HLSL30·HLSS30), `ndvi`(무차원), `valid_frac`(0–1, 구름 아닌 픽셀 비율) | Story County 시범 필지 12개, 2023-04-01 ~ 2025-11-23. 필지 평균 |
| `story_fields_crop_history.csv` | 216 | `field_id`, `year`, `cdl_class`, `crop_name`, `share`(0–1) | CDL 2008–2025, 필지 다수 작물 |
| `story_fields_soil.csv` | 6,027 | `field_id`, `awc_cm_cm`, `om_pct`, `kffact`, `drainagecl`, `comppct_r`(%), `mukey` | SSURGO 구성요소별(필지 1개에 여러 행) |
| `story_county_weather_daily_power.csv` | 11,323 | `date`, `t2m_c`, `tmin_c`, `tmax_c`, `precip_mm`, `rh2m_pct`, `ws2m_ms`, `srad_mj_m2` | NASA POWER, Story County 대표점, 1995–2025 |
| `county_weather_monthly_power.csv` | 417,384 | `county_fips`, `state_alpha`, `month`, `precip_mm`(월합), `t2m_c`, `tmax_c`(월평균), `n_days` | 콘벨트 12주 1,122개 카운티, 1995–2025 |
| `county_smap_monthly.csv` | 86,394 | `county_fips`, `month`, `product`, `variable`, `value`, `unit`(cm3/cm3), `n_obs` | SMAP L3, **2015-04부터** (2012 없음). 맥락 칸 |
| `county_yield_nass.csv` | 30,183 | `county_fips`, `year`, `crop`, `yield_bu_ac` | NASS 일괄 파일, 옆축(선택) |
| `county_nldas_monthly.csv` | 준비 중 | NLDAS-2 Noah 근권 토양수분·ET | 서버가 받는 중. 오면 1:1로 알림 |

---

## 김우찬 — #24 HLS NDVI 평활·맨땅 기간 + 계수표

### 작업 1. Savitzky–Golay 평활과 dekad 집계 → `field_dekad.csv`

- 입력: `story_fields_ndvi_hls.csv` (+ 기상 열은 `story_county_weather_daily_power.csv`)
- 처리:
  1. `valid_frac < 0.5`인 관측은 버리고 `qa_flag`에 사유를 남깁니다(임계값은 파라미터).
  2. 필지·연도별로 dekad(매월 1–10, 11–20, 21–말; 1..36)로 묶어 `ndvi_raw`=dekad 평균, `n_obs`=관측 수.
  3. 빈 dekad는 선형 보간한 뒤 Savitzky–Golay(`sgolayfilt` 또는 `smoothdata(...,"sgolay")`, 창·차수는 파라미터, 기본 창 5 dekad·2차)로 `ndvi_sg`.
  4. `bare_flag` = `ndvi_sg < 0.3` (임계값 파라미터, `calibration_params.csv`에 기록).
  5. `precip_mm`(dekad 합), `t2m_c`(dekad 평균)은 POWER 일자료에서. `et0_mm`은 POWER에 없으면 빈칸. `sm_anom_ctx`는 빈칸으로 둡니다(엔진이 채움).
- 출력 열(이 순서): `field_id`, `year`, `dekad`, `date_start`, `ndvi_raw`, `ndvi_sg`, `n_obs`, `bare_flag`(true/false), `precip_mm`, `et0_mm`, `t2m_c`, `sm_anom_ctx`, `qa_flag`
- 키: `field_id, year, dekad` 중복 없음.

### 작업 2. 필지별 맨땅 기간 → `field_season.csv`

- 입력: 작업 1의 `field_dekad.csv`
- 계절 `spring`(MAM)·`summer`(JJA)·`fall`(SON)·`winter`(DJF)와 `annual` 행.
- 출력 열: `field_id`, `year`, `season`, `ndvi_p50`(계절 `ndvi_sg` 중앙값), `bare_days`(bare dekad 수 × 일수), `bare_start`, `bare_end`(그 계절 가장 긴 연속 맨땅 구간의 시작·끝 날짜), `precip_mm`, `tmin_c`, `tmax_c`, `et0_mm`, `smap_sm_anomaly`(빈칸), `source_notes`(예: `hls;power`)
- HLS가 없는 겨울(관측 0)은 `bare_days`를 빈칸으로 두고 `source_notes`에 `no_obs`.

### 작업 3. V9 코드 계수표 → `coefficients.csv`

- 우찬님 V9 MATLAB 코드에 있는 **물 요구량(Kc 등)·피복작물 효과 계수**를 한 줄에 하나씩 옮깁니다. 값을 새로 만들지 않습니다.
- 출력 열: `param`(snake_case, 예 `kc_corn_mid`), `value`, `unit`(무차원·mm·% 등), `crop`(`corn`·`soybean`·`cereal_rye`… 없으면 빈칸), `stage`(`ini`·`mid`·`end`·빈칸), `effect`(무엇에 쓰는지 한 줄), `source`(문헌 이름 또는 URL·DOI), `source_page`, `v9_file`(V9의 파일명:줄), `notes`
- 출처가 없는 계수는 `source`를 `미확인`으로 둡니다. 엔진은 `미확인` 계수를 "assumption"으로 표시합니다.
- 기준 문헌 예: FAO-56 (Allen et al., 1998) Table 12(Kc), SARE "Managing Cover Crops Profitably", Iowa State Extension. 쪽 번호를 적어 주세요.

### 끝나면

`field_dekad.csv`, `field_season.csv`, `coefficients.csv`(+ 각 manifest)와 `matlab/vegetation/*.m`이 저장됐다고 1:1 채널에 알립니다. 방법 비교 그림(`method_compare.png`)이 있으면 함께 올립니다.

---

## 김윤성 — #29 2012 가뭄 vs 평년 카운티 비교 (물수지 검증용)

목적: 엔진의 몬테카를로 물수지가 2012년 가뭄을 "나쁜 해"로 잡는지 확인할 기준표를 만듭니다.

- 입력: `county_weather_monthly_power.csv`, `county_nldas_monthly.csv`(도착하면), `county_smap_monthly.csv`(2015 이후라 2012는 없음, 참고용), `county_yield_nass.csv`(선택)
- 평년: **1995–2011 + 2013–2024**의 같은 달 평균(2012 제외). 기간은 파라미터.
- 생육기: 5–9월(파라미터).

### 출력 1. `drought_2012_county.csv`

- 열: `county_fips`, `state_alpha`, `variable`, `period`(`2012-05`…`2012-09`, `2012-MJJAS`), `value_2012`, `baseline_mean`, `baseline_sd`, `anomaly`(value − baseline), `anomaly_pct`(%, 강수만), `z_score`, `unit`, `source_id`(`power`·`nldas2`·`nass`)
- `variable` ∈ `precip_mm`, `tmax_c`, `rzsm`(NLDAS 근권 토양수분, 도착 시), `et_mm`(NLDAS, 도착 시), `yield_bu_ac`(선택, 연 단위면 `period`=`2012`)
- NDVI: 2012년에는 HLS가 없습니다(HLS 2013년부터). NDVI 행은 만들지 말고, 1:1 채널에 "2012 NDVI 필요하면 MODIS 요청"이라고만 남겨 주세요.

### 출력 2. `climate_annual.csv` (Story 시범 필지 12개)

- 열: `field_id`, `year`, `precip_mm`, `et_mm`(NLDAS, 없으면 빈칸), `et0_mm`(빈칸 가능), `t2m_mean_c`, `ndvi_peak`(우찬의 `field_dekad.csv` 있으면 연 최대 `ndvi_sg`, 없으면 빈칸), `gdd_c`(기준 10 °C, 일 평균기온), `frost_days`(tmin < 0 °C), `heat_days`(tmax > 32 °C), `crop_cdl`(`story_fields_crop_history.csv`), `source_ids`(`power;cdl` 등 `;` 구분)
- 필지 기상은 Story County 대표점 POWER 값을 씁니다(맥락 칸 규칙, SOT 2절).

### 출력 3. `calibration_params.csv` (두 사람 공동)

- 열: `param`, `value`, `unit`, `method`, `source`, `notes`
- 넣을 것: `bare_ndvi_threshold`(우찬), `sg_window_dekad`, `sg_order`, `valid_frac_min`, `baseline_years`, `growing_season_months`, `heat_tmax_c`(32), `frost_tmin_c`(0)

### 끝나면

`drought_2012_county.csv`, `climate_annual.csv`(+ manifest)와 `matlab/climate/*.m` 저장 후 1:1 채널에 알립니다. 2012가 평년보다 강수 몇 %, 토양수분 z 몇인지 한 줄 요약을 같이 적어 주세요.

---

## manifest.json 예시

```json
{"file":"field_dekad.csv","rows":1296,"sha256":"","schema_version":"1","matlab_version":"R2026b","script":"matlab/vegetation/ndvi_sg.m","git_commit":"","created_kst":"2026-11-15T17:30","sources":["hls","power"]}
```
