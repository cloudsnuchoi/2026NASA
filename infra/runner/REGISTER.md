# Self-hosted runner 등록 (VPS, user `hackathon`)

러너는 이미 `/srv/hackathon/actions-runner`에 설치돼 있고, 아직 등록만 안 된 상태다. 레이블은 `self-hosted, linux`(자동)에 `hetzner`를 더한다. [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)(아직 [`infra/ci/ci.yml`](../ci/ci.yml)에 대기 — [infra/ci/README.md](../ci/README.md) 참고)은 `runs-on: [self-hosted, linux]`를 쓴다.

## ⚠ 공개 저장소 + self-hosted 러너 위험

공개 저장소에서는 누구나 포크해서 PR을 열 수 있다. 그 PR의 코드가 **VPS에서 실행**될 수 있다. 러너 사용자가 docker 그룹이면 사실상 root 권한이 된다. 그래서 세 겹으로 막는다.

1. **워크플로 조건:** 모든 job에 `if: github.event_name != 'pull_request' || github.event.pull_request.head.repo.full_name == github.repository`를 건다. 포크 PR은 job이 아예 시작하지 않는다. 같은 저장소 브랜치는 쓰기 권한(collaborator)이 있어야 만들 수 있다.
2. **저장소 설정 (적용됨, 2026-11-15):** 외부 기여자의 포크 PR 워크플로는 **항상 승인이 필요**하다(`approval_policy = all_external_contributors`). 확인은 Settings → Actions → General → "Approval for running fork pull request workflows from contributors".
3. **트리거 제한:** `pull_request_target`은 쓰지 않는다. 시크릿을 워크플로에 넣지 않는다. 러너 작업 폴더에는 `.env`나 키를 두지 않는다.

추가 권장: 데모가 끝나면 러너를 내린다(`./config.sh remove`). `hackathon` 사용자를 docker 그룹에서 빼는 것은 Mattermost 운영 때문에 이번에는 하지 않는다.

## 1. 등록 토큰 받기 (1시간 유효)

어느 쪽이든 하나를 고른다.

- **웹:** <https://github.com/cloudsnuchoi/2026NASA/settings/actions/runners/new>를 열고, "Configure" 칸의 `--token` 값을 복사한다.
- **gh(admin 권한 계정):**
  ```bash
  gh api -X POST repos/cloudsnuchoi/2026NASA/actions/runners/registration-token -q .token
  ```

## 2. VPS에서 등록 (user `hackathon`)

```bash
cd /srv/hackathon/actions-runner
ls config.sh run.sh svc.sh            # 설치 확인
read -rs RUNNER_TOKEN; export RUNNER_TOKEN   # 토큰 붙여넣고 엔터 (화면/히스토리에 안 남음)
./config.sh --unattended --replace \
  --url https://github.com/cloudsnuchoi/2026NASA \
  --token "$RUNNER_TOKEN" \
  --name amolla-vps --labels hetzner --work _work
unset RUNNER_TOKEN
```

예상 출력의 끝은 `√ Runner successfully added`, `√ Settings Saved.`이다.

## 3. 실행 (둘 중 하나)

- **tmux (sudo 불필요, 권장):**
  ```bash
  tmux new -d -s runner 'cd /srv/hackathon/actions-runner && ./run.sh'
  tmux capture-pane -pt runner | tail -3     # "Listening for Jobs"
  ```
- **systemd 서비스 (sudo 필요):** `sudo ./svc.sh install hackathon && sudo ./svc.sh start`

## 4. 확인

```bash
gh api repos/cloudsnuchoi/2026NASA/actions/runners -q '.runners[] | "\(.name) \(.status) \([.labels[].name]|join(","))"'
# amolla-vps online self-hosted,Linux,X64,hetzner
gh workflow run ci -R cloudsnuchoi/2026NASA && sleep 20 && gh run list -R cloudsnuchoi/2026NASA -L 1
```

러너에는 `python3`, `python3-venv`, `node`/`npm`이 필요하다. VPS에는 이미 Python 3.10과 Node v26이 있다. `python3 -m venv`가 실패하면 `sudo apt install python3.10-venv`를 실행한다.

## 5. 러너가 돈 뒤: main에 CI 필수 체크 추가

러너가 online이고 `ci` 워크플로가 한 번 초록으로 끝났다면, 저장소 admin 계정으로 아래를 실행한다.

```bash
RID=$(gh api repos/cloudsnuchoi/2026NASA/rulesets -q '.[] | select(.name=="main-protection") | .id')
gh api repos/cloudsnuchoi/2026NASA/rulesets/$RID > /tmp/rs.json
python3 - <<'PY'
import json
rs = json.load(open("/tmp/rs.json"))
rules = [r for r in rs["rules"] if r["type"] != "required_status_checks"]
rules.append({"type": "required_status_checks", "parameters": {
    "strict_required_status_checks_policy": False,
    "required_status_checks": [{"context": "ci-ok"}]}})
body = {k: rs[k] for k in ("name", "target", "enforcement", "conditions", "bypass_actors")}
body["rules"] = rules
json.dump(body, open("/tmp/rs_new.json", "w"))
PY
gh api -X PUT repos/cloudsnuchoi/2026NASA/rulesets/$RID --input /tmp/rs_new.json -q '.rules[].type'
```

⚠ 러너가 꺼져 있으면 `ci-ok`가 영원히 대기한다. 그러면 PR을 머지할 수 없다. 그때는 admin 우회로 머지하거나, 위 스크립트에서 `required_status_checks`를 다시 빼면 된다.
