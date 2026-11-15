# 아몰라 실시간 현황 · 16:31 KST

제출 목표 22:00 KST까지 **5시간 28분** 남음. 팀 채팅: https://process-investigators-dean-unified.trycloudflare.com/

| 레인 | 진행 | 완료/전체 |
| --- | --- | --- |
| 데이터 | 100% | 11/11 |
| 엔진·API | 83% | 5/6 |
| AI 모델 | 100% | 5/5 |
| MATLAB | 50% | 3/6 |
| UI | 0% | 0/5 |
| 시뮬 | 0% | 0/2 |
| 인프라·봇 | 83% | 5/6 |

## 데이터 100%
- ✅ POWER 일별 12주 1995–2025
- ✅ CDL 카운티 작물 비율
- ✅ CSB 필지 경계
- ✅ SSURGO 필지 토양
- ✅ HLS NDVI 데모 필지
- ✅ SMAP L3 (맥락)
- ✅ NLDAS-2 월별
- ✅ IMERG 일별 2010–2025 (16개 연도) — 24개 연도 적재
- ✅ NEX-GDDP 2개 모델 이상 (API) — 2개 모델
- ✅ GEOS-S2S 다음 시즌 (API) — 멤버 10
- ✅ 대비 데모 필지 (3개 카운티 이상) — 데모 필지 20개, 4개 카운티

## 엔진·API 83%
- ✅ model_api 상시 실행
- ✅ Story 데모 필지 목록 /fields
- ✅ 전략 비교 MC·CVaR
- ✅ 2012 백테스트 전략별 차이 — 서로 다른 물 부족 값 4개
- ✅ 필지별 결과 차이 (A P50 범위 > 0.02) — A P50 범위 [0.447, 0.504]
- 🟡 공개 데모 배포 (#15)

## AI 모델 100%
- ✅ Prithvi 작물 분류 — crop_pred=Soybeans, agreement_with_cdl=0.95
- ✅ GEOS-S2S 다음 시즌 분포 — 앙상블 멤버 10
- ✅ NEX-GDDP 2030년대 — 모델 2개
- ✅ Monte Carlo·CVaR — 전략별 P50 {'B': 0.584, 'C': 0.569, 'D': 0.533, 'A': 0.484}
- ✅ /explain (DeepSeek) — 6.1 s, deepseek-flash

## MATLAB 50%
- 🟡 coefficients.csv
- 🟡 field_dekad.csv
- 🟡 field_season.csv
- ✅ drought_2012_county.csv
- ✅ climate_annual.csv
- ✅ calibration_params.csv

## UI 0%
- 🟡 frontend/package.json
- 🟡 S0–S3 (#12)
- 🟡 S4 전략 탭 (#13)
- 🟡 S5–S7 (#14)
- 🟡 공개 배포 (#15)

## 시뮬 0%
- 🟡 sim/ 코드
- 🟡 복셀 시뮬 (#30)

## 인프라·봇 83%
- ✅ Mattermost
- ✅ 봇 (tmux bot)
- ✅ 러너 (tmux runner)
- ✅ SSH 공개키 자동 등록 (keywatch) — root 프로세스로 확인
- 🟡 main CI 최근 성공 — 기록 없음
- ✅ live 현황 (tmux live)

## 막힌 점
- 없음

## 다음 할 일
1. MATLAB: coefficients.csv
2. MATLAB: field_dekad.csv
3. MATLAB: field_season.csv

## AI 모델
- ✅ Prithvi 작물 분류 — crop_pred=Soybeans, agreement_with_cdl=0.95
- ✅ GEOS-S2S 다음 시즌 분포 — 앙상블 멤버 10
- ✅ NEX-GDDP 2030년대 — 모델 2개
- ✅ Monte Carlo·CVaR — 전략별 P50 {'B': 0.584, 'C': 0.569, 'D': 0.533, 'A': 0.484}
- ✅ /explain (DeepSeek) — 6.1 s, deepseek-flash

## 에이전트 레인 (tmux)
| 세션 | 모델 | 하는 일 | 마지막 활동 |
| --- | --- | --- | --- |
| api | — | model_api 상시 실행 (:8090) | 15:50 |
| bot | DeepSeek Flash + Codex sol/terra + Claude | Mattermost 오케스트레이터 봇 | 16:01 |
| imerg | claude-sonnet-5-5 | IMERG·NLDAS-2 카운티 적재 | 13:59 |
| live | — | 이 현황 생성기 (5분) | 15:54 |
| mm-tunnel | — | Mattermost Cloudflare 터널 | 12:11 |
| prithvi | claude-opus-5-5 | Prithvi 작물 분류 추론 | 15:42 |
| runner | — | GitHub Actions 러너 | 13:09 |

## 사람 (마지막 활동, KST)
| 이름 | Mattermost | 레포 |
| --- | --- | --- |
| 김우찬 | 15:09 | — |
| 김윤성 | 16:15 | — |
| 고지은 | 15:50 | — |
| 하지민 | 14:56 | — |
| 강다은 | 13:47 | — |
| Hylē | 16:01 | — |

## 최근 머지된 PR
