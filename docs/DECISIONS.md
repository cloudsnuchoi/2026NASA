# 결정 로그 (Decision Log)

팀 **아몰라** · NASA Space Apps 2026 · 07 Field Shift.  
시각은 **Asia/Seoul (KST)**. 새로운 팀 결정만 여기에 추가한다. 제품의 현재 상태는 [PRD.md](./PRD.md), 데이터·API는 [SOT.md](./SOT.md)가 우선이다.

표기: `결정` / `정정` / `동결` / `열림`.

---

## 2026-11-14

- **결정.** 챌린지 **07 Field Shift: Adapting Farms with NASA Data** 로 참가한다. 팀명 **아몰라**, 인원 6명(Hylē, 강다은, 김윤성, 하지민, 고지은, 김우찬). 서울 로컬, 작업 시간 11/14 09:00–11/15 23:59 KST.
- **결정.** 제품의 중심은 **윤작 전략 비교 의사결정 지원**이다. 스마트팜·온실·자율 수확은 본편이 될 수 없다. 윤작과 직접 연결된 애드온만 허용한다.
- **결정.** 애드온 하나: 전략별 질소 수지 → 구역별 드론 변량시비 **처방 지도**. 시비량은 문헌 범위만, 문구는 「현장 토양검정 후 확정」. 자동 확정 kg/ha 금지.
- **결정.** 학습·미세조정·강화학습은 이번 주말 본편에서 하지 않는다. 시간이 남아도 RL은 넣지 않고, 미세조정(Prithvi 등)은 컷 1순위다.
- **결정.** MATLAB은 시계열 평활(Savitzky–Golay 등), 계절·추세 분해, 이상 탐지에 쓴다. 웹에는 CSV·파라미터만 넘기거나 Python으로 이식한다.
- **결정 (22:36, 파이프라인 문서).** 맨땅·취약 계절·MC·CVaR·백테스트·침식·물 지도는 벡터 검색이 아니라 계산이다. RAG + pgvector는 근거 카드에만. LLM은 FastAPI 모델 API를 tool-call 한다. 별도 Pinecone/Milvus는 띄우지 않는다. DB는 Postgres + PostGIS + pgvector. 앱 스키마와 협업 도구 DB는 분리한다.

---

## 2026-11-15 03:50

- **정정.** 수익 극대화·질소 처방을 본편 목적함수로 두었던 초안을 **폐기**하고, 챌린지 07 원문의 결정으로 되돌린다. “기존 윤작에 어떤 작물을 추가·변경해 토양 건강과 기상·수자원 회복력을 높일까.”
- **결정.** 대상은 콘벨트 옥수수–대두 농가. 본편은 아이오와 카운티 1곳(빗물). 네브래스카는 물 제약 대비를 위한 선택 확장.
- **결정.** 비교 전략 4개: (A) 기준 C–S, (B) C–S + 겨울 호밀 피복, (C) C–S–밀/귀리 + 피복, (D) C–S–알팔파(서부에서 물 사용 위험을 카드에 명시).
- **결정.** MC + CVaR = 회복력. CDL/CSB 백테스트 = 검증. 경제·가격·RMA = 시장 적합성의 옆축. 드론 N 처방 지도는 애드온만.
- **결정.** 자르는 순서: Prithvi 미세조정 → 네브래스카 비교 → 경제 심화 (이어서 OpenET, 광학 전 시계열, pgvector).
- **열림.** 아이오와 카운티 이름, 코워크스페이스 VPS 사양·도메인, 새 프레이밍 기준의 역할 미세 조정. (저장소 이름은 이후 아침에 닫힘.)

---

## 2026-11-15 오전 (저장소)

- **결정.** 공개 GitHub 저장소 이름은 **2026NASA**, 조직/소유자 `cloudsnuchoi`. URL: https://github.com/cloudsnuchoi/2026NASA . 라이선스는 **Apache-2.0**. 비공개로 두지 않는다.
- **열림.** 협업자 초대: GitHub 아이디가 확인된 인원만 API로 초대됨. 나머지 세 명(하지민, qlenfnfn으로 보이는 강다은, 김윤성)은 아이디 수령 또는 본인 초대 대기. 이 작업에서 추가 초대는 하지 않는다.

---

## 2026-11-15 08:00–10:00 · 기준 동결

- **동결.** [PRD.md](./PRD.md), [SOT.md](./SOT.md), 체크리스트, 협업 규칙(AGENTS.md, CONTRIBUTING.md)을 저장소에 고정한다. 이후 계약 변경은 이슈+PR.
- **결정 (16시간 제약).** 라이브 엔진은 **규칙·지수 스코어링 + 몬테카를로 + CVaR** 다. 강화학습·미세조정 없음. WOFOST 7.2는 라이브 경로의 전제가 아니며, 시간이 남으면 오프라인 보정 입력으로만 쓴다.
- **결정.** MATLAB은 라이브 파이프라인에 들어가지 않는다. 오프라인 분석·캘리브레이션의 출력 테이블만 DB에 적재한다.
- **결정.** 저장 CRS는 **EPSG:4326**. 분석 투영은 주말 기본값으로 **EPSG:5070** (NAD83 Conus Albers). 필지 식별자는 **CSB ID** (`field_id`).
- **결정.** 원본 데이터는 VPS `/data/raw`(불변), 가공은 `/data/processed/vN`. 원본 래스터·비밀값은 Git에 커밋하지 않는다.
- **결정.** 6인 협업 운영: 이슈 → `feat/<이슈번호>-slug` 브랜치 → PR → 리뷰 1명 → squash merge. 매시 10분 싱크. 진행 현황은 GitHub Issues와 (권한이 되면) Project 보드.
- **열림.** 아이오와 카운티 이름(다운로드 AOI). 동결 창에서 이슈로 닫을 것.

---

## 2026-11-15 08:20 · 팀 명세(TEAM_SPEC) 고정

근거 문서: [TEAM_SPEC.md](./TEAM_SPEC.md). 입력: 팀 아이디에이션·UIUX·디자인 PDF(14쪽), 챌린지 07 원문.

- **정정.** 「주제가 정해졌다」는 이전 표현은 과했다. 아이디에이션은 **완전히 잠기지 않았다.** 잠긴 것은 둘뿐이다. (1) 대상: 콘벨트 옥수수–대두 농가, **아이오와 또는 일리노이** 카운티 1곳 (2) 결정: 토양 건강과 날씨·물 회복력을 위해 기존 윤작에 무엇을 추가·변경할지. 기능 세트는 **09:00–11:00 데이터 검증 스파이크**(TEAM_SPEC 6절)로 확인하고 11:00에 잠근다.
- **결정.** 팀 PDF의 화면 흐름을 기본안으로 채택: 지도 핀 → 필지 프로필(위치·면적·기온·강수·증발산·식생지수·CDL 이전 작물) → 작물 선택(최대 2, 확장 3) → 2ⁿ 후보 → 탭 4개(기준 A 대비 식생·물·수익 %, 장점 3·단점, 고유 특징, 물 제한 시 물 가중) → 탭 상세(과거 1–5년, 미래 분포) → 용어 설명 → 사람 판단 리마인더. 후보 생성 규칙 최종안은 열림(O1).
- **결정 (미래 기후).** 3년 결정론적 예보를 보여 주지 않는다. 시나리오 **분포**로 보여 준다. 다음 시즌 = NASA **GEOS-S2S-3** 계절 예보(NCCS datashare `geos-s2s-3/NRT/`, 0.5°). 2030년대 = NASA **NEX-GDDP-CMIP6**(`s3://nex-gddp-cmip6/`, THREDDS, 0.25°, CC0). **WeatherNext**(Google DeepMind, 15일 중기)는 작업 창 애드온 **선택**으로만 둔다 — 접근 신청 승인 5–7 영업일이라 마감 전 사용 불가 가능성이 크다.
- **결정 (비전).** Prithvi는 **추론만**, 미세조정 없음. 작물·맨땅 인식용, 실패 시 CDL 라벨.
- **정정 (비전 체크포인트 사실 확인).** Hugging Face `ibm-nasa-geospatial`에 **Prithvi-EO-2.0 작물 분류 미세조정 공개본은 없다**(2.0은 사전학습 백본과 Sen1Floods11·BurnScars 미세조정본뿐). 미세조정 금지를 지키기 위해 공개 작물 분류 체크포인트 **`ibm-nasa-geospatial/Prithvi-EO-1.0-100M-multi-temporal-crop-classification`**(HLS+CDL, 13클래스, Apache-2.0, 카드 mIoU 0.4269)으로 추론한다. 정확도가 낮으므로 화면에서는 보조 인식이고 기준은 CDL.
- **결정 (AI 4층).** 비전 인식 → 예측·시나리오 → 시뮬레이션(몬테카를로 물수지 + CVaR, 규칙·지수 점수) → LLM 설명(모델 API tool-call) + RAG(pgvector, 인용 전용). RL·미세조정 없음.
- **결정 (데이터 승격).** NLDAS-2(공식07 #16)와 NAIP(#14)를 P0로 승격. 공식 Resources는 **27행**(Resources 24항목·링크 26개 + Details의 GRACE/GRACE-FO)으로 관리한다.
- **결정 (역할 슬롯).** MATLAB 데이터 처리·분석 2명(오프라인만, 고정 스키마 CSV/Parquet → Postgres), three.js/HTML 복셀 시뮬 1명(데모 영상), UI/UX 2명, Hylē = 오케스트레이터·PM. 이름 배정은 제안만(TEAM_SPEC 7.1).
- **열림 (백엔드 공백).** 모델 API·DB 적재·MC·LLM/RAG 통합·배포 담당이 슬롯에 없다. 안 A(권장): 강다은(Python 백엔드·데이터·AI·MC 경험)이 백엔드. 안 B: Hylē + 에이전트가 소유. Hylē가 09:00 전 결정.
- **결정 (협업 도구).** 6명 모두 각자 노트북에서 Codex CLI + Gemini CLI(agy)를 GitHub에 연결해 쓴다. Codex는 `AGENTS.md`, Gemini는 `GEMINI.md`(→ `AGENTS.md` 가져옴)를 읽는다.
- **결정 (오케스트레이션).** GitHub = 유일한 상태. 무거운 중앙 오케스트레이터 에이전트는 만들지 않는다. 30–60분마다 읽기 전용 모니터링 다이제스트(`infra/monitor/digest.sh` 또는 NASA 봇)로 지연·막힘·리뷰 대기를 본다.

## 2026-11-15 09:30 · 역할 확정, 채팅·오케스트레이터·CI 운영

- **결정 (역할).** MATLAB A 김윤성, MATLAB B 김우찬, UI/UX A 고지은, UI/UX B 하지민, 복셀 시뮬·데모 영상 강다은(확인 필요), Hylē = 풀스택(백엔드 공백 안 B) + 총괄. TEAM_SPEC 7.1·7.2 갱신.
- **결정 (소통).** VPS에 Mattermost Team Edition 12.0.2 + Postgres를 띄운다(`infra/chat/`, 127.0.0.1만 열고 Cloudflare quick tunnel로 노출). 팀 `amolla`. 공개 채널: 공지(announce), uiux-design, demo-video, ppt-slides, data-matlab, backend, sim-voxel, random. 비공개 `1on1-<이름>` = 팀원 + Hylē + orchestrator 봇.
- **결정 (오케스트레이터).** 08:20의 「무거운 중앙 에이전트 없음」을 바꾼다. 팀원이 git·Codex 초보라서 1:1 지시가 필요하기 때문이다. 대신 작게 만든다. `infra/orchestrator/bridge.py`가 웹소켓으로 1on1과 멘션을 받고, LLM(OpenAI 호환)에 저장소 문서와 GitHub 읽기 전용 상태를 넣어 "다음 할 일, 붙여 넣을 프롬프트, 완료 기준"을 답한다. Hylē의 글이 우선한다. 봇은 GitHub에 쓰지 않는다. Mattermost 공식 Agents 플러그인은 무라이선스 등급에서 채널 에이전트와 원격 MCP가 막혀 있어 보조(옵션 A)로만 둔다.
- **결정 (git 운영).** 팀원은 git 명령 대신 `docs/PROMPTS.md`의 **마무리 블록**을 에이전트에 붙인다. MATLAB 담당은 git을 쓰지 않고, Hylē가 커밋한다. main은 PR 필수(승인 0, admin 우회), 머지는 Hylē만 한다. CI는 self-hosted 러너(`[self-hosted, linux]`)에서 돌리고, 포크 PR은 실행하지 않는다. 러너 등록 뒤 `ci-ok`를 필수 체크로 더한다.

---

## 2026-11-15 11:10 · 공간 두 층, QuickStats 선택, 아키텍처·대시보드

- **동결 (본편 카운티).** 2층 정밀 분석의 본편 카운티는 아이오와 **Story County**, `county_fips=19169`, `state_alpha=IA`. 이전 「아이오와 또는 일리노이 중 스파이크로 선택」을 여기서 닫는다. 네브래스카 대비는 그대로 P1·컷 가능.
- **결정 (데이터 두 층).** 콘벨트 **전체를 다루되 해상도를 나눈다.**
  - **1층 (넓게):** 콘벨트 12개 주 (`IA, IL, IN, OH, NE, MN, SD, WI, MO, KS, MI, KY`)를 **카운티 집계**로 받는다. NASA POWER(카운티 중심점), GPM IMERG, SMAP L3/L4(맥락 칸 평균), CDL 카운티 작물 비율, NEX-GDDP-CMIP6 카운티 평균. 어느 카운티든 1차 위험·윤작 힌트를 보여 준다.
  - **2층 (깊게):** Story County만 필지 30 m — CDL 래스터, CSB, SSURGO, HLS NDVI, GEOS-S2S. 몬테카를로·백테스트의 본편 검증 장소다. 30 m를 콘벨트 전체에 받지 않는다.
- **결정 (QuickStats).** USDA NASS QuickStats API 사이트(`quickstats.nass.usda.gov`)는 2026-11-15 팀에서 **접속 자체가 되지 않았다.** 카운티 수량은 시장 적합성의 **옆축·보조**이므로 QuickStats를 **선택(optional)** 으로 낮춘다. 본편 성공 기준과 go/no-go에서 수량 API를 빼다.
- **결정 (NASS 일괄 파일 대체, 확인함).** QuickStats 대신 [NASS Large Datasets](https://www.nass.usda.gov/datasets/) 일괄 파일을 먼저 시도한다. 2026-11-15 11:10 KST 확인: `https://www.nass.usda.gov/datasets/` 는 `http://www-origin.nass.usda.gov/datasets` 로 301된 뒤 origin이 **HTTP 500**. 목록·파일은 **`https://sb.nass.usda.gov/datasets/`** 에서 HTTP 200. 작물 파일 `qs.crops_20261103.txt.gz` 는 HTTP 200, `Content-Length=1132568713`, `Last-Modified=2026-11-03 08:14 UTC` (17:14 KST), 키 없음. 콘벨트 12주·카운티·옥수수/대두·연 수량만 필터한다. 이 경로도 실패하면 수량 열을 생략하고 CDL/CSB 백테스트만 남긴다.
- **결정 (문서·현황판).** 시스템 그림의 원본은 [ARCHITECTURE.md](./ARCHITECTURE.md) (전체 구조, 빌드 파이프라인, 서비스 파이프라인, 의사결정 모델, 협업 흐름, AI 4층·알고리즘). 진행 현황은 `docs/dashboard/` 정적 페이지가 공개 레포 GitHub REST API를 비인증으로 읽어 표시하고, GitHub Pages(`main`의 `/docs`)로 연다.
- **확인 (역할).** Hylē = 풀스택·오케스트레이터. MATLAB = 김윤성, 김우찬. UI/UX = 고지은, 하지민. three.js 복셀 시뮬 = 강다은. VPS 서버 에이전트가 Postgres 17 + PostGIS + pgvector + pg_trgm (`/srv/hackathon`)으로 적재 중. crawl4ai는 RAG 근거 문서용이며 P0 다운로드 다음이다.

## 2026-11-15 11:40 · 라이브 현황판·STATUS 댓글

- **결정 (상태 프로토콜).** 팀원(또는 그 사람의 Codex/agy)은 이슈에 고정 형식의 `STATUS:` 댓글을 남긴다. 시작·막힘·완료 때와 최소 30분마다. 첫 줄은 `STATUS: 🟢 진행 중` 또는 `🔴 막힘` / `🟡 리뷰 대기` / `✅ 완료`, 이어서 `작업:`, `진행률: NN%`, 선택으로 `막힌 점:`, `다음:`. 형식은 [PROMPTS.md](./PROMPTS.md) 0.1절, [AGENTS.md](../AGENTS.md), [ONBOARDING.md](./ONBOARDING.md).
- **결정 (현황판).** [dashboard](./dashboard/index.html)는 팀원 카드(현재 작업, 상태, 진행률, 이슈, 상대 시각, 30/60분 지연 경고, 열린 PR)를 맨 위에 두고, 마감 카운트다운·체크리스트 구간, 영역 진행률, PR 대기열, 최근 활동을 보여 준다. 이슈 댓글 API(`since`, 최신순, `per_page=100`)와 localStorage 캐시로 비인증 한도(60/시간) 안에서 2분마다 갱신한다. 선택 토큰은 브라우저 localStorage에만 저장한다.
- **결정 (GitHub 로그인 매핑).** `cloudsnuchoi` = Hylē, `ssbb215356` = 김윤성, `flyingbear-code` = 김우찬, `jieun-Ribby` = 고지은, `hahah383` = 하지민, `kangdaeun2005` = 강다은. 대시보드 `LOGIN_MAP` 한 곳에서만 고친다.
- **결정 (30분 점검).** Hylē/봇의 30분 레포 점검은 `STATUS:` 댓글을 읽어 막힘·지연·리뷰 대기를 보고한다.
