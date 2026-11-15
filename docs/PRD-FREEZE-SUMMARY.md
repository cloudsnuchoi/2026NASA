# PRD 최종 동결 요약 (2026-11-15 18:57 KST) · 디자인 채널용

- 이름: **ART FARM**, 부제 **"Field Shift: Adapting Farms with NASA Data"**. 로고·사이트·슬라이드·제출 모두 이 이름, 화면 문구는 전부 영어.
- **Tier 1 Quick Screen**: 콘벨트 어디서나 네 꼭짓점 + 작물 2–3개(Corn/Soy/Wheat, 같은 작물 연속 금지). NASA POWER 10년 + USGS 3DEP + FAO-56/FAO-33. 모든 결과에 "screening estimate". 순위 없음.
- **Tier 2 Deep Analysis**: 다각형이 데모 필지 20개(Story IA 12, McLean IL 3, Lancaster NE 3, Union OH 2)와 겹치면 전략 A–D 카드(P10–P90, CVaR, 2012 백테스트, Prithvi/CDL, /explain). 밖이면 "Deep analysis available in 4 pilot counties".
- 강조 규칙: Corn+Soy → A·B, Wheat 추가 → C도, D(알팔파)는 참고 카드. 강조는 추천이 아님.
- 목업의 원형 구역 → Iowa / Illinois / Nebraska / Ohio 프리셋 버튼.
- 금지: "Recommended", 1위 배지, 보장 문구, 출처 없는 숫자. 결과 화면의 "MATLAB engine" → "FAO-56 engine (ported from team MATLAB prototype V8)".
- 경제값(가격·수량·비용)은 "assumption" 라벨 + USDA ERS/NASS 출처·연도. 출처 없으면 "information gap".
- Kc는 FAO-56 표 값(옥수수 1.20, 대두 1.15, 밀 1.15)으로, 목업 값을 쓰면 툴팁에 차이 표시.
- "Water saving %", "soil organic matter index"에는 "relative index — not a guarantee" 툴팁.
- 디자인 요청: 다각형 색은 노랑/빨강 대신 조화로운 색, 위성 베이스맵은 캡처 대신 고해상도 타일.
- 오늘 구현됨: 데모 필지 20개, IMERG·NLDAS 등 적재, Prithvi 20필지, MC/CVaR, 2012 백테스트, /explain. 계획: /quick, 프론트·배포, 복셀 시뮬.
- MATLAB이 서버에서 안 돌던 원인: 스크립트 파일 이름 = 내부 함수 이름(select_cornbelt_4vertices). 서버 문제 아님.
- 원문: docs/PRD.md, docs/SOT.md 6.0(/quick), docs/DECISIONS.md 18:57.
