# 기여 가이드

팀 **아몰라** · 공개 저장소 [cloudsnuchoi/2026NASA](https://github.com/cloudsnuchoi/2026NASA)  
해커톤 마감: **2026-11-15 23:59 Asia/Seoul (KST)**. 여섯 명이 각자 노트북에서 같은 저장소와 VPS DB를 쓴다.

제품 계약은 [docs/PRD.md](docs/PRD.md), 데이터·API는 [docs/SOT.md](docs/SOT.md), 일정은 [docs/CHECKLIST.md](docs/CHECKLIST.md). 에이전트는 [AGENTS.md](AGENTS.md)도 따른다.

---

## 워크플로

```text
이슈 생성 또는 기존 이슈 선택
    → 브랜치 feat/<이슈번호>-slug  (main에서)
    → 작게 커밋 (Conventional Commits)
    → PR을 main으로
    → 리뷰 1명 승인
    → squash merge
    → 이슈 닫힘, 보드 Status를 Done으로
```

1. **이슈가 일의 단위다.** 라벨 `area:*` 와 `priority: P0` 또는 `P1`을 붙인다. 본문의 “제안 담당”은 사람 이름이다. 급하지 않으면 GitHub 계정 할당은 본인이 한다.
2. **`main`은 항상 데모 가능한 쪽을 향한다.** 직접 푸시하지 않는다.
3. **한 PR · 한 이슈 · 작은 diff.** 계약(SOT) 변경과 구현은 가능하면 같은 PR에 둔다.
4. **리뷰 1명.** 해커톤 중에는 같은 영역이 아닌 사람 또는 팀장이 빠르게 본다. 승인 전 merge 금지. 작성자는 squash merge.
5. **충돌은 로컬에서 rebase 또는 merge 후 푸시.** `main`의 데이터 계약이 바뀌었으면 SOT를 다시 읽는다.
6. **데이터와 비밀값은 PR에 포함하지 않는다.** VPS의 `/data/raw`, `/data/processed/vN`만 사용한다. 연결 정보는 환경 변수.

브랜치 예:

```bash
git fetch origin
git switch -c feat/8-compare-api origin/main
# ... work, tests ...
git commit -m "feat(api): implement POST /strategies/compare"
git push -u origin feat/8-compare-api
```

---

## 매시 10분 싱크

**시각 (KST):** 11:00부터 18:00까지 매시 정각, 이후에는 30분 간격으로 줄여도 된다. **10분**을 넘기지 않는다.

각자 한 줄:

1. 방금 닫거나 옮긴 이슈
2. 막힌 점 (데이터, 계약, 리뷰, VPS)
3. 다음 한 시간의 목표

보드의 Status(Todo / In Progress / Blocked / Done 등)를 그 자리에서 갱신한다. 새로운 범위는 이슈로만 추가하고, 이 자리에서 PRD를 다시 열지 않는다. 18:00 기능 동결 이후에는 버그와 제출물만 말한다.

진행 현황의 **라이브 대시보드**는 GitHub Project 보드(또는 보드를 못 만들면 Issues + 라벨 필터)다. 별도 사내 Jira를 새로 들이지 않는다.

---

## 노트북에서 에이전트를 쓰는 법

- 각 저장소 루트를 작업 디렉터리로 연다. Codex CLI / agy CLI에게 **이 파일과 `AGENTS.md`, `docs/SOT.md`를 먼저 읽으라**고 한다.
- 프롬프트에 **이슈 번호**를 넣고, 다른 폴더를 고치지 말라고 제한한다.
- 공유 DB와 API URL은 `.env`(커밋 금지)로만 주입한다. 에이전트 로그에 키를 붙여 넣지 않는다.
- 같은 파일을 두 사람이 동시에 고치지 않게, 이슈·폴더 소유를 지킨다.

---

## 코드 리뷰에서 볼 것

- SOT 계약(필드명, 단위, CRS, 카드 항목) 준수
- 비밀값·대용량 데이터 없음
- 테스트 또는 스모크
- SI를 썼으면 `docs/si-log.md` 갱신
- 농부 판단을 대체하는 카피(“심어라”, 단일 최적해)가 없는지
