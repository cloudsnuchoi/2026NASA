# 아몰라 실시간 현황 · 20:27 KST

제출 목표 22:00 KST까지 **1시간 32분** 남음. 팀 채팅: https://process-investigators-dean-unified.trycloudflare.com/

| 레인 | 진행 | 완료/전체 |
| --- | --- | --- |
| 데이터 | 100% | 11/11 |
| 엔진·API | 100% | 6/6 |
| AI 모델 | 100% | 5/5 |
| MATLAB | 86% | 6/7 |
| UI | 100% | 7/7 |
| 인프라·봇 | 83% | 5/6 |

## 데이터 100%
- ✅ POWER 일별 12주 1995–2025
- ✅ CDL 카운티 작물 비율
- ✅ CSB 필지 경계
- ✅ SSURGO 필지 토양
- ✅ HLS NDVI 데모 필지
- ✅ SMAP L3 (맥락)
- ✅ NLDAS-2 월별
- ✅ IMERG 일별 2010–2025 (16개 연도) — 25개 연도 적재
- ✅ NEX-GDDP 2개 모델 이상 (API) — 2개 모델
- ✅ GEOS-S2S 다음 시즌 (API) — 멤버 10
- ✅ 대비 데모 필지 (3개 카운티 이상) — 데모 필지 20개, 4개 카운티

## 엔진·API 100%
- ✅ model_api 상시 실행
- ✅ Story 데모 필지 목록 /fields
- ✅ 전략 비교 MC·CVaR
- ✅ 2012 백테스트 전략별 차이 — 서로 다른 물 부족 값 4개
- ✅ 필지별 결과 차이 (A P50 범위 > 0.02) — A P50 범위 [0.447, 0.504]
- ✅ 공개 데모 배포 — https://watts-astrology-asus-blessed.trycloudflare.com

## AI 모델 100%
- ✅ Prithvi 작물 분류 — crop_pred=Corn, agreement_with_cdl=0.19
- ✅ GEOS-S2S 다음 시즌 분포 — 앙상블 멤버 10
- ✅ NEX-GDDP 2030년대 — 모델 2개
- ✅ Monte Carlo·CVaR — 전략별 P50 {'B': 0.574, 'C': 0.556, 'D': 0.535, 'A': 0.494}
- ✅ /explain (DeepSeek) — 7.7 s, deepseek-flash

## MATLAB 86%
- ✅ 윤성 1차 CSV: drought_2012_county.csv
- ✅ 윤성 1차 CSV: climate_annual.csv
- ✅ 윤성 1차 CSV: calibration_params.csv
- 🟡 woochan: v8_cards_20fields.csv + coefficients_sources.csv — 🟡 접속함·작업 중
- ✅ yoonsung: drought_compare_2012.png + drought_compare_2012_summary.csv — ✅ 결과 파일 있음
- ✅ jimin: baresoil_days_20fields.csv — ✅ 결과 파일 있음
- ✅ jieun: fig_p10p90.png + fig_backtest2012.png — ✅ 결과 파일 있음

## UI 100%
- ✅ frontend/ 코드 (main)
- ✅ 공개 데모 접속 200 (로그인 없음) — https://watts-astrology-asus-blessed.trycloudflare.com
- ✅ 공개 API /fields (20필지)
- ✅ 1층 /quick (screening estimate) — HTTP 200
- ✅ 2층 전략 비교 /strategies/compare — HTTP 200
- ✅ 화면 캡처 docs/screens
- ✅ 공개 URL QA (docs/QA-FINAL.md)

## 인프라·봇 83%
- ✅ Mattermost
- ✅ 봇 (tmux bot)
- ✅ 러너 (tmux runner)
- ✅ SSH 공개키 자동 등록 (keywatch) — root 프로세스로 확인
- 🟡 main CI 최근 성공
- ✅ live 현황 (tmux live)

## 막힌 점
- 없음

## 다음 할 일
1. MATLAB: woochan: v8_cards_20fields.csv + coefficients_sources.csv
2. 인프라·봇: main CI 최근 성공

## AI 모델
- ✅ Prithvi 작물 분류 — crop_pred=Corn, agreement_with_cdl=0.19
- ✅ GEOS-S2S 다음 시즌 분포 — 앙상블 멤버 10
- ✅ NEX-GDDP 2030년대 — 모델 2개
- ✅ Monte Carlo·CVaR — 전략별 P50 {'B': 0.574, 'C': 0.556, 'D': 0.535, 'A': 0.494}
- ✅ /explain (DeepSeek) — 7.7 s, deepseek-flash

## 에이전트 레인 (tmux)
| 세션 | 모델 | 하는 일 | 마지막 활동 |
| --- | --- | --- | --- |
| api | — | model_api 상시 실행 (:8090) | 19:27 |
| bot | DeepSeek Flash + Codex sol/terra + Claude | Mattermost 오케스트레이터 봇 | 19:52 |
| live | — | 이 현황 생성기 (5분) | 15:54 |
| mat2 | ? | ? | 20:17 |
| mfixq | ? | ? | 19:53 |
| mm-tunnel | — | Mattermost Cloudflare 터널 | 12:11 |
| runner | — | GitHub Actions 러너 | 13:09 |
| sub2 | ? | ? | 20:17 |
| ux | ? | ? | 20:17 |
| web | — | 프론트+API 프록시 (:8095) | 20:09 |
| web-tunnel | — | 공개 데모 터널 | 19:00 |

## 사람 (마지막 활동, KST)
| 이름 | Mattermost | 레포 |
| --- | --- | --- |
| 김우찬 | 20:26 | — |
| 김윤성 | 20:15 | — |
| 고지은 | 20:22 | — |
| 하지민 | 19:58 | — |
| 강다은 | 17:18 | — |
| Hylē | 16:01 | 20:10 |

## 최근 머지된 PR
- #61 docs(matlab): 가이드 경로를 work/로 + 실행만 하는 원칙
- #59 fix(matlab): V8 배치가 서버 API 캐시를 읽고 기존 결과를 보관 — 우찬님 USGS·Open-Meteo 오류 해결
- #60 fix(web): 공개 URL QA 수정 (경계 좌표, 결측을 0%로 표시하던 문제, 문구) + QA-FINAL
- #58 feat(web): AI 생성 이미지 표시(사진 워터마크 + 로고 푸터) · SI 내역 확정
- #57 fix: 테스트가 실제 수정 큐에 쓰던 문제 + live.json MATLAB 사람별 3단계 + 시뮬 Stretch
- #56 feat(orchestrator,matlab): MATLAB 오류 → 에이전트 자동 수정 큐 + 오늘 저녁 역할표
- #55 fix(status): UI 레인 진행률을 공개 데모 실동작 점검으로
- #53 docs(submission): 제출 초안 — 문구·데이터 링크·SI·슬라이드 7장·영상 대본
