# 아몰라 실시간 현황 · 21:44 KST

일정: 1차 제출 21:00 (지남) · 동결 23:00 (1시간 15분 남음) · 최종 제출 23:30 (1시간 45분 남음)
최종 제출 23:30 KST까지 **1시간 45분** 남음. 팀 채팅: https://process-investigators-dean-unified.trycloudflare.com/ · 데모: https://watts-astrology-asus-blessed.trycloudflare.com

| 레인 | 진행 | 완료/전체 |
| --- | --- | --- |
| 데이터 | 100% | 11/11 |
| 엔진·API | 100% | 6/6 |
| AI 모델 | 100% | 5/5 |
| MATLAB | 86% | 6/7 |
| UI | 100% | 7/7 |
| 인프라·봇 | 100% | 6/6 |

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
- ✅ /explain (DeepSeek) — 5.8 s, deepseek-flash

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

## 인프라·봇 100%
- ✅ Mattermost
- ✅ 봇 (tmux bot)
- ✅ 러너 (tmux runner)
- ✅ SSH 공개키 자동 등록 (keywatch) — root 프로세스로 확인
- ✅ main CI 최근 성공 — success
- ✅ live 현황 (tmux live)

## 막힌 점
- 없음

## 다음 할 일
1. MATLAB: woochan: v8_cards_20fields.csv + coefficients_sources.csv

## AI 모델
- ✅ Prithvi 작물 분류 — crop_pred=Corn, agreement_with_cdl=0.19
- ✅ GEOS-S2S 다음 시즌 분포 — 앙상블 멤버 10
- ✅ NEX-GDDP 2030년대 — 모델 2개
- ✅ Monte Carlo·CVaR — 전략별 P50 {'B': 0.574, 'C': 0.556, 'D': 0.535, 'A': 0.494}
- ✅ /explain (DeepSeek) — 5.8 s, deepseek-flash

## 에이전트 레인 (tmux)
| 세션 | 모델 | 하는 일 | 마지막 활동 |
| --- | --- | --- | --- |
| api | — | model_api 상시 실행 (:8090) | 19:27 |
| bot | DeepSeek Flash + Codex sol/terra + Claude | Mattermost 오케스트레이터 봇 | 21:20 |
| live | — | 이 현황 생성기 (5분) | 15:54 |
| mfixq | ? | ? | 19:53 |
| mm-tunnel | — | Mattermost Cloudflare 터널 | 12:11 |
| mwatch | ? | ? | 20:40 |
| rbatch | ? | ? | 21:00 |
| runner | — | GitHub Actions 러너 | 13:09 |
| sub2 | ? | ? | 20:17 |
| web | — | 프론트+API 프록시 (:8095) | 20:09 |
| web-tunnel | — | 공개 데모 터널 | 19:00 |

## 사람 (마지막 활동, KST)
| 이름 | Mattermost | 레포 |
| --- | --- | --- |
| 김우찬 | 21:10 | — |
| 김윤성 | 21:04 | — |
| 고지은 | 21:04 | — |
| 하지민 | 20:45 | — |
| 강다은 | 17:18 | — |
| Hylē | 16:01 | 21:16 |

## 최근 머지된 PR
- #74 docs(matlab): 가이드 Run 하나로 정리 + live.json 추가 세트 6개
- #73 fix(bot): MATLAB 방 캡처 요구 금지 규칙
- #71 feat(matlab): 서버 봇 직접 안내(notify.log), 레인 상태, MATLAB 결과 30분 배치
- #72 fix(ui): 모바일 360/390/768 점검과 UX-AUDIT 수정
- #70 feat(matlab): run_all_<name>.m 원클릭 실행과 JSON 실행 로그, mwatch 자동 수정
- #69 docs(site): 모델 상태 정리, Data & Sources 패널, MATLAB 빌드 단계 결과
- #68 docs: 강다은 데모 영상 역할 + MATLAB UX 진단표
- #65 docs(submission): 제출 패키지 v1 (역할·Project 링크·MATLAB 검증 문단)
