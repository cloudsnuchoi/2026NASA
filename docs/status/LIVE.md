# 아몰라 실시간 현황 · 00:03 KST

일정: 1차 제출 21:00 (지남) · 동결 23:00 (지남) · 최종 제출 23:30 (지남)
최종 제출 23:30 KST까지 **0시간 0분** 남음. 팀 채팅: https://process-investigators-dean-unified.trycloudflare.com/ · 데모: https://watts-astrology-asus-blessed.trycloudflare.com

| 레인 | 진행 | 완료/전체 |
| --- | --- | --- |
| 데이터 | 100% | 11/11 |
| 엔진·API | 100% | 6/6 |
| AI 모델 | 100% | 5/5 |
| MATLAB | 93% | 14/15 |
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
- ✅ /explain (OpenAI) — 5.4 s, gpt-4o-mini

## MATLAB 93%
- ✅ 윤성 1차 CSV: drought_2012_county.csv
- ✅ 윤성 1차 CSV: climate_annual.csv
- ✅ 윤성 1차 CSV: calibration_params.csv
- ✅ woochan: v8_cards_20fields.csv + coefficients_sources.csv — ✅ 결과 파일 있음
- ✅ yoonsung: drought_compare_2012.png + drought_compare_2012_summary.csv — ✅ 결과 파일 있음
- ✅ jimin: baresoil_days_20fields.csv — ✅ 결과 파일 있음
- ✅ jieun: fig_p10p90.png + fig_backtest2012.png — ✅ 결과 파일 있음
- ✅ yoonsung 추가: yoonsung_nldas_2012 — nldas_vs_engine_2012.png
- ✅ yoonsung 추가: yoonsung_season_anomaly — season_anomaly_1995_2025.png
- ✅ yoonsung 추가: yoonsung_s2s_box — s2s_vs_history_box.png
- ✅ jimin 추가: jimin_growing_season — growing_season_20fields.csv
- ✅ jimin 추가: jimin_ndvi_anomaly — ndvi_anomaly.png
- ✅ jimin 추가: jimin_bare_vs_rye — bare_vs_strategyB.csv
- ✅ yoonsung 추가: yoonsung_nass_compare — nass_compare_2012.png
- 🟡 jieun 추가: jieun_slide_fig3 — fig3_yoonsung_extra.png

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
1. MATLAB: jieun 추가: jieun_slide_fig3

## AI 모델
- ✅ Prithvi 작물 분류 — crop_pred=Corn, agreement_with_cdl=0.19
- ✅ GEOS-S2S 다음 시즌 분포 — 앙상블 멤버 10
- ✅ NEX-GDDP 2030년대 — 모델 2개
- ✅ Monte Carlo·CVaR — 전략별 P50 {'B': 0.574, 'C': 0.556, 'D': 0.535, 'A': 0.494}
- ✅ /explain (OpenAI) — 5.4 s, gpt-4o-mini

## 에이전트 레인 (tmux)
| 세션 | 모델 | 하는 일 | 상태 | 기다리는 것 | 마지막 활동 |
| --- | --- | --- | --- | --- | --- |
| api | — | model_api 상시 실행 (:8090) | — | — | 23:39 |
| bot | DeepSeek Flash + Codex sol/terra + Claude | Mattermost 오케스트레이터 봇 | running | — | 21:20 |
| live | — | 이 현황 생성기 (5분) | — | — | 15:54 |
| mfixq | ? | ? | running | — | 19:53 |
| mm-tunnel | — | Mattermost Cloudflare 터널 | — | — | 12:11 |
| mwatch | ? | ? | running | — | 20:40 |
| rbatch | ? | ? | running | — | 21:00 |
| runner | — | GitHub Actions 러너 | — | — | 13:09 |
| web | — | 프론트+API 프록시 (:8095) | — | — | 21:56 |
| web-tunnel | — | 공개 데모 터널 | — | — | 19:00 |

## 레인 상태 (tmux 없음)
| 레인 | 상태 | 기다리는 것 |
| --- | --- | --- |
| fields2 | waiting-merge | main에 없는 커밋 5개 (감독 머지) |
| fix | waiting-merge | main에 없는 커밋 3개 (감독 머지) |
| imerg | waiting-merge | main에 없는 커밋 11개 (감독 머지) |
| l1 | done | — |
| l2 | done | — |
| l4 | done | — |
| l5 | done | — |
| nudge | blocked | 프로세스 없음·완료 표시 없음 |
| prd | waiting-merge | main에 없는 커밋 1개 (감독 머지) |
| prithvi | waiting-merge | main에 없는 커밋 1개 (감독 머지) |
| qa | waiting-merge | main에 없는 커밋 3개 (감독 머지) |
| site | waiting-merge | main에 없는 커밋 1개 (감독 머지) |

## 사람 (마지막 활동, KST)
| 이름 | Mattermost | 레포 |
| --- | --- | --- |
| 김우찬 | 22:40 | — |
| 김윤성 | 21:55 | — |
| 고지은 | 21:04 | — |
| 하지민 | 22:38 | — |
| 강다은 | 17:18 | — |
| Hylē | 16:01 | 23:54 |

## 최근 머지된 PR
- #89 i18n: 메인 앱, /demo/, Data & Sources 영어화(표시 문자열만)
- #88 docs(readme): 배너, 버튼, 히어로, 논문 썸네일, 파이프라인, 영어화
- #87 docs: 라이브 진입점(README 배지, /demo/ 배너), Project 칸 순서, USDA ERS 재추가
- #86 feat(explain): DeepSeek → OpenAI gpt-4o-mini (설명문만, 숫자는 엔진)
- #85 feat(landing): Research Paper 섹션, 제출서·README에 영상·논문 링크
- #84 docs(paper): ART FARM 해석 소논문(PDF, OpenAlex로 확인한 인용 40개)
- #83 fix(ui): 목업 V8 결과 대시보드를 라이브 #results에 그대로 이식(엔진 값 연결)
- #82 docs(matlab): 우찬 Kc ±10% 민감도 결과와 제출 문장 스니펫
