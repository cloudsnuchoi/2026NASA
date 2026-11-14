# SOT · Source of Truth

팀 **아몰라** · `cloudsnuchoi/2026NASA`  
동결: **2026-11-15 08:00–10:00 Asia/Seoul (KST)**.

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
| USDA NASS QuickStats | USDA NASS, 공식07 | 연, 카운티/주 | API (`api_GET`, 키 필수, 요청당 최대 50,000행) 또는 웹 UI | 기타 (공식07) | NASS 인용. API 키는 환경 변수 |
| 피복·윤작 문헌 | SARE, Iowa State Extension, MCCC 등, **외부** | 해당 없음 (문서) | 공식 URL. 전문 PDF를 저장소에 올리지 않음 | 기타 (외부) | 각 문헌 저작권. 짧은 인용+DOI/URL만 RAG. Other Data·References |

### 1.2 강하게 권장 (시간 되는 대로)

| 이름 | 출처 | 해상도·주기 | 접근 | NASA 여부 | 라이선스·인용 |
| --- | --- | --- | --- | --- | --- |
| PRISM | Oregon State PRISM Climate Group, 공식07 | 일·월·30년. 무료 웹서비스 해상도 4 km 등 (문서 2025-03-26). 30년 평년은 웹서비스에 없고 별도 다운로드 | `services.nacse.org` 그리드 서비스 또는 FTP | 기타 (공식07) | PRISM 이용 약관 확인 후 인용 |
| OpenET | OpenET, 공식07 (탭은 미국 서부; 2025-12-16 발표로 인접 48주 래스터 확대). 아이오와 **필지 ID 서비스 개통은 미확인** | 통상 30 m ET, 2016~ (확대 발표 기준) | `POST https://openet-api.org/raster/timeseries/point` (API 키). 필지 경계 API는 이 주말 전제로 두지 않음 | 기타 (공식07) | OpenET 약관·키. 시간이 없으면 FAO-56만으로 물 비교 |
| ECOSTRESS | NASA/JPL, 공식07 | 통상 약 70 m (탭/문서 불일치 가능, 제품 메타데이터 따름) | Earthdata / JPL / AppEEARS | NASA | 제품 DOI·인용. 공백은 「관측 없음」 |
| USDA 가격 lite / RMA Cause of Loss | USDA AMS/ERS/RMA, 주로 **외부** 또는 QuickStats 일부 | 연·카운티/주 등 | QuickStats, ERS, RMA 공개 표 | 기타 | 인용 + Other Data. 본편 목적함수로 쓰지 않음 |

### 1.3 이번 주말 후순위 (본편에서 빼도 됨)

GAEZ, GRACE/GRACE-FO, NAIP, NLCD, LANDFIRE, GEDI, VIIRS, ERA5, NLDAS 등. 쓰면 출처와 NASA/기타를 구분해 제출서에 적는다. GRACE는 유역 맥락만, 필지 값 금지.

### 1.4 접근 주의

- SMAP·GRACE를 필지 정밀 관측처럼 쓰지 않는다.
- POWER 격자는 API 메타데이터를 따른다.
- CDL 웹서비스는 호출 전에 생존을 확인한다. 클래스 코드를 추측하지 않는다.
- 미국 전용 자료를 한국 필지에 붙이지 않는다.
- 비밀값(Earthdata, QuickStats, OpenET 등)은 환경 변수만.

---

## 2. 정규 ID, 단위, 좌표계

| 항목 | 규칙 |
| --- | --- |
| `field_id` | **CSB 고유 식별자.** 적재 시 CSB 속성 테이블의 공식 컬럼명을 확인해 그대로 쓴다. 컬럼명을 여기서 지어내지 않는다. 문자열로 저장. |
| `county_fips` | 5자리 문자 (주 2 + 카운티 3). 아이오와 본편 AOI 키. |
| `state_alpha` | `IA` (본편), 선택 확장 시 `NE`. |
| `strategy_code` | `A` \| `B` \| `C` \| `D` (PRD 4절). |
| `year` | 작물 연도 정수. CDL 연 라벨과 맞출 때는 CDL 연도를 따름. |
| `date` | 저장은 ISO 8601 날짜(`YYYY-MM-DD`). 시각이 있으면 UTC. 화면의 현지 달력은 `America/Chicago`. |
| 저장 CRS | **EPSG:4326** (경위도, WGS84). `geometry`는 GeoJSON도 4326. 경도·위도 순서 주의(GeoJSON은 lon, lat). |
| 분석 투영 | **EPSG:5070** (NAD83 Conus Albers). 면적·거리·리샘플은 여기서 계산한 뒤 저장은 4326으로 되돌린다. |
| 온도 | °C (`t2m_c`, `tmin_c`, `tmax_c`) |
| 강수·ET·ETo | mm (`precip_mm`, `et0_mm`, `etc_mm`) |
| 토양수분 | 제품 원단위를 컬럼 주석에 기록. 표시·모델에는 **평년 대비 아노말리**를 우선 (`smap_sm_anomaly`, 무차원 또는 제품 단위 차). 필지 평균인 척하지 않음. |
| NDVI 등 식생지수 | 무차원 (`ndvi`). 유효 범위는 제품 정의. |
| 면적 | ha (`area_ha`). 에이커가 필요하면 표시 직전에만 변환하고 필드명을 `area_ac`로 구분. |
| 수량 (QuickStats 옥수수) | `bu/ac` (`yield_bu_ac`). 리터/ha로 바꾸지 말고, 단위를 응답에 포함. |
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
  /power/ /imerg/ /smap/ /hls/ /landsat/ /srtm/ /cdl/ /csb/ /ssurgo/ /quickstats/ /prism/ ...
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

MATLAB 출력 파일명 예: `/data/processed/v1/matlab/field_dekad_anomaly.parquet`. 컬럼은 이 문서의 단위·ID를 따른다.

---

## 5. DB 스키마 (초안 DDL)

서비스 DB: **Postgres 16 + PostGIS + pgvector**. 협업 도구(Mattermost 등)와 **데이터베이스를 분리**한다. 분석 중간 테이블은 Parquet + DuckDB도 허용하나, API가 읽는 값은 아래 테이블(또는 이와 동등한 뷰)에 있어야 한다.

임베딩 차원은 사용하는 모델에 맞춰 한 숫자로 고정하고, 그 숫자를 이 절 또는 이슈에 기록한다. 아래는 예시로 `vector(1536)`을 썼다.

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
  embedding       vector(1536)               -- 모델 확정 후 차원 고정
);

-- 주말 안에 임베딩이 실패하면 embedding 을 비우고 키워드 검색만 한다.
CREATE INDEX evidence_chunk_t_idx ON evidence_chunk
  USING GIN (to_tsvector('simple', coalesce(quote, '') || ' ' || coalesce(source_title, '')));
```

맵 레이어는 사전 계산한 GeoJSON/COG를 객체 스토리지 또는 `/data/processed/vN/maps/`에 두고, 메타만 DB에 둘 수 있다.

---

## 6. API 계약 (OpenAPI 스타일)

베이스 URL은 배포 후 `infra/`에 적는다. 데모 **인증 없음** (제출: 로그인 없는 링크). 내부 운영 키가 필요하면 게이트웨이에만 두고, 심사 링크는 공개한다.

공통 오류:

```json
{ "error": { "code": "not_found", "message": "Unknown field_id" } }
```

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
  "county_fips": "19000",
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
      "notes": "County yield filled when QuickStats is loaded. 2012 US drought is a candidate stress year.",
      "metrics": {}
    }
  ],
  "sources": ["CDL", "CSB", "QuickStats"]
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

### LLM 규칙

- 숫자는 위 엔드포인트 응답에 있는 것만 사용한다.
- RAG는 인용 문장과 DOI/URL 전용이다.
- 없는 값은 “정보 공백”이다. 추정 숫자를 채우지 않는다.

---

## 7. 아직 비워 두는 값

- 아이오와 본편 **카운티 이름과 `county_fips`** — 동결 창 이슈로 닫고 이 절을 PR로 갱신한다.
- 데모 `field_id` 실값, POWER 격자 해상도, CSB ID 컬럼명, 임베딩 차원, 공개 API 베이스 URL.

이 목록에 없는 숫자를 계약인 것처럼 추가하지 않는다.
