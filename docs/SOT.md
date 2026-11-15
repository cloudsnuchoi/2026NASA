# SOT · Source of Truth

팀 **아몰라** · `cloudsnuchoi/2026NASA`  
동결: **2026-11-15 08:00–10:00 Asia/Seoul (KST)**. 갱신: **2026-11-15 08:20 KST** (1.5절), **2026-11-15 11:10 KST** (1.6절 두 층 공간, QuickStats 선택 + NASS 일괄 대체, Story County `19169` 동결). **최종 갱신 2026-11-15 18:57 KST**: 제품 이름 **ART FARM**(부제 *Field Shift: Adapting Farms with NASA Data*), 화면 두 단계 **Tier 1 Quick Screen / Tier 2 Deep Analysis**(1.7절), `POST /quick` 계약(6.0절).

이 문서가 **데이터, 식별자, 단위, 좌표계, 집계, 디렉터리, DB 스키마, API 계약**의 단일 원본이다. 코드·이슈·에이전트는 여기와 다른 필드명, 단위, 엔드포인트를 만들지 않는다. 바꾸려면 이슈와 PR이 필요하다.

충돌 시 우선순위: (1) 공식 챌린지·제출·심사 원문 (2) 이 문서와 [PRD.md](./PRD.md) (3) [DECISIONS.md](./DECISIONS.md) (4) 이슈 본문. 여기 없는 해상도·엔드포인트·라이선스 문구는 지어내지 않고 `미확인`으로 남긴다.

상세 배경은 팀 내부 메모 `fieldshift_context_v3.md`, `fieldshift_data_pipeline.md`에 있으나, **주말 구현 계약은 이 저장소 문서가 이긴다.**

---

## 1. 데이터셋

`공식07` = 챌린지 Resources 탭에 있는 항목. `외부` = 탭에 없음. 쓰면 제출 페이지 **Other Data**와 References에 적는다. 라이선스는 사용자 가이드로 재확인하고, 이 표의 문구를 최종 법적 단정으로 쓰지 않는다.

### 1.1 필수 (이번 주말 본편)

| 이름 | 출처 | 해상도·주기 (탭/통상, 불일치는 미확인으로 표시) | 접근 | NASA 여부 | 라이선스·인용 (확인 후 References에 확정) |
| --- | --- | --- | --- | --- | --- |
| NASA POWER | NASA LaRC, 공식07 | 일·월·기후값. 공간 격자 문서는 0.25°/0.5° 등 **불일치** → **API 응답 메타데이터**를 따름. Daily는 문서상 1981-01-01~NRT | 계정 없이 REST. `GET https://power.larc.nasa.gov/api/temporal/daily/point` 등 | NASA | NASA Earth Science 공개 데이터. POWER/LaRC 인용. 사용자 가이드 확인 |
| GPM IMERG | NASA/JAXA, 공식07 | 공간은 탭에 없음. 통상 0.1°, 30분–일. Final 예: `GPM_3IMERGHH` (버전은 Earthdata에서 재확인) | Earthdata + `earthaccess`. 단기명으로 검색 후 AOI 클립 | NASA | NASA/JAXA 제품 DOI·인용. Earthdata Login으로 다운로드 |
| SMAP | NASA/NSIDC, 공식07 | 탭: 2–3일. 공간 통상 수–36 km. L3 방사계 예: `SPL3SMP` (버전은 NSIDC에서 재확인) | Earthdata + `earthaccess` 또는 AppEEARS | NASA | NASA/NSIDC 제품 인용. **필지 정밀 값으로 쓰지 않음** (맥락 칸만) |
| Landsat 8/9 또는 HLS v2 | Landsat: USGS/NASA 공식07. HLS(`HLSL30`/`HLSS30`): 외부(Resources 개별 행 아님) | Landsat 탭: 30 m, 통상 8–16일. HLS: 30 m COG | EarthExplorer, Earthdata, AppEEARS, 또는 확인된 GEE 컬렉션 | Landsat/HLS는 NASA·파트너 | Landsat는 통상 USGS 퍼블릭 도메인. HLS는 제품 인용. 가이드 확인 |
| SRTM | NASA/USGS, 공식07 | 통상 1 arc-sec(~30 m) 제품(예: SRTMGL1). 버전은 Earthdata에서 확인 | Earthdata / earthaccess | NASA | NASA/USGS 인용 |
| SSURGO / gSSURGO | USDA NRCS, 공식07 (gSSURGO는 SSURGO 항목의 격자 배포) | 폴리곤(SSURGO) / 주 단위 격자(gSSURGO, 통상 10 m 안내) | Soil Data Access, Web Soil Survey, 주 FileGDB 다운로드 | 기타 (공식07) | 미국 정부 저작물 가능성이 큼. NRCS 이용 조건 확인 후 인용 |
| CDL (Cropland Data Layer) | USDA NASS, 공식07 (CropScape) | 탭: 30 m, 연 1회. 공식 배포 2008–2025 전국 30 m. 2024–2025는 10 m 원본+30 m 리샘플 안내 | 공식 다운로드 또는 문서화된 CDL 서비스. 사용 전 엔드포인트 생존 확인. 클래스 코드는 공식 속성표만 | 기타 (공식07) | 미국 정부 저작물 가능성이 큼. NASS 인용. CropScape UI 로그인은 변동 가능 |
| Crop Sequence Boundaries (CSB) | USDA NASS, **외부** | 8년 창, 2018–2025는 v2024 안내(2026-03-27 공개) | 공식 FileGDB. 아이오와만 클립 | 기타 (외부) | NASS 이용 조건 확인. **제출 Other Data 필수.** 소유 경계가 아님 |
| USDA NASS QuickStats / NASS bulk (**선택**) | USDA NASS, 공식07 | 연, 카운티/주 수량(`yield_bu_ac`). **옆축·보조**. 본편 목적함수·go/no-go 아님 | **선택.** QuickStats API(`api_GET`, 키 필수, 요청당 최대 50,000행) 사이트는 2026-11-15 팀에서 접속 불가. **대체 (확인함):** NASS Large Datasets 일괄 파일. 안내 URL `https://www.nass.usda.gov/datasets/` 는 11:10 KST에 origin 500. 목록·파일 호스트 `https://sb.nass.usda.gov/datasets/` (HTTP 200). 작물 파일 `qs.crops_20261103.txt.gz` (1,132,568,713 bytes, Last-Modified 2026-11-03 08:14 UTC = 17:14 KST, HTTP 200, 키 없음). 콘벨트 12주·카운티·옥수수/대두·연 수량만 필터해 `/data/raw/nass_bulk/`에 저장. 실패 시 수량 열은 `null`이고 CDL/CSB 백테스트만 유지 | 기타 (공식07) | NASS 인용. API를 쓸 때만 “This product uses the NASS API but is not endorsed or certified by NASS.” |
| 피복·윤작 문헌 | SARE, Iowa State Extension, MCCC 등, **외부** | 해당 없음 (문서) | 공식 URL. 전문 PDF를 저장소에 올리지 않음 | 기타 (외부) | 각 문헌 저작권. 짧은 인용+DOI/URL만 RAG. Other Data·References |

### 1.2 강하게 권장 (시간 되는 대로)

| 이름 | 출처 | 해상도·주기 | 접근 | NASA 여부 | 라이선스·인용 |
| --- | --- | --- | --- | --- | --- |
| PRISM | Oregon State PRISM Climate Group, 공식07 | 일·월·30년. 무료 웹서비스 해상도 4 km 등 (문서 2025-03-26). 30년 평년은 웹서비스에 없고 별도 다운로드 | `services.nacse.org` 그리드 서비스 또는 FTP | 기타 (공식07) | PRISM 이용 약관 확인 후 인용 |
| OpenET | OpenET, 공식07 (탭은 미국 서부; 2025-12-16 발표로 인접 48주 래스터 확대). 아이오와 **필지 ID 서비스 개통은 미확인** | 통상 30 m ET, 2016~ (확대 발표 기준) | `POST https://openet-api.org/raster/timeseries/point` (API 키). 필지 경계 API는 이 주말 전제로 두지 않음 | 기타 (공식07) | OpenET 약관·키. 시간이 없으면 FAO-56만으로 물 비교 |
| ECOSTRESS | NASA/JPL, 공식07 | 통상 약 70 m (탭/문서 불일치 가능, 제품 메타데이터 따름) | Earthdata / JPL / AppEEARS | NASA | 제품 DOI·인용. 공백은 「관측 없음」 |
| USDA 가격 lite / RMA Cause of Loss | USDA AMS/ERS/RMA, 주로 **외부** 또는 NASS 수량 일부 | 연·카운티/주 등 | NASS 일괄 파일(선택), ERS, RMA 공개 표. QuickStats API는 선택 | 기타 | 인용 + Other Data. 본편 목적함수로 쓰지 않음 |

### 1.3 이번 주말 후순위 (본편에서 빼도 됨)

GAEZ, GRACE/GRACE-FO, NLCD, LANDFIRE, GEDI, VIIRS, ERA5 등. (**NAIP와 NLDAS는 2026-11-15 08:20 결정으로 1.5절로 승격.**) 쓰면 출처와 NASA/기타를 구분해 제출서에 적는다. GRACE는 유역 맥락만, 필지 값 금지.

### 1.4 접근 주의

- SMAP·GRACE를 필지 정밀 관측처럼 쓰지 않는다.
- POWER 격자는 API 메타데이터를 따른다.
- CDL 웹서비스는 호출 전에 생존을 확인한다. 클래스 코드를 추측하지 않는다.
- 미국 전용 자료를 한국 필지에 붙이지 않는다.
- 비밀값(Earthdata, OpenET, 선택적 QuickStats 키 등)은 환경 변수만. NASS 일괄 파일은 키가 없다.

### 1.5 2026-11-15 08:20 KST 추가 (예측·시나리오·비전·영상)

근거: [DECISIONS.md](./DECISIONS.md) 2026-11-15 08:20, [TEAM_SPEC.md](./TEAM_SPEC.md) 4·5절. 접근 경로는 2026-11-15 KST에 웹·API로 확인한 것만 적었다. 파일 내부 변수명처럼 열어 보지 못한 것은 `미확인`.

| 이름 | `source_id` | 출처 | 해상도·주기 | 접근 (확인함) | NASA 여부 | 라이선스·인용 | 우선 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| NLDAS-2 Noah / Forcing | `nldas2` | NASA GES DISC, 공식07 (#16 NLDAS/GLDAS) | 0.125°, 시간(`NLDAS_NOAH0125_H`)·월(`NLDAS_NOAH0125_M`), forcing `NLDAS_FORA0125_H`, 1979~ | Earthdata + `earthaccess` (CMR에서 v2.0 확인). Giovanni 가능 | NASA | DOI 10.5067/T4OW83T8EXDO (Noah 시간). data.nasa.gov 메타 라이선스: U.S. Government Works | P0 (ET·근권 토양수분, 맥락 칸) |
| GLDAS Noah | `gldas` | NASA GES DISC, 공식07 (#16) | 0.25°, 3시간·월, v2.1 2000~ / v2.0 1948~ | Earthdata (CMR `GLDAS_NOAH025_3H`, `_M`) | NASA | 제품 DOI·인용 (사용 시 확인) | 컷 (미국 밖 대체용) |
| GEOS-S2S-3 | `geos_s2s` | NASA GMAO, **외부** | 0.5° 격자, 월 초기화 40멤버(GMAO 설명) | `https://portal.nccs.nasa.gov/datashare/gmao/geos-s2s-3/` → `NRT/APCN/YYYYMM/` 에 `YYYYMM_precip.tar.xz`, `YYYYMM_at.tar.xz` 등 공개 목록(2026-11-02 파일 확인). `Hindcast/` 폴더 있음. 압축 내부 형식·변수명·리드 수는 **미확인** | NASA | 명시 라이선스 문구 **미확인**. GMAO GEOS-S2S-3 인용 + 접근일 | P0 (다음 시즌 분포) |
| NEX-GDDP-CMIP6 | `nex_gddp` | NASA NCCS / NEX, **외부** | 0.25°, 일, historical ~2014 + SSP | `s3://nex-gddp-cmip6/` (us-west-2, AWS Open Data) 또는 NCCS THREDDS NCSS 칸 추출 | NASA | **CC0** (2022-09 이후). 인용: “NEX-GDDP-CMIP6 was accessed on DATE from https://registry.opendata.aws/nex-gddp-cmip6” + tech note | P0 (2030년대 분포) |
| NAIP | `naip` | USDA FPAC, 공식07 (#14) | 아이오와 중부 STAC 검색 결과 2017(1 m), 2019·2021(0.6 m), 2023(0.3/0.6 m), 2025(0.6 m) | Microsoft Planetary Computer STAC `collections=naip` (검색 무계정), AWS `naip-analytic`(Requester Pays) | 기타 (공식07) | AWS 레지스트리 표기 “Public Domain with Attribution” | P0 (영상), P1 (앱 썸네일) |
| HLS v2 | `hls` | NASA LP DAAC, 외부(Landsat/S2 행의 조화 산출물) | 30 m, `HLSL30` 2013-04-11~, `HLSS30` 2015-11-28~ | Earthdata + `earthaccess` (CMR v2.0 확인) | NASA | 제품 인용 | P0 (NDVI·Prithvi 입력) |
| Prithvi 작물 분류 체크포인트 | `prithvi_crop` | NASA·IBM (Hugging Face `ibm-nasa-geospatial`), **외부 모델** | 입력 HLS 6밴드 × 3시점, 224×224 칩, 30 m, 13클래스 | `https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-1.0-100M-multi-temporal-crop-classification` (`multi_temporal_crop_classification_Prithvi_100M.pth`, `config.yaml`) | NASA·파트너 | **Apache-2.0**, DOI 10.57967/hf/0954. 카드 성능 aAcc 60.64 %, mIoU 0.4269 | P0 보조 (실패 시 CDL) |
| Prithvi-EO-2.0 백본 | — | NASA·IBM·JSC | 사전학습만 (tiny/100M/300M/600M, TL 변형), 미세조정본은 Sen1Floods11·BurnScars뿐 | HF `ibm-nasa-geospatial/Prithvi-EO-2.0-*` | NASA·파트너 | 각 모델 카드 | **사용 안 함** (작물 헤드 없음 → 미세조정 필요 → 결정 위반) |
| WeatherNext 2/3 | `weathernext` | Google DeepMind, **외부** | WN2: 0.25°, 6시간, 15일, 64멤버. 신규는 WN3 권장 | Earth Engine / BigQuery / GCS. **접근 신청 폼 승인 5–7 영업일** | 기타 | 과거 자료 CC BY 4.0, 실시간은 별도 실험 약관 | **선택·컷 기본** (작업 창 15일 애드온만) |

규칙:

- GEOS-S2S·NEX-GDDP·NLDAS는 **맥락 칸** 자료다. 필지 정밀 값처럼 표시하지 않는다(2절 2단 격자의 맥락 단).
- 미래는 분포(앙상블 분위, 다모델 범위)로만 보여 준다. 3년 결정론적 값 금지.
- NEX-GDDP 기준기간은 모델 historical 1985–2014, 미래 창은 2031–2040(기본). delta 방식만.
- Prithvi는 **추론만**. 결과는 `vision_result` 테이블에 배치 적재하고, 요청 경로에서 GPU 추론을 하지 않는다.

---

### 1.6 공간 두 층 (2026-11-15 11:10 KST 동결)

콘벨트 전체를 대상으로 하되, **모든 데이터를 콘벨트 30 m로 받지 않는다.** 상세 그림은 [ARCHITECTURE.md](./ARCHITECTURE.md).

| 층 | 범위 | 해상도 | 데이터셋 (이번 주말 P0) | 화면 역할 |
| --- | --- | --- | --- | --- |
| **1층** 넓게 | 콘벨트 12개 주: `IA, IL, IN, OH, NE, MN, SD, WI, MO, KS, MI, KY` | 카운티 집계 (네이티브 칸을 카운티 평균 또는 중심점 배정) | NASA POWER 일별(카운티 중심점, 1995–2025), GPM IMERG 일별, SMAP L3/L4(맥락 칸, 필지 정밀 금지), CDL **카운티 작물 비율** 2008–2025, NEX-GDDP-CMIP6 카운티 평균(2030s) | 어디든 핀을 찍으면 1차 물·맨땅·가뭄 위험과 윤작 힌트 |
| **2층** 깊게 | 아이오와 **Story County**, `county_fips=19169` | 필지 30 m 또는 필지 평균(CSB 마스크) | CDL 30 m 래스터 2008–2025, Crop Sequence Boundaries, SSURGO(유기물, K factor, 배수, AWC), HLS L30/S30 NDVI, GEOS-S2S-3 다음 시즌 분포 | 데모 본편, 몬테카를로, 2012 가뭄 백테스트, 복셀 시뮬 |

선택 수량(옆축): NASS 일괄 파일로 12주 카운티 연 수량. 없거나 실패해도 1·2층 P0는 성립한다.

저장 위치: 원본 `/srv/hackathon/data/raw/<dataset>/` (SOT 약칭 `/data/raw`). 1층 집계와 2층 래스터를 같은 데이터셋 폴더 안에서 `tier1_county/`와 `tier2_story/`처럼 구분해도 된다. 가공은 `/srv/hackathon/data/processed/vN`.


### 1.7 화면 두 단계 Tier 1 / Tier 2 (2026-11-15 18:57 KST 동결)

1.6절의 **데이터 두 층**(카운티 집계 / 필지 30 m)은 그대로다. 그 위에 **화면 두 단계**를 둔다. 상세 제품 규칙은 [PRD.md](./PRD.md) 4–6절.

| 단계 | 범위 | 입력 | 엔드포인트 | 상태 |
| --- | --- | --- | --- | --- |
| **Tier 1 Quick Screen** | 콘벨트 12개 주 안의 임의 네 꼭짓점 다각형 | NASA POWER 일별 2016–2025(다각형 중심점), USGS 3DEP 꼭짓점 고도, FAO-56 Kc(Table 12), FAO-33 Ky | `POST /quick` (6.0절) | **계획** (계약 동결, 구현 진행 중) |
| **Tier 2 Deep Analysis** | 데모 필지 **20개**: Story IA `19169` 12, McLean IL `17113` 3, Lancaster NE `31109` 3, Union OH `39159` 2 | 1.6절 2층 데이터 + IMERG, NLDAS-2, GEOS-S2S, NEX-GDDP-CMIP6, Prithvi `vision_result` | 6절 기존 엔드포인트 (`/fields`, `/field/{id}/*`, `/strategies/compare`, `/validation/backtest`, `/explain`) | **구현됨** (model_api, VPS 내부) |

Tier 2 진입 조건: Tier 1 다각형이 데모 필지 CSB 경계와 **겹칠 때**. 겹치지 않으면 `deep_analysis.available=false`와 문구 `"Deep analysis available in 4 pilot counties"`.

---

## 2. 정규 ID, 단위, 좌표계

| 항목 | 규칙 |
| --- | --- |
| `field_id` | **CSB 고유 식별자.** 적재 시 CSB 속성 테이블의 공식 컬럼명을 확인해 그대로 쓴다. 컬럼명을 여기서 지어내지 않는다. 문자열로 저장. |
| `county_fips` | 5자리 문자 (주 2 + 카운티 3). 2층 본편은 **`19169`** (Iowa Story County). 1층은 콘벨트 12주 모든 카운티. |
| `state_alpha` | 본편 **`IA`**. 1층은 콘벨트 12주 코드. 선택 확장 시 `NE`. |
| `strategy_code` | `A` \| `B` \| `C` \| `D` (PRD 4절). 2ⁿ 후보 생성(TEAM_SPEC 2.3)을 쓰면 후보는 `candidate_id`(예: `C-S+cover_rye`)로 식별하고, A–D에 해당하면 `strategy_code`를 함께 준다. |
| `year` | 작물 연도 정수. CDL 연 라벨과 맞출 때는 CDL 연도를 따름. |
| `date` | 저장은 ISO 8601 날짜(`YYYY-MM-DD`). 시각이 있으면 UTC. 화면의 현지 달력은 `America/Chicago`. |
| 저장 CRS | **EPSG:4326** (경위도, WGS84). `geometry`는 GeoJSON도 4326. 경도·위도 순서 주의(GeoJSON은 lon, lat). |
| 분석 투영 | **EPSG:5070** (NAD83 Conus Albers). 면적·거리·리샘플은 여기서 계산한 뒤 저장은 4326으로 되돌린다. |
| 온도 | °C (`t2m_c`, `tmin_c`, `tmax_c`) |
| 강수·ET·ETo | mm (`precip_mm`, `et0_mm`, `etc_mm`) |
| 토양수분 | 제품 원단위를 컬럼 주석에 기록. 표시·모델에는 **평년 대비 아노말리**를 우선 (`smap_sm_anomaly`, 무차원 또는 제품 단위 차). 필지 평균인 척하지 않음. |
| NDVI 등 식생지수 | 무차원 (`ndvi`). 유효 범위는 제품 정의. |
| 면적 | ha (`area_ha`). 에이커가 필요하면 표시 직전에만 변환하고 필드명을 `area_ac`로 구분. |
| 수량 (NASS, 선택) | `bu/ac` (`yield_bu_ac`). 리터/ha로 바꾸지 말고, 단위를 응답에 포함. 없으면 `null`. |
| 지수 스코어 | 0–1 또는 문서화된 상대 지수. **확정 t/ha, kg/ha를 자동 출력하지 않음.** |
| 확률·분위 | P10/P50/P90, CVaR는 같은 물리량 단위를 응답의 `unit` 필드에 명시. |

2단 격자:

1. **필지 단 ≈ 30 m** (HLS/CDL/광학/ECOSTRESS/SRTM/토양) → 마스크 후 **필지 평균** 또는 구역 통계.
2. **맥락 단** (SMAP, IMERG, POWER 등): **네이티브 칸을 필지 중심점에 배정.** 칸을 필지 모양으로 쪼개 정밀한 척 하지 않음.

CSB 폴리곤은 소유 경계·필지세가 아니다. API·UI에 이 문장을 넣는다.

---

## 3. 시간 집계

| 주기 | 쓰는 곳 | 규칙 |
| --- | --- | --- |
| 일 (`daily`) | 서리·폭염, 강수, FAO-56 입력, 기후 MC 표본 | 달력일. 결측은 채우기 전에 QA 플래그. 빈 SMAP 날을 필지 수분으로 보간하지 않음. |
| 10일 순 (`dekad`) | NDVI, 맨땅 표시, SMAP 표시 | 매월 1–10, 11–20, 21–말. 집계 함수(평균·최대·합)를 컬럼에 적는다. |
| 계절 (`season`) | 취약 계절 카드 | `spring`=`MAM`, `summer`=`JJA`, `fall`=`SON`, `winter`=`DJF` (북반구). 필요하면 `annual` 행을 별도. |
| 연 / 윤작 사이클 | CDL/CSB 백테스트, 전략 비교 | 전략 `A`는 2년 사이클, `C`/`D`는 문서화된 다년 사이클. 사이클 정의는 `strategy_score` 메타에 기록. |
| 약 30년 | 평년, 아노말리, MC·CVaR | POWER 등이 허용하는 최대 창(문서상 1981~ 가능). 실제 적재 기간을 `data_source`와 응답 `period`에 명시. |

아노말리는 **같은 격자의 평년** 대비로 계산한다. 문헌 결측을 0으로 채우지 않는다. 광학 QA/Fmask, SMAP retrieval/quality, IMERG 극값 플래그는 제품 가이드의 비트를 따르고, 비트를 여기서 지어내지 않는다. ECOSTRESS 공백은 「관측 없음」.

---

## 4. 디렉터리 규칙

VPS(또는 로컬 데이터 디스크) 기준. **Git에는 원본·가공 래스터를 넣지 않는다.** 스크립트와 매니페스트만 `data_pipeline/`에 커밋한다.

```text
/data/raw/                 # 불변. 다운로드 원본만. 덮어쓰기 금지. 재처리는 새 사본 금지, 재다운로드만
  /power/ /imerg/ /smap/ /hls/ /landsat/ /srtm/ /cdl/ /csb/ /ssurgo/ /nass_bulk/ /quickstats/ /prism/ ...
/data/processed/v1/        # 첫 가공본. 스키마가 바뀌면 v2, v3... (vN을 덮어쓰지 말 것)
/data/cache/               # 재생성 가능
/data/lit/                 # 문헌 원문은 라이선스가 허용할 때만. 저장소에는 URL·DOI 목록만
```

코드 저장소 레이아웃:

```text
data_pipeline/   # ETL, 매니페스트, QA
model_api/       # FastAPI, 스코어링, MC, 백테스트
rag/             # 근거 카드, 검색, LLM tool-call 프롬프트
frontend/        # 웹 UI
matlab/          # 오프라인 스크립트. 출력은 /data/processed/vN 또는 DB
infra/           # Docker Compose, Caddy, env example
notebooks/       # EDA
docs/            # PRD, SOT, 체크리스트, 결정 로그
```

MATLAB 출력은 `/data/processed/v{N}/matlab/` 아래 다음 파일만 만든다 (스키마 상세: [TEAM_SPEC.md](./TEAM_SPEC.md) 7.4).

| 파일 | 키 | 적재 테이블 |
| --- | --- | --- |
| `field_dekad.parquet` | `field_id, year, dekad` | `field_dekad` |
| `field_season.parquet` | `field_id, year, season` | `field_season` |
| `climate_annual.parquet` | `field_id, year` | `climate_annual` |
| `scenario_climate.parquet` | `field_id, horizon, source_id, scenario, model, member, variable, period` | `scenario_climate` |
| `calibration_params.csv` | `param` | `calibration_param` |

공통: Parquet 우선(CSV면 UTF-8, 쉼표, 헤더 1줄), snake_case, 결측은 빈 값(0 금지), 파일마다 `{file}.manifest.json`(`rows`, `sha256`, `schema_version`, `matlab_version`, `script`, `git_commit`, `created_kst`, `sources`). MATLAB은 DB에 직접 쓰지 않고, 적재는 `data_pipeline/load_matlab.py`가 한다.

---

## 5. DB 스키마 (초안 DDL)

서비스 DB: **Postgres 16 + PostGIS + pgvector**. 협업 도구(Mattermost 등)와 **데이터베이스를 분리**한다. 분석 중간 테이블은 Parquet + DuckDB도 허용하나, API가 읽는 값은 아래 테이블(또는 이와 동등한 뷰)에 있어야 한다.

임베딩은 `intfloat/multilingual-e5-small`(MIT, 한·영, 384차원)로 고정한다(2026-11-15 Hylē 승인, DECISIONS). 문서는 `passage: `, 질의는 `query: ` 접두사를 붙인다.

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE data_source (
  source_id       text PRIMARY KEY,
  name            text NOT NULL,
  is_nasa         boolean NOT NULL,
  official07      boolean NOT NULL,
  license         text,
  citation        text,
  access_url      text,
  notes           text
);

CREATE TABLE fields (
  field_id        text PRIMARY KEY,          -- CSB id
  csb_version     text,
  county_fips     char(5) NOT NULL,
  state_alpha     char(2) NOT NULL,
  geom            geometry(MultiPolygon, 4326) NOT NULL,
  centroid        geometry(Point, 4326),
  area_ha         numeric,
  current_rotation text,                     -- e.g. 'C-S'
  notes           text
);

CREATE INDEX fields_geom_gix ON fields USING GIST (geom);

CREATE TABLE field_season (
  field_id        text NOT NULL REFERENCES fields (field_id),
  year            integer NOT NULL,
  season          text NOT NULL,             -- spring|summer|fall|winter|annual
  ndvi_p50        numeric,
  bare_days       integer,
  bare_start      date,
  bare_end        date,
  precip_mm       numeric,
  tmin_c          numeric,
  tmax_c          numeric,
  et0_mm          numeric,
  smap_sm_anomaly numeric,                   -- context cell, not field-precise
  source_notes    text,
  PRIMARY KEY (field_id, year, season)
);

CREATE TABLE climate_daily (
  field_id        text NOT NULL REFERENCES fields (field_id),
  date            date NOT NULL,
  source_id       text NOT NULL REFERENCES data_source (source_id),
  t2m_c           numeric,
  tmin_c          numeric,
  tmax_c          numeric,
  precip_mm       numeric,
  et0_mm          numeric,
  qa_flag         text,
  PRIMARY KEY (field_id, date, source_id)
);

CREATE TABLE strategy_score (
  field_id        text NOT NULL REFERENCES fields (field_id),
  strategy_code   text NOT NULL,             -- A|B|C|D
  run_id          text NOT NULL,
  n_cycle_index   numeric,
  erosion_index   numeric,
  organic_matter_index numeric,
  pest_break_index numeric,
  water_use_index numeric,
  forage_index    numeric,
  market_index    numeric,
  p10             numeric,
  p50             numeric,
  p90             numeric,
  cvar            numeric,
  unit            text,                      -- unit of p10/p50/p90/cvar
  card            jsonb NOT NULL,            -- why, evidence, benefits, gaps, risks
  created_at      timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (field_id, strategy_code, run_id)
);

CREATE TABLE backtest_result (
  field_id        text NOT NULL REFERENCES fields (field_id),
  strategy_code   text NOT NULL,
  year            integer NOT NULL,
  observed_cdl    text,
  observed_sequence text,
  county_yield_bu_ac numeric,
  notes           text,
  metrics         jsonb,
  PRIMARY KEY (field_id, strategy_code, year)
);

CREATE TABLE evidence_chunk (
  chunk_id        bigserial PRIMARY KEY,
  strategy_code   text,                      -- nullable = general
  source_title    text NOT NULL,
  doi             text,
  url             text,
  license         text,
  quote           text NOT NULL,
  embedding       vector(384)                -- intfloat/multilingual-e5-small (2026-11-15 확정)
);

-- 주말 안에 임베딩이 실패하면 embedding 을 비우고 키워드 검색만 한다.
CREATE INDEX evidence_chunk_t_idx ON evidence_chunk
  USING GIN (to_tsvector('simple', coalesce(quote, '') || ' ' || coalesce(source_title, '')));

-- 2026-11-15 08:20 추가: MATLAB 산출, 시나리오, 비전 (TEAM_SPEC 7.4)
CREATE TABLE field_dekad (
  field_id        text NOT NULL REFERENCES fields (field_id),
  year            integer NOT NULL,
  dekad           smallint NOT NULL,         -- 1..36
  date_start      date NOT NULL,
  ndvi_raw        numeric,
  ndvi_sg         numeric,                   -- Savitzky-Golay smoothed
  n_obs           integer,
  bare_flag       boolean,
  precip_mm       numeric,
  et0_mm          numeric,
  t2m_c           numeric,
  sm_anom_ctx     numeric,                   -- context cell, not field-precise
  qa_flag         text,
  PRIMARY KEY (field_id, year, dekad)
);

CREATE TABLE climate_annual (
  field_id        text NOT NULL REFERENCES fields (field_id),
  year            integer NOT NULL,
  precip_mm       numeric,
  et_mm           numeric,                   -- actual ET (NLDAS-2, context cell)
  et0_mm          numeric,                   -- FAO-56 reference ET from POWER
  t2m_mean_c      numeric,
  ndvi_peak       numeric,
  gdd_c           numeric,                   -- base 10 C
  frost_days      integer,                   -- tmin < 0 C
  heat_days       integer,                   -- tmax > 32 C
  crop_cdl        text,
  source_ids      text,                      -- ';' separated
  PRIMARY KEY (field_id, year)
);

CREATE TABLE scenario_climate (
  field_id        text NOT NULL REFERENCES fields (field_id),
  horizon         text NOT NULL,             -- next_season | 2030s
  source_id       text NOT NULL,             -- geos_s2s | nex_gddp
  scenario        text NOT NULL,             -- forecast | ssp245 | ssp585
  model           text NOT NULL,
  member          text NOT NULL DEFAULT 'mean',
  variable        text NOT NULL,             -- pr | tas | tasmax | tasmin
  period          text NOT NULL,             -- e.g. 2027-JJA, 2031-2040
  value           numeric,
  unit            text,
  baseline_period text,
  anomaly         numeric,
  anomaly_unit    text,
  PRIMARY KEY (field_id, horizon, source_id, scenario, model, member, variable, period)
);

CREATE TABLE vision_result (
  field_id        text NOT NULL REFERENCES fields (field_id),
  year            integer NOT NULL,
  model_id        text NOT NULL,             -- e.g. ibm-nasa-geospatial/Prithvi-EO-1.0-100M-multi-temporal-crop-classification
  scene_dates     text NOT NULL,             -- 3 HLS dates, ';' separated
  crop_pred       text,                      -- field majority class
  class_fractions jsonb,                     -- {class: fraction}
  bare_fraction   numeric,
  agreement_with_cdl numeric,                -- pixel agreement 0-1
  notes           text,
  PRIMARY KEY (field_id, year, model_id)
);

CREATE TABLE calibration_param (
  param           text PRIMARY KEY,
  value           numeric,
  unit            text,
  method          text,
  source          text,
  notes           text
);
```

맵 레이어는 사전 계산한 GeoJSON/COG를 객체 스토리지 또는 `/data/processed/vN/maps/`에 두고, 메타만 DB에 둘 수 있다.

---

## 6. API 계약 (OpenAPI 스타일)

베이스 URL은 배포 후 `infra/`에 적는다. 데모 **인증 없음** (제출: 로그인 없는 링크). 내부 운영 키가 필요하면 게이트웨이에만 두고, 심사 링크는 공개한다.

공통 오류:

```json
{ "error": { "code": "not_found", "message": "Unknown field_id" } }
```

### 6.0 Tier 1 `POST /quick` (2026-11-15 18:57 KST 동결, **계획**)

Tier 1 Quick Screen. 엔진 표기 `"FAO-56 engine (ported from team MATLAB prototype V8)"`. MATLAB 런타임을 부르지 않는다. **순위 필드를 두지 않는다**(`rank`, `score_rank`, `recommended` 금지). 아래 예시의 `<…>`는 형식 표시이며 실제 값이 아니다.

요청:

```json
{
  "polygon": [
    { "lat": 42.0890, "lon": -93.6750 },
    { "lat": 42.0890, "lon": -93.6700 },
    { "lat": 42.0850, "lon": -93.6700 },
    { "lat": 42.0850, "lon": -93.6750 }
  ],
  "crops": ["corn", "soybean"],
  "lang": "en"
}
```

- `polygon`: 꼭짓점 **정확히 4개**, EPSG:4326 `lat`/`lon` (십진수 도). 자기교차 금지. 콘벨트 12개 주 밖이면 `400 out_of_service_area`.
- `crops`: `corn`, `soybean`, `wheat` 중 **서로 다른 2–3개**. 그 밖이면 `400 invalid_request`.
- 윤작 열거: 선택 작물의 순환 배열 중 **같은 작물이 연속하지 않는** 것만(순환 끝–처음 포함). 순서는 열거 순서이며 의미 없다.

응답:

```json
{
  "tier": "quick",
  "label": "screening estimate",
  "engine": "FAO-56 engine (ported from team MATLAB prototype V8)",
  "polygon": { "area_ha": "<float>", "perimeter_m": "<float>", "centroid": { "lat": "<float>", "lon": "<float>" } },
  "terrain": { "elevation_m": { "min": "<float>", "max": "<float>", "mean": "<float>" }, "slope_pct": "<float|null>", "source": "USGS 3DEP Elevation Point Query Service" },
  "climate": { "source": "NASA POWER daily (point at polygon centroid)", "period": { "start": "2016-01-01", "end": "2025-12-31" }, "precip_mm_yr": "<float>", "et0_mm_yr": "<float>", "t2m_mean_c": "<float>" },
  "cards": [
    {
      "sequence": ["corn", "soybean"],
      "label": "screening estimate",
      "metrics": [
        { "name": "crop_water_demand_mm_yr", "value": "<float>", "unit": "mm/yr", "kind": "estimate", "method": "FAO-56 Kc x ET0" },
        { "name": "water_deficit_ratio", "value": "<float>", "unit": "ratio_0_1", "kind": "estimate", "method": "FAO-56 water balance" },
        { "name": "water_saving_vs_cs", "value": "<float|null>", "unit": "%", "kind": "relative_index", "tooltip": "Relative index vs. corn-soybean baseline. Not a guarantee." }
      ],
      "info_gaps": ["No field-level soil test", "No irrigation data", "Economic assumptions are regional averages"],
      "assumptions": [
        { "name": "kc_mid_corn", "value": 1.20, "unit": "-", "label": "assumption", "source": "FAO-56 Table 12", "year": 1998 },
        { "name": "corn_price", "value": "<float|null>", "unit": "USD/bu", "label": "assumption", "source": "USDA ERS|NASS <table name>", "year": "<int>" }
      ]
    }
  ],
  "deep_analysis": {
    "available": false,
    "field_ids": [],
    "highlight_strategies": [],
    "message": "Deep analysis available in 4 pilot counties"
  },
  "sources": [ { "name": "NASA POWER", "url": "https://power.larc.nasa.gov/" }, { "name": "USGS 3DEP", "url": "https://www.usgs.gov/3d-elevation-program" }, { "name": "FAO-56", "url": "https://www.fao.org/3/x0490e/x0490e00.htm" } ],
  "disclaimer": "Screening estimate. This tool does not replace farmer judgment."
}
```

규칙:

- 모든 카드에 `label: "screening estimate"`, `info_gaps`(빈 배열이면 안 됨), `assumptions`(각 항목 `label: "assumption"`, `source`, `year`).
- `assumptions[].source`/`year`를 확인하지 못한 경제 값은 **넣지 않고** `info_gaps`에 적는다. `value: null`로 남겨도 되지만 화면에 숫자를 그리지 않는다.
- Kc는 FAO-56 Table 12(옥수수 mid 1.20, 대두 mid 1.15, 밀 mid 1.15. ini/end 같은 표). Ky는 FAO-33. 표와 대조하지 못한 계수는 `"source": "unverified"`.
- `kind: "relative_index"`인 지표는 화면에 relative-index 툴팁 필수.
- 미래 기후 값은 Tier 1에 두지 않는다(분포 규칙. 미래는 Tier 2 `climate/outlook`).
- POWER·3DEP 호출 실패 시 값은 `null`, 해당 사실을 `info_gaps`에 적는다. 대체값을 채우지 않는다.
- `deep_analysis.available=true`이면 `field_ids`에 겹치는 데모 필지, `highlight_strategies`에 선택 작물과 맞는 전략: `corn`+`soybean` → `["A","B"]`, `wheat` 포함 → `["A","B","C"]`. `D`는 항상 참고 카드이며 강조 목록에 넣지 않는다.

**Tier 2 화면 규칙 (기존 응답).** `POST /strategies/compare` 응답에는 현재 `rank` 필드가 있다(2026-11-15 18:57 확인). UI는 `rank`를 **표시하거나 정렬에 쓰지 않는다**. 필드 제거는 계획(별도 이슈, 계약 테스트와 함께).

### `GET /health`

응답 예:

```json
{ "status": "ok", "time": "2026-11-15T12:00:00Z" }
```

### `GET /field/{id}/profile`

응답 예:

```json
{
  "field_id": "CSB-EXAMPLE-0001",
  "csb_version": "v2024",
  "county_fips": "19169",
  "state_alpha": "IA",
  "area_ha": 24.3,
  "current_rotation": "C-S",
  "centroid": { "type": "Point", "coordinates": [-93.5, 42.0] },
  "geometry": { "type": "MultiPolygon", "coordinates": [] },
  "soil_summary": { "source_id": "gssurgo", "notes": "texture and hydrologic group once loaded" },
  "disclaimer": "CSB boundaries are not ownership parcels. This tool supports, and does not replace, farmer judgment.",
  "sources": ["CSB", "CDL", "gSSURGO"]
}
```

`19000`과 `CSB-EXAMPLE-0001`은 자리 표시자다. 실제 적재 후 예시 ID를 이 문서에 PR로 갱신한다. 카운티 FIPS는 지어내지 말고 AOI 확정 값을 쓴다.

### `GET /field/{id}/bare-periods`

응답 예:

```json
{
  "field_id": "CSB-EXAMPLE-0001",
  "periods": [
    {
      "start": "2024-11-05",
      "end": "2025-04-12",
      "bare_days": 158,
      "evidence": {
        "optical_dates": ["2024-11-08", "2025-03-20"],
        "cdl_year_label": { "2024": "corn", "2025": "soy" },
        "method": "ndvi_and_cdl",
        "gaps": ["cloud-masked dates omitted"]
      }
    }
  ],
  "sources": ["HLS", "CDL"]
}
```

### `GET /field/{id}/vulnerable-seasons`

응답 예:

```json
{
  "field_id": "CSB-EXAMPLE-0001",
  "period": { "start": "1991-01-01", "end": "2020-12-31" },
  "seasons": [
    {
      "season": "summer",
      "hazards": ["drought", "heat"],
      "precip_anomaly_mm": -42.0,
      "t2m_anomaly_c": 1.4,
      "smap_sm_anomaly": -0.8,
      "notes": "SMAP is a context-cell assignment, not a field-precise measurement."
    }
  ],
  "sources": [
    { "source_id": "power", "native_resolution": "see API metadata" },
    { "source_id": "imerg", "native_resolution": "nominal 0.1 deg" },
    { "source_id": "smap", "native_resolution": "nominal 36 km L3" }
  ]
}
```

### `POST /strategies/compare`

요청 예:

```json
{
  "field_id": "CSB-EXAMPLE-0001",
  "current_rotation": "C-S",
  "priorities": {
    "water": 0.3,
    "soil": 0.4,
    "stability": 0.2,
    "income": 0.1
  },
  "constraints": {
    "water_limited": false,
    "equipment": [],
    "market": []
  }
}
```

슬라이더 값은 0–1, 합이 1이 아니면 서버가 정규화하고 `priorities_normalized`를 돌려준다. **단일 최적해를 반환하지 않는다.**

응답 예:

```json
{
  "field_id": "CSB-EXAMPLE-0001",
  "priorities_normalized": { "water": 0.3, "soil": 0.4, "stability": 0.2, "income": 0.1 },
  "run_id": "demo-001",
  "unit": "index_0_1",
  "strategies": [
    {
      "strategy_code": "A",
      "label": "Baseline corn-soy",
      "why": "Current convention on this field.",
      "evidence": [{ "doi": null, "url": "https://power.larc.nasa.gov/", "quote": "Climate inputs from NASA POWER." }],
      "benefits": ["Matches existing equipment and markets"],
      "info_gaps": ["In-field soil test not provided"],
      "local_review_risks": ["Winter bare-ground erosion exposure"],
      "scores": {
        "n_cycle_index": 0.41,
        "erosion_index": 0.35,
        "organic_matter_index": 0.33,
        "pest_break_index": 0.30,
        "water_use_index": 0.55,
        "forage_index": 0.10,
        "market_index": 0.80
      },
      "p10": 0.32,
      "p50": 0.44,
      "p90": 0.51,
      "cvar": 0.29
    },
    { "strategy_code": "B", "label": "C-S + cereal rye cover" },
    { "strategy_code": "C", "label": "C-S-wheat or oats + cover" },
    {
      "strategy_code": "D",
      "label": "C-S-alfalfa",
      "local_review_risks": ["High water use is a material risk in western/irrigated settings and must be reviewed locally."]
    }
  ],
  "disclaimer": "Supportive comparison only. Not a single optimum. Not a substitute for farmer or agronomist judgment. Nitrogen figures, if any, are literature ranges pending a field soil test."
}
```

응답에는 전략을 **최소 3장, 기본 4장** 모두 포함한다. 카드 다섯 항목(why, evidence, benefits, info_gaps, local_review_risks)은 구현 시 생략 금지.

### `GET /validation/backtest`

질의 예: `/validation/backtest?field_id=CSB-EXAMPLE-0001&year=2012`

응답 예:

```json
{
  "field_id": "CSB-EXAMPLE-0001",
  "years": [2012],
  "county_yield_bu_ac": { "2012": null },
  "results": [
    {
      "strategy_code": "A",
      "year": 2012,
      "observed_sequence": "C-S",
      "notes": "County yield is optional (NASS bulk fallback if QuickStats API is unreachable). 2012 US drought is a candidate stress year.",
      "metrics": {}
    }
  ],
  "sources": ["CDL", "CSB"]
}
```

### `GET /maps/{field_id}/{layer}`

`layer` ∈ `erosion` | `water_stress` | `frost` | `ndvi_zones`.

응답 예 (GeoJSON FeatureCollection 또는 타일 URL):

```json
{
  "field_id": "CSB-EXAMPLE-0001",
  "layer": "water_stress",
  "crs": "EPSG:4326",
  "geojson": { "type": "FeatureCollection", "features": [] },
  "tile_url": null,
  "sources": ["SMAP", "POWER", "SRTM"],
  "notes": "SMAP-based water stress is displayed at context-cell resolution."
}
```

### `GET /evidence/search`

질의 예: `/evidence/search?q=cereal%20rye&strategy=B`

응답 예:

```json
{
  "query": "cereal rye",
  "strategy_code": "B",
  "hits": [
    {
      "source_title": "Managing Cover Crops Profitably",
      "doi": null,
      "url": "https://www.sare.org/resources/managing-cover-crops-profitably-3rd-edition/",
      "quote": "Short cited sentence only.",
      "license": "see source page"
    }
  ],
  "insufficient_evidence": false
}
```

DOI가 없는 공식 핸드북은 `url` 필수. 근거가 없으면 `insufficient_evidence: true` 이고 문장을 생성하지 않는다.

### 2026-11-15 08:20 추가 엔드포인트

화면 흐름은 [TEAM_SPEC.md](./TEAM_SPEC.md) 2절. 아래 예시의 숫자는 **자리 표시자**다.

#### `GET /locate?lat=&lon=`

```json
{
  "in_service_area": true,
  "field_id": "CSB-EXAMPLE-0001",
  "county_fips": "19169",
  "state_alpha": "IA",
  "area_ha": 28.47,
  "geometry": { "type": "MultiPolygon", "coordinates": [] },
  "message": null
}
```

서비스 지역 밖이면 `in_service_area: false`, `field_id: null`, `message: "Outside the service area."`

#### `GET /field/{id}/profile` 확장 필드

기존 응답에 아래 필드를 추가한다(모두 nullable, 없으면 `null`과 `info_gaps`에 이유).

```json
{
  "region_label": "Central Iowa, Corn Belt",
  "precip_mm_yr": 790.0,
  "et_mm_day": 4.2,
  "et0_mm_day": null,
  "ndvi_peak": 0.68,
  "ndvi_class": "good",
  "t2m_mean_c": 9.5,
  "cdl_history": [{ "year": 2025, "crop": "Corn" }, { "year": 2024, "crop": "Soybeans" }],
  "soil": { "om_pct": null, "k_factor": null, "awc_cm_cm": null },
  "vision": { "model_id": "ibm-nasa-geospatial/Prithvi-EO-1.0-100M-multi-temporal-crop-classification", "crop_pred": "Corn", "bare_fraction": null, "agreement_with_cdl": null },
  "hero_state": "normal",
  "period": { "start": "1991-01-01", "end": "2020-12-31" },
  "info_gaps": []
}
```

`ndvi_class` ∈ `good`·`fair`·`low`(임계값은 `calibration_param`). `hero_state` ∈ `normal`·`drought`·`wet`·`heat`·`frost`.

#### `POST /rotations/candidates`

```json
{
  "field_id": "CSB-EXAMPLE-0001",
  "current_rotation": "C-S",
  "selected_options": ["cover_rye", "small_grain"],
  "constraints": { "water_limited": false, "water_cap_mm": null, "equipment": [], "market": [] }
}
```

`selected_options` ⊂ {`cover_rye`, `small_grain`, `alfalfa`}, 길이 ≤ 3. 응답은 부분집합 2ⁿ개:

```json
{
  "field_id": "CSB-EXAMPLE-0001",
  "n_options": 2,
  "candidates": [
    { "candidate_id": "C-S", "strategy_code": "A", "sequence": "C-S", "options": [], "feasible": true, "warnings": [] },
    { "candidate_id": "C-S+cover_rye", "strategy_code": "B", "sequence": "C-S", "options": ["cover_rye"], "feasible": true, "warnings": [] },
    { "candidate_id": "C-S-W", "strategy_code": null, "sequence": "C-S-W", "options": ["small_grain"], "feasible": true, "warnings": [] },
    { "candidate_id": "C-S-W+cover_rye", "strategy_code": "C", "sequence": "C-S-W", "options": ["small_grain", "cover_rye"], "feasible": true, "warnings": [] }
  ]
}
```

#### `POST /strategies/compare` 확장 필드

요청에 `candidate_ids`(선택, 없으면 A–D)를 받을 수 있다. 응답의 각 전략에 아래를 추가한다.

```json
{
  "candidate_id": "C-S+cover_rye",
  "rank": 1,
  "goal_label": "Water saving",
  "display": {
    "vegetation_pct": { "p10": -2.0, "p50": 3.0, "p90": 7.0 },
    "water_use_pct": { "p10": -12.0, "p50": -6.0, "p90": 1.0 },
    "revenue_pct": { "p10": -5.0, "p50": 0.0, "p90": 4.0 },
    "basis": "relative index change vs strategy A; not a guarantee"
  },
  "pros": ["...", "...", "..."],
  "cons": ["..."],
  "unique_feature": "...",
  "weights_applied": { "water": 0.5, "soil": 0.3, "stability": 0.1, "income": 0.1 },
  "water_weight_boosted": false,
  "scenario_results": [
    { "horizon": "next_season", "source_id": "geos_s2s", "metric": "season_water_deficit_mm", "p10": null, "p50": null, "p90": null, "cvar": null },
    { "horizon": "2030s", "source_id": "nex_gddp", "scenario": "ssp245", "metric": "season_water_deficit_mm", "p10": null, "p50": null, "p90": null, "cvar": null }
  ]
}
```

`pros`는 정확히 3개, 탭끼리 같은 문장을 쓰지 않는다. `cons`는 1개 이상. 카드 5항목은 그대로 유지.

#### `GET /field/{id}/climate/history?years=5`

```json
{
  "field_id": "CSB-EXAMPLE-0001",
  "years": [
    { "year": 2025, "precip_mm": null, "et_mm": null, "ndvi_peak": null, "t2m_mean_c": null, "crop_cdl": "Corn", "naip_thumb_url": null }
  ],
  "sources": ["POWER", "IMERG", "NLDAS-2", "HLS", "CDL", "NAIP"]
}
```

`years` 최대 5, 최신 연도부터.

#### `GET /field/{id}/climate/outlook`

```json
{
  "field_id": "CSB-EXAMPLE-0001",
  "next_season": {
    "source_id": "geos_s2s", "init": "2026-11", "period": "2027-JJA",
    "pr_anomaly_pct": { "p10": null, "p50": null, "p90": null },
    "tas_anomaly_c": { "p10": null, "p50": null, "p90": null },
    "n_members": null, "native_resolution": "0.5 deg"
  },
  "mid_century": [
    { "source_id": "nex_gddp", "scenario": "ssp245", "period": "2031-2040", "baseline_period": "1985-2014",
      "pr_change_pct": { "min": null, "p50": null, "max": null }, "tasmax_change_c": { "min": null, "p50": null, "max": null }, "n_models": null }
  ],
  "label": "Possible ranges (scenarios), not a forecast of a single future.",
  "native_resolution_note": "Context-cell data (tens of km), not field-precise."
}
```

GEOS-S2S가 스파이크에서 실패하면 `next_season`은 `null`이고 `info_gaps`에 이유를 적는다.

#### `GET /glossary`

```json
{ "terms": [{ "term_id": "evapotranspiration", "ko": "증발산", "en": "Evapotranspiration", "short_ko": "...", "short_en": "...", "source_url": null }] }
```

#### `POST /explain`

요청 `{ "field_id", "candidate_id" | "strategy_code", "question", "lang": "ko" | "en" }`. 응답 `{ "answer", "tool_calls": [{ "endpoint", "json_paths_used": [] }], "citations": [{ "doi", "url" }], "insufficient_evidence": false }`. 숫자는 `tool_calls` 응답에 있는 것만.

#### `GET /sim/{field_id}/scene?strategy=`

복셀 시뮬용. 스키마는 [TEAM_SPEC.md](./TEAM_SPEC.md) 7.5의 `sim_scene.json` (`schema_version`, `field_id`, `strategy_code`, `grid`, `texture`, `frames[]`, `events[]`, `sources[]`). 정적 파일 `/data/processed/vN/sim/{field_id}_{strategy}.json`로 대체 가능.

### LLM 규칙

- 숫자는 위 엔드포인트 응답에 있는 것만 사용한다.
- RAG는 인용 문장과 DOI/URL 전용이다.
- 없는 값은 “정보 공백”이다. 추정 숫자를 채우지 않는다.
- 제공자 DeepSeek(OpenAI 호환, `https://api.deepseek.com`), 모델 id **`deepseek-flash`**(DeepSeek-V4.1-Flash, 2026-11-15 공식 문서 확인). 설정 변수 `LLM_API_KEY`·`LLM_BASE_URL`·`LLM_MODEL`.

---

## 7. 아직 비워 두는 값

- ~~아이오와 본편 카운티 이름과 `county_fips`~~ — **닫힘 (2026-11-15 11:10 KST):** Story County, `19169`, `IA`.
- 데모 `field_id` 실값, POWER 격자 해상도, CSB ID 컬럼명, 공개 API 베이스 URL. (임베딩 차원은 384로 확정, 5절)
- GEOS-S2S 압축 파일 내부 형식·변수명·리드 월 수, NEX-GDDP 사용 모델 3개 이름, Prithvi 체크포인트 로드 방식(mmseg vs terratorch), `ndvi_class`·`hero_state` 임계값, 후보 생성 규칙 최종안(TEAM_SPEC O1).

이 목록에 없는 숫자를 계약인 것처럼 추가하지 않는다.
