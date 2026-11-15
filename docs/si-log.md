# SI 사용 로그 (Use of AI)

제출서 Use of AI(SI) 항목의 원장이다. 코딩 에이전트, LLM API, 생성 이미지·영상을 쓴 날마다 한 줄 이상 적는다. SI로 **해법 아이디어 자체**를 만들지 않는다. 생성 그림·영상은 눈에 보이는 워터마크, NASA 로고·깃발·미션 표식 금지.

| 시각 (KST) | 누가 | 도구 | 범위 | 산출물에 고지했는가 |
| --- | --- | --- | --- | --- |
| 2026-11-15 08:00–10:00 | Hylē / 에이전트 | 코딩 어시스턴트 | PRD·SOT·체크리스트·협업 문서 동결, 이슈 초안 | 이 로그와 제출서에 기록 예정 |
| 2026-11-15 11:40 | Hylē / 에이전트 | 코딩 어시스턴트 | 라이브 현황판 재설계, STATUS 댓글 프로토콜, 모니터링 문서 | 이 로그와 대시보드 문서 |
| 2026-11-15 13:50 | Hylē / 엔진 레인 에이전트 | 코딩 어시스턴트 (Claude Code), DeepSeek API(`/explain` 런타임) | `model_api/` FastAPI·MC 물수지 엔진·테스트·fixture (#8) | 이 로그, `model_api/README.md` |
| 2026-11-15 15:30–17:00 | Hylē / 엔진 수정 레인 에이전트 | 코딩 어시스턴트 (Claude Code) | QA P1(E1·E3·E4) 근본 수정: 전략별 물수지, 필지 CDL 윤작·OpenET Kc 보정, IMERG 조건부 문구, NLDAS 맥락, 회귀 테스트 (`feat/engine-p1`) | 이 로그, `model_api/README.md` |
| 2026-11-15 14:40 | QA 레인 에이전트 | 코딩 어시스턴트 (Claude Code), DeepSeek API(`/explain` 1회 실호출) | 라이브 E2E 테스트, DB 점검 SQL, `docs/QA-REPORT.md` | 이 로그, `docs/QA-REPORT.md` |
| 2026-11-15 15:40–16:25 | Prithvi 레인 에이전트 | 코딩 어시스턴트 (Claude Code) | Prithvi-EO-1.0-100M 작물 분류 CPU 추론(순수 PyTorch forward, 미세조정 없음), HLS 3시점 칩 수집, vision_result 20필지 적재 (#28) | 이 로그, `docs/PRITHVI.md` |
| 2026-11-15 15:00–17:00 | contrast fields 레인 에이전트 | 코딩 어시스턴트 (Claude Code) | 대비 데모 필지 8개(McLean IL·Lancaster NE·Union OH) 적재 스크립트, `/fields` 카운티 라벨·Story 우선, 대비 테스트, `docs/CONTRAST-FIELDS.md` (`feat/contrast-fields`) | 이 로그, `docs/CONTRAST-FIELDS.md` |
| 2026-11-15 19:00–20:00 | L4 제출 레인 에이전트 | 코딩 어시스턴트 (Claude Code) | 제출 초안 `docs/submission/`(submission.md, data-links.md, si-use.md, slides, video-script). 숫자는 라이브 model_api·docs에서 가져옴 | 이 로그, `docs/submission/si-use.md` |
| 2026-11-15 19:00–19:40 | L1 web 레인 에이전트 | 코딩 어시스턴트 (Claude Code) | ART FARM 프론트엔드(목업 V8 영어화·Leaflet/Esri 지도·Tier 1/2 결과), `POST /quick` (V8 FAO-56 포팅, 디스크 캐시, 모의 HTTP 테스트), `infra/web` 읽기 전용 프록시·레이트 리밋·터널 (`feat/artfarm-web`) | 이 로그, `infra/web/README.md` |
| 2026-11-15 19:00 KST | L2 MATLAB pipeline / Codex | 코딩 어시스턴트 | 20필지 입력 내보내기, V8 비대화형 배치, MATLAB 분석 스켈레톤, 검증기·반복 스크립트 | `docs/MATLAB-VALIDATION.md`, `feat/matlab-pipeline` |
| 2026-11-15 19:43–20:15 KST | MATLAB-fix 레인 에이전트 | 코딩 어시스턴트 (Claude Code) | V8 배치 실패 원인 분석(USGS 8 s 타임아웃, Open-Meteo MRI_AGCM3_2_S ET0 전부 null), 서버 API 사전 수집 캐시 `data_pipeline/v8_prefetch.py`, V8 캐시 우선 읽기·ET0 정보 공백 처리, 4개 스크립트 old/<stamp> 보관 정책, MATLAB 정적 검사·Python 사전 검증 (`fix/matlab-scripts`) | 이 로그, `matlab/contrib/woochan/CHANGELOG.md` |
- 2026-11-15 20:25 KST · Claude Opus 5.5 (STATIC lane) · docs/demo static GitHub Pages copy + API fallback layer, tools/make_demo_snapshot.py, tools/test_static_demo.py (Playwright, live API blocked)
