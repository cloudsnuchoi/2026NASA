# PRD · ART FARM

**ART FARM** — *Field Shift: Adapting Farms with NASA Data*

팀 **아몰라** · NASA Space Apps Challenge 2026 · 챌린지 07 *Field Shift: Adapting Farms with NASA Data*  
**최종 동결: 2026-11-15 18:57 Asia/Seoul (KST)** (Hylē 최종 지시). 이전 동결 08:00–10:00, 갱신 11:10. 이 문서를 바꾸려면 이슈와 PR이 필요하다.  
데이터·스키마·API의 단일 원본은 [SOT.md](./SOT.md)다. 화면 흐름·역할·인계 계약은 [TEAM_SPEC.md](./TEAM_SPEC.md). 구조는 [ARCHITECTURE.md](./ARCHITECTURE.md). 결정 기록은 [DECISIONS.md](./DECISIONS.md).

> **18:57 KST 최종 동결 요약.** 제품 이름은 **ART FARM**, 부제 *Field Shift: Adapting Farms with NASA Data*. 화면은 **두 단계(Tier)** 다. **Tier 1 Quick Screen**은 콘벨트 어디서나 네 꼭짓점을 찍어 FAO-56 식으로 **선별 추정(screening estimate)** 을 보여 주고, **Tier 2 Deep Analysis**는 그 다각형이 우리 데모 필지 20개 중 하나와 겹칠 때 엔진(model_api)의 전략 A–D 카드를 보여 준다. 순위·「추천」·보장 문구는 쓰지 않는다. 출처 없는 숫자는 지운다.

표기 규칙: **[구현됨]** = 2026-11-15 18:57 KST 기준 저장소·VPS에서 동작 확인. **[계획]** = 계약은 정했으나 아직 동작하지 않음. 표시가 없으면 원칙·규칙이다.

---

## 0. 이름

- 제품 이름: **ART FARM** (로고·사이트·프론트·제출·슬라이드 모두 같은 이름).
- 부제: **"Field Shift: Adapting Farms with NASA Data"**.
- 챌린지 이름 *Field Shift*는 부제와 챌린지 표기로만 쓴다. NASA 로고·깃발·미션 표식은 쓰지 않는다.

---

## 1. 문제

콘벨트 옥수수–대두 농가는 기온·강수 변동, 수분 스트레스, 침식, 양분 고갈, 병해충 순환에 노출되어 있다. 관행의 2년 옥수수–대두(C–S) 윤작은 해당 작물 면적의 절반을 넘지만(ERS 2013; 그보다 새로운 공식 전국 수치는 미확인), 겨울 맨땅 구간이 길고 다양성이 낮다.

한 시즌의 윤작·피복 선택은 **되돌리기 어렵고** 흙·물·다음 수확에 닿는다. 위성은 맨땅, 수분·열·강수 아노말리, 취약 계절처럼 지상만으로는 빈칸인 신호를 메운다. 농가에 필요한 것은 “정답을 대신 정하는 AI”가 아니라, NASA 지구관측과 현지 토양·작물 특성을 들어 **선택지를 비교하고 불확실성을 드러내는 지원 도구**다.

공식 소개 영상의 문장: *Compare rotations, reveal trade-offs, understand risk, make uncertainty visible.*

---

## 2. 사용자와 공간

**사용자.** 미국 콘벨트 옥수수–대두 농가, 그리고 그 판단을 돕는 현지 농업 전문가.

**공간 = 두 단계.**

| 단계 | 어디서 | 무엇으로 |
| --- | --- | --- |
| **Tier 1 Quick Screen** | 콘벨트 어디서나 (12개 주 `IA, IL, IN, OH, NE, MN, SD, WI, MO, KS, MI, KY`) | 사용자가 그린 네 꼭짓점 다각형 + NASA POWER 10년 + USGS 3DEP 고도 + FAO-56/FAO-33 식 |
| **Tier 2 Deep Analysis** | 데모 필지 **20개, 4개 카운티**: Story IA(`19169`) 12, McLean IL(`17113`) 3, Lancaster NE(`31109`) 3, Union OH(`39159`) 2 | model_api 엔진: MC 물수지·CVaR, 2012 가뭄 백테스트, Prithvi/CDL, `/explain` |

다각형이 데모 필지와 겹치지 않으면 Tier 1 결과만 보여 주고 “**Deep analysis available in 4 pilot counties**”를 띄운다. 목업의 원형 구역 대신 4개 카운티 데모 필지 위치(Iowa, Illinois, Nebraska, Ohio) **프리셋**을 둔다.

**비사용자.** 한국 필지, 스마트팜·온실·자율 수확 운영자, 시비량을 자동 확정하려는 시스템. 이 제품의 화면은 농부 판단을 **대체하지 않는다**.

---

## 3. 돕는 결정

기존 윤작에 **어떤 작물을 추가하거나 바꿔야** 토양 건강을 개선하고, 날씨·물 변화에 대한 회복력을 높일 수 있는가.

도구는 패턴과 가능성을 보여 준다. 단일 최적 수익해나 “이 작물을 심으라”는 명령을 내지 않는다. 카드마다 정보 공백과 **현지 검토가 필요한 위험**을 남긴다.

---

## 4. 정직성 규칙 (동결)

1. **보장·추천 문구 금지.** “Recommended”, “best”, “guaranteed”, 1위 배지, 순위 정렬을 쓰지 않는다. 카드 순서는 열거 순서일 뿐이다.
2. **출처 없는 숫자 금지.** 화면의 숫자는 (a) 이름 있는 데이터셋, (b) 공개 문헌 표(FAO-56, FAO-33 등), (c) 출처·연도를 단 **assumption** 중 하나여야 한다. 셋 다 아니면 지우고 “information gap”으로 둔다. 가짜 대체값(fallback)을 채우지 않는다.
3. **Tier 1 라벨.** Tier 1의 모든 결과에 “**screening estimate**” 라벨을 붙인다. 엔진 표기는 “**FAO-56 engine (ported from team MATLAB prototype V8)**”이다. 결과 화면에 “MATLAB engine”이라고 쓰지 않는다.
4. **경제 가정.** 목업 `CROP_DB`의 가격·수량·비용은 **assumption** 라벨과 USDA ERS/NASS 출처·연도를 함께 표시한다. 출처·연도를 확인하지 못한 값은 표시하지 않고 정보 공백으로 둔다.
5. **작물계수.** Kc는 FAO-56 Table 12 값으로 바꾼다(옥수수 Kc_mid 1.20, 대두 1.15, 밀 1.15. ini/end도 같은 표). 목업 값(예: 옥수수 1.08)을 남기면 툴팁에 FAO-56 표 값과의 차이를 보인다. Ky는 FAO-33 표를 출처로 단다. 표와 대조하지 못한 값은 “unverified” 표시.
6. **상대 지수.** “Water saving %”, “soil organic matter index” 등 %·지수에는 “relative index — vs. baseline, not a guarantee” 툴팁을 단다. Tier 2의 %에는 P10–P90을 함께 보인다.
7. **미래는 분포만.** 결정론적 다년 예보 값을 만들지 않는다. 미래 분포는 Tier 2(GEOS-S2S, NEX-GDDP-CMIP6)에서만 보인다.
8. **해상도.** SMAP·GRACE 등 거친 자료를 필지 정밀 값처럼 보이지 않는다.
9. **판단 대체 안 함.** “This tool does not replace farmer judgment.” 문구와 현지 검토 체크리스트를 숨기지 않는다.
10. **MATLAB V8에서 옮기지 않는 것.** 작물 배분 최적화(단일 최적해), 수익 하한값 고정(`max(40, …)` 류), NDVI 상한 고정처럼 출처 없는 보정은 Tier 1에 옮기지 않는다. V8의 NOAA/NWS·Open-Meteo 미래 호출은 Tier 1에 쓰지 않는다(비 NASA 단일 모델 → 분포 규칙 위반).

---

## 5. Tier 1 · Quick Screen

**[계획]** 계약은 [SOT.md](./SOT.md) 6.0절 `POST /quick`. 구현은 진행 중이며, 이 문서 동결 시점에 model_api에는 아직 없다.

1. 사용자가 콘벨트 지도(위성 베이스맵)에서 **네 꼭짓점**을 클릭한다(또는 4개 카운티 프리셋을 고른다).
2. 작물 **2–3개**를 고른다: Corn, Soybean, Wheat. 같은 작물이 연속하는 윤작은 만들지 않는다.
3. 계산: 다각형 면적·둘레(WGS84), USGS 3DEP 꼭짓점 고도, NASA POWER 과거 10년(2016–2025) 일별 기후, FAO-56 작물 물수요(Kc × ET0)와 FAO-33 수량 반응(Ky). 팀 MATLAB V8 수식을 JS/Python으로 옮긴 것이다.
4. 출력: 윤작 카드마다 `screening estimate` 라벨, 지표(상대 지수 표시), **info_gaps**, 출처를 단 **assumptions**. **순위 없음.**
5. 다각형이 데모 필지와 겹치면 Tier 2로 들어가는 버튼을, 아니면 “Deep analysis available in 4 pilot counties”를 보인다.

---

## 6. Tier 2 · Deep Analysis

### 6.1 비교 전략 (4개)

| 코드 | 윤작 | 역할 |
| --- | --- | --- |
| `A` | 기준 옥수수–대두 (`C-S`) | 현재/관행 |
| `B` | `C-S` + 겨울 호밀(cereal rye) 피복 | 맨땅 단축, 침식·피복. 본작 순서는 유지 |
| `C` | `C-S`–밀 또는 귀리 + 피복 | 주작 다양화, 병해충 순환 차단 후보 |
| `D` | `C-S`–알팔파 | **참고(reference) 카드.** 사료 가치, 질소 고정, 심근. 서부·관개 지역에서는 물 사용 위험이 큼 → 카드에 명시 |

**선택 작물과 강조.** Corn+Soy → `A`, `B` 강조. Wheat를 더하면 `C`도 강조. `D`(알팔파)는 항상 참고 카드. 강조는 “선택과 맞음” 표시일 뿐 추천이 아니다.

### 6.2 카드 내용

- 카드 다섯 항목: **why, evidence, benefits, info_gaps, local_review_risks** (생략 금지).
- 기준 A 대비 상대 지수와 **P10 / P50 / P90**, 하위 10 % **CVaR**.
- 맨땅 기간, 취약 계절, 과거 연도별 기후, 미래 분포(다음 시즌 GEOS-S2S, 2030년대 NEX-GDDP-CMIP6).
- 2012 가뭄 백테스트(전략별 물 부족 차이).
- Prithvi 작물 분류 결과와 CDL 일치도.
- `/explain`: LLM이 엔진 응답의 숫자만 인용해 설명.

유기물·질소의 **확정 kg**, 병해충 **손실액**은 자동 수치화하지 않는다. 질소는 문헌 범위 + 「현장 토양검정 후 확정」.

---

## 7. 오늘 구현된 것 (2026-11-15 18:57 KST)

| 항목 | 상태 | 근거 |
| --- | --- | --- |
| 데모 필지 20개, 4개 카운티 (Story IA 12, McLean IL 3, Lancaster NE 3, Union OH 2), CSB 2018–2025 경계 | **[구현됨]** | `GET /fields` total=20 |
| NASA POWER 일별 12주 1995–2025, GPM IMERG 일별, NLDAS-2 월별, SMAP L3(맥락), HLS NDVI(데모 필지), CDL, SSURGO | **[구현됨]** 적재 | `docs/status/live.json` 데이터 레인 |
| GEOS-S2S 다음 시즌 앙상블(멤버 10), NEX-GDDP-CMIP6 2030년대(모델 2개) | **[구현됨]** 적재 | live.json |
| Prithvi-EO-1.0-100M multi-temporal crop classification **추론**(미세조정 없음, CPU) → `vision_result`, 20개 필지 전부 | **[구현됨]** | `GET /field/{id}/profile` |
| 몬테카를로 물수지 + P10/P50/P90 + CVaR(하위 10 %), 전략 A–D | **[구현됨]** | `POST /strategies/compare`, `POST /simulate` |
| 2012 가뭄 백테스트 (전략별 물 부족 차이) | **[구현됨]** | `GET /validation/backtest?field_id=` |
| `/explain` (DeepSeek, tool 응답 숫자만) | **[구현됨]** | `POST /explain` |
| model_api 상시 실행 (FastAPI, 읽기 전용 DB) | **[구현됨]** VPS 내부 | `GET /health` |
| Tier 1 `POST /quick` | **[계획]** | SOT 6.0 계약만 |
| 프론트엔드(ART FARM UI, 위성 베이스맵, 프리셋) | **[계획]** 진행 중 | 이슈 #12–#14 |
| 공개 데모 배포 | **[계획]** 진행 중 | 이슈 #15 |
| 복셀 시뮬(three.js) | **[계획]** | 이슈 #30 |
| MATLAB 오프라인 산출 중 `field_dekad`, `field_season` | **[계획]** 진행 중 | live.json MATLAB 레인 |
| RAG(pgvector) 근거 검색 | 엔드포인트 `GET /evidence/search`는 있음. 말뭉치 범위 **미확인** | — |

---

## 8. 범위

### 8.1 한다 (In)

- 로그인 없는 웹: Tier 1 Quick Screen + Tier 2 Deep Analysis
- **AI 4층**: (1) 비전 — Prithvi 추론만(실패 시 CDL) (2) 예측·시나리오 — GEOS-S2S, NEX-GDDP-CMIP6 (3) 시뮬레이션 — MC 물수지 + CVaR + 규칙·지수 (4) LLM 설명 — tool-call + RAG(인용 전용)
- FastAPI 모델 서비스([SOT.md](./SOT.md) 계약), Postgres + PostGIS + pgvector
- 오프라인 MATLAB 분석·캘리브레이션(산출 테이블만 DB로). MATLAB V8 수식은 Tier 1 엔진으로 **이식**하며, MATLAB 런타임은 요청 경로에 없다
- 영어 데모·제출 페이지, SI 고지, References·라이선스

### 8.2 하지 않는다 (Out)

- 강화학습, 기반 모델 미세조정, Prithvi 미세조정
- 결정론적 다년 기후 예보 표시
- 순위, 「추천」, 단일 최적해, 수익 극대화 목적함수
- MATLAB / WOFOST를 요청 경로의 라이브 계산으로 삽입
- 별도 벡터 DB, WeatherNext 본편 의존
- SMAP·GRACE를 필지 정밀 관측처럼 표시
- SI가 작물 지식이나 숫자를 지어내는 것
- NASA 로고·깃발·미션 표식 사용

---

## 9. 성공 기준

1. 공개 URL이 **로그인 없이** 열린다.
2. Tier 1: 콘벨트 임의 위치에서 네 꼭짓점 → 작물 2–3개 → `screening estimate` 카드(정보 공백·출처 단 가정 포함). 순위 없음.
3. Tier 2: 데모 필지 하나에서 전략 A–D 카드(다섯 항목), P10–P90·CVaR, 2012 백테스트, Prithvi/CDL, `/explain`이 끝까지 동작한다.
4. 비교에 쓰인 핵심 숫자가 **이름 있는 NASA 산출물**에서 온다(POWER, IMERG, NLDAS-2, HLS, GEOS-S2S, NEX-GDDP-CMIP6).
5. 도구가 판단을 대체하지 않는다고 명시된다.
6. 제출 목표 **22:00 KST**.

---

## 10. 데모 시나리오 (영어 발표 뼈대)

1. ART FARM 첫 화면: “This is a decision-support tool. It does not replace farmer judgment.”
2. **Tier 1**: 콘벨트 아무 곳에 네 꼭짓점 → Corn+Soy(+Wheat) → screening estimate 카드. 가정의 출처와 정보 공백을 보인다.
3. Iowa 프리셋(Story County 데모 필지) → **Tier 2**: 전략 A–D 카드, A·B(·C) 강조, D는 참고 카드이며 물 사용 위험을 숨기지 않는다.
4. P10/P50/P90·CVaR로 불확실성, 2012 가뭄 백테스트로 타당성.
5. `/explain`으로 엔진 숫자만 인용한 설명.
6. 닫는 문장: 농가가 현지 전문가와 함께 고를 수 있게, 빈칸과 위험을 남긴다.

---

## 11. 컷 순서

1. 복셀 시뮬 → 데모 영상에서 빼기
2. RAG 근거 → 키워드 + DOI 테이블
3. Tier 1 미래 패널 (이미 없음, 유지)
4. Tier 1 경제 가정 → 출처 확인 안 되면 카드에서 경제 줄을 빼고 정보 공백
5. Tier 2 프리셋 중 IL·OH (Iowa·Nebraska 유지)

섹션 4 정직성 규칙과 섹션 9의 1·3·5번은 포기하지 않는다.
