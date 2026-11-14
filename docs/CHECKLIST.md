# 해커톤 체크리스트 · 2026-11-15 (Asia/Seoul, KST)

팀 **아몰라** · 저장소 [cloudsnuchoi/2026NASA](https://github.com/cloudsnuchoi/2026NASA)  
마감 **2026-11-15 23:59 KST** (권장 제출 완료 **23:55**). 이 문서의 시각은 모두 **Asia/Seoul (KST)** 이다.

제품·데이터·API의 고정본은 [PRD.md](./PRD.md), [SOT.md](./SOT.md)다. 결정은 [DECISIONS.md](./DECISIONS.md)에만 추가한다. 작업 항목은 GitHub Issues다.

---

> **2026-11-15 08:20 KST 추가.** 09:00–11:00 데이터 검증 스파이크, 11:00 기능 잠금, 14:00·17:00 통합 체크포인트, 역할별 인계 계약은 [TEAM_SPEC.md](./TEAM_SPEC.md) 6·7·10절을 따른다. 시간 블록은 이 문서와 같다.

## 0. 운영 원칙 (16시간)

1. **아이디어는 이미 확정됐다.** 챌린지 07의 결정(기존 윤작에 무엇을 더하거나 바꿀지)과 전략 A–D, 아이오와 본편은 다시 논쟁하지 않는다. 남은 시간은 구현·검증·제출이다.
2. **순서는 “데이터 전체 분석 → 그다음 설계”가 아니다.** 설계(PRD·SOT·스키마·API)를 먼저 고정하고, 데이터 다운로드·EDA는 **그와 동시에** 한다. 프론트·API는 계약과 스텁으로 병렬 착수하고, 가공 테이블이 나오는 대로 교체한다.
3. **이번 주말 엔진은 규칙·지수 스코어링 + 몬테카를로 + CVaR** 이다. 강화학습·미세조정은 하지 않는다. WOFOST·Prithvi·네브래스카·경제 심화는 시간이 남을 때만, 아래 컷 순서를 따른다.
4. **MATLAB은 라이브 파이프라인에 넣지 않는다.** 오프라인 분석·캘리브레이션만 하고, 결과는 CSV/Parquet로보내 DB에 적재한다.
5. **한 저장소, 한 DB, 한 API 계약.** 여섯 대의 노트북은 `feat/<이슈번호>-slug` 브랜치와 PR로만 합친다. 원본 데이터는 VPS의 `/data/raw`(불변)에만 둔다.
6. **진행 현황은 GitHub Issues + Project 보드**다. 매시 10분 싱크(아래). 대기업 IT의 최소형: 이슈 = 작업 단위, 보드 = 라이브 대시보드, PR = 코드 리뷰, SOT = 인터페이스 계약.

**컷 순서 (시간이 없으면 앞에서부터 자른다):** Prithvi 미세조정 → 네브래스카 비교 → 경제 심화 → OpenET(FAO-56만 유지) → 광학 전 시계열(CDL 연 라벨로 맨땅 근사) → pgvector(키워드+DOI 테이블로 대체).

**그래도 남기는 최소 산출:** 현재 윤작 포함 전략 3–4장 비교, 이유·근거·이점·정보 공백·현지 검토 위험, 맨땅/취약 계절, 불확실성(분포 또는 CVaR), NASA 데이터 출처, 로그인 없는 웹 프로토타입.

---

## 1. 08:00–10:00 · 동결 (Freeze)

목표: 팀 전원이 같은 계약으로 갈라져 작업할 수 있게 한다.

- [ ] [PRD.md](./PRD.md) 확정 (문제, 사용자, 결정, 전략, 범위, 성공 기준, 데모)
- [ ] [SOT.md](./SOT.md) 확정 (데이터 표, ID/단위/CRS, 집계, 디렉터리, DB 스키마, API 계약)
- [ ] [DECISIONS.md](./DECISIONS.md)에 오늘 아침 동결을 기록
- [ ] [AGENTS.md](../AGENTS.md), [CONTRIBUTING.md](../CONTRIBUTING.md)를 각 노트북의 Codex CLI / agy CLI 컨텍스트로 지정
- [ ] 아이오와 본편 **카운티 이름**을 정하고 SOT·이슈에 반영 (미정이면 다운로드 AOI만 임시 FIPS로 고정하고 이름을 빈칸으로 두지 말 것)
- [ ] VPS 접속 정보·데이터 경로·DB URL은 환경 변수로만 공유 (저장소에 비밀값 금지)
- [ ] GitHub 라벨·이슈·보드가 열려 있고, 각자 맡을 이슈를 고른다 (계정 할당은 선택)

**통과 기준:** 스키마와 API 예시 JSON을 바꾸려면 이슈+PR이 필요하다. 이후 임의 변경 금지.

---

## 2. 08:00–11:00 · 데이터 다운로드와 EDA (VPS, 동결과 병렬)

담당 중심: 강다은 (다운로드·ETL), 하지민 (시계열 EDA), 김우찬 (문헌·작물 특성 테이블).

- [ ] Earthdata / QuickStats / (쓰면) OpenET 키가 VPS 환경 변수로만 설정됨
- [ ] 필수 NASA: POWER, GPM IMERG, SMAP(맥락 칸), Landsat 또는 HLS, SRTM — AOI 클립만 `/data/raw/`에 저장
- [ ] 필수 기타: CDL, CSB, SSURGO/gSSURGO, QuickStats, 피복·윤작 문헌 목록
- [ ] 권장(시간 되면): PRISM, OpenET 포인트, ECOSTRESS
- [ ] 원본은 `/data/raw`에 **불변** 보관. 체크섬·출처·라이선스를 `data_pipeline/` 매니페스트에 기록
- [ ] 가공은 `/data/processed/v1` (이후 버전은 `v2`…). Git에는 경로와 스크립트만
- [ ] 필지 ID = CSB ID로 `fields` 뼈대 적재
- [ ] EDA: 맨땅 구간, 수분·강수·기온 아노말리, 2012 가뭄 창이 데이터에 보이는지
- [ ] SMAP·GRACE를 필지 정밀 값처럼 쓰지 않았는지 확인

이 창이 밀려도 11:00에 API·프론트 스텁 작업은 시작한다.

---

## 3. 11:00–18:00 · 병렬 구축

각자 **이슈 범위만** 변경한다. 매시 10분 싱크.

| 영역 | 주요 산출 | 제안 담당 |
| --- | --- | --- |
| `data_pipeline/` | 조화, QA, `field_season`, Parquet → Postgres | 강다은 |
| `model_api/` | 규칙·지수, MC+CVaR, FastAPI 계약 구현 | 강다은, Hylē |
| `model_api/` 백테스트 | CDL/CSB 이력 대조 | 강다은, 김윤성 |
| `rag/` | 근거 카드, `/evidence/search`, LLM 도구호출 | 김우찬, Hylē |
| `frontend/` | 지도, 슬라이더, 전략 카드, 맨땅·취약 계절 | 고지은, 하지민 |
| `matlab/` | 오프라인 평활·아노말리 → CSV | 하지민 |
| `infra/` | Compose, Postgres+PostGIS+pgvector, 공개 배포 | Hylē |
| 작물 특성 테이블 | FAO-56 Kc, 질소·피복 문헌 범위 | 김우찬 |
| P1 (여유 시) | 구역화·파레토, N 처방 애드온 | 김윤성 |

- [ ] `GET /health`, `GET /field/{id}/profile` 가 스텁 또는 실데이터로 응답
- [ ] `GET /field/{id}/bare-periods`, `/vulnerable-seasons` 응답
- [ ] `POST /strategies/compare` 가 전략 4장(또는 최소 3장)을 단일 최적해 없이 반환
- [ ] `GET /validation/backtest` 최소 구현
- [ ] `GET /evidence/search` (임베딩 실패 시 키워드+DOI 테이블)
- [ ] `GET /maps/{field_id}/{layer}` 또는 사전 계산 GeoJSON
- [ ] UI: 우선순위 슬라이더, 카드(이유·근거·이점·공백·위험), “지원 도구이며 판단을 대체하지 않음”
- [ ] LLM은 FastAPI 숫자만 tool-call. 숫자를 생성·수정하지 않음
- [ ] 단위 테스트 또는 계약 테스트(예시 JSON 스키마) 최소치
- [ ] `docs/si-log.md`에 사용한 SI를 그날그날 기록

---

## 4. 18:00–20:00 · 기능 동결과 E2E

- [ ] 18:00 **기능 동결.** 새 기능 금지. 버그·카피·성능만.
- [ ] 로그인 없이 데모 URL이 열린다 (로컬호스트만으로 제출 금지)
- [ ] 아이오와 필지 1개로 데모 시나리오(PRD)를 처음부터 끝까지 클릭
- [ ] 카드 숫자와 API 응답이 일치한다. LLM 문장에 API에 없는 숫자가 없다
- [ ] 맨땅 기간, 취약 계절, 불확실성(P10/P50/P90 또는 CVaR)이 화면에 보인다
- [ ] NASA 데이터 출처가 UI 또는 프로젝트 페이지에 명시된다
- [ ] 알팔파(전략 D)의 물 사용 위험이 카드에 적혀 있다
- [ ] CSB는 소유 경계가 아님을 UI에 적는다
- [ ] 비밀값·원본 래스터가 저장소에 없는지 확인

---

## 5. 20:00–23:30 · 제출물

제출 페이지는 **영어**. 데모가 한국어면 **영어 자막**. 슬라이드는 영어.

- [ ] 데모: **영상 30초 이하** 또는 **표지·소개 포함 슬라이드 7장 이하** (둘 중 하나 이상, 한도를 넘기면 글로벌 심사 제외)
- [ ] 프로젝트 페이지 이미지(쓸 경우)는 JPG·PNG·GIF, **각 10MB 이하** (페이지에 영상·문서 파일 업로드 불가)
- [ ] README 최종 (구조, 실행 방법, 데이터 출처, 라이선스)
- [ ] References: 사용 데이터·문헌·소프트웨어 **라이선스와 인용** 포함
- [ ] 제출서 **NASA Data**에 사용한 NASA 데이터/자원 **최소 1개** (권장: POWER + IMERG 또는 SMAP 또는 Landsat/HLS)
- [ ] 제출서 **Space Agency Partner & Other Data**: CSB, SSURGO, QuickStats, PRISM, 문헌 등 Resources 밖·파트너 자료
- [ ] 제출서 **Use of AI (SI)**: 사용 범위, 가속 도구임을 명시. SI가 만든 그림·영상은 워터마크. NASA 로고·깃발·미션 표식 사용·변조 금지
- [ ] Summary, Project Details, Project Demonstration URL, Project URL 초안 완성
- [ ] **모든 링크가 로그인·비밀번호·가입 없이 열린다** (GitHub 공개 저장소, 공개 데모, YouTube/Drive 등 링크 권한 확인)
- [ ] 팀원 전원 Members 탭·동일 지역 등록 확인 (최종)

**23:30–23:55:** 업로드, 링크 클릭 검수, 제출 버튼. **23:59를 넘기지 않는다.**

---

## 6. Space Apps 제출 요건 (공식 체크)

출처: 2026 Project Submission Guide, Judging & Awards Guide, 서울 안내. 원문과 다르면 원문 우선.

- [ ] 프로젝트 페이지 하나로 제출 (영어)
- [ ] 항목: Summary, Project Demonstration(URL), Project(URL), Project Details, Use of AI(SI), NASA Data 링크, Space Agency Partner & Other Data 링크
- [ ] 데모 한도: 슬라이드 7장 이하(표지 포함) **또는** 영상 30초 이하
- [ ] 페이지 이미지 형식·용량 준수
- [ ] 링크는 로그인 없이 열림
- [ ] 글로벌 어워드를 노리면 NASA 데이터 또는 자원 ≥ 1
- [ ] SI로 해법 아이디어 자체를 만들지 않음. 제출서에 사용 방법 기술
- [ ] 만 18세 미만의 얼굴·목소리·이름 등 식별 정보 없음
- [ ] 사전 작업 규칙(11/14 09:00 KST 이전 제작물 제출 금지)을 위반하지 않음

**심사 5기준 (각 1–5):** Impact, Creativity, Validity, Relevance, Presentation. 우리 설계는 Impact를 먼저 보고, Relevance(NASA 데이터가 핵심)와 Validity(동작·불확실성·백테스트)를 그 다음에 본다. Presentation(30초/7장에 필지 하나와 전략 카드)을 마지막에 절대 희생하지 않는다.

---

## 7. 매시 싱크 (10분)

시각 예: 11:00, 12:00, …, 18:00, 이후 30분 간격 가능.

각자가 한 줄로: (1) 닫을 이슈 / (2) 막힌 점 / (3) 다음 한 시간 목표. 보드 Status를 그 자리에서 옮긴다. 상세는 [CONTRIBUTING.md](../CONTRIBUTING.md).
