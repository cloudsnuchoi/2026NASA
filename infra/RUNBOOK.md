# RUNBOOK · VPS 세팅 순서 (Hylē, user `hackathon`)

> 대상 서버: Hetzner Ubuntu 22.04. 작업 범위는 `/srv/hackathon`뿐이다. `/opt/hyle*`, `/root/hyle-pause-*`, 다른 컨테이너, `hyle-*` systemd, `/etc/nginx`는 **건드리지 않는다**.
> 외부 노출은 Cloudflare quick tunnel로만 한다. ufw는 22번 포트만 연 상태 그대로 둔다. 시간은 KST.
> 전체 약 25–30분. 각 단계의 "기대 출력"과 다르면 멈추고 그 출력을 1on1이나 이 대화에 붙인다.

| # | 단계 | 시간 |
| --- | --- | --- |
| 0 | 사전 확인 | 1분 |
| 1 | 저장소 클론 | 1분 |
| 2 | 폴더·.env 준비 | 2분 |
| 3 | Mattermost 기동 | 3–5분 (이미지 pull) |
| 4 | 터널 + SiteURL | 1분 |
| 5 | 팀·채널·계정·봇 프로비저닝 | 1–2분 |
| 6 | 오케스트레이터 브리지 | 5분 |
| 7 | GitHub Actions 러너 등록 | 5분 |
| 8 | (선택) 브라우저 MATLAB 공유 | 3분 |
| 9 | 팀에 배포 | 5분 |

---

## 0. 사전 확인 (1분)

```bash
whoami                                   # hackathon
docker network ls --format '{{.Name}}' | grep -x hackathon-net
ss -ltn | grep -E ':8065\b' || echo "8065 free"
df -h /srv/hackathon | tail -1
```
기대 출력: `hackathon`, `hackathon-net`, `8065 free`. 8065가 사용 중이면 2단계 `.env`의 `MM_HOST_PORT`를 바꾸고 아래 명령의 8065도 그 값으로 바꾼다.

## 1. 저장소 클론 (1분)

```bash
cd /srv/hackathon/projects
git clone https://github.com/cloudsnuchoi/2026NASA.git   # 이미 있으면: git -C 2026NASA pull --ff-only
cd 2026NASA && git log --oneline -1
```

## 2. 폴더·.env 준비 (2분)

```bash
cd /srv/hackathon/projects/2026NASA/infra/chat
mkdir -p /srv/hackathon/db/mattermost/postgres /srv/hackathon/db/mattermost/app/{config,data,logs,plugins,client-plugins}
# Mattermost 컨테이너는 uid 2000으로 실행 → sudo 없이 docker로 소유권 변경
docker run --rm -v /srv/hackathon/db/mattermost/app:/x alpine chown -R 2000:2000 /x
cp -n .env.example .env
sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$(openssl rand -hex 24)/" .env
chmod 600 .env && grep -c . .env
```
기대 출력: 마지막 줄은 `8` 정도(빈 값 없음). `.env`는 git에서 무시된다(`git status`에 안 나와야 한다).

## 3. Mattermost 기동 (3–5분)

```bash
docker compose up -d
docker compose ps
until curl -fsS http://127.0.0.1:8065/api/v4/system/ping >/dev/null; do sleep 3; done; curl -s http://127.0.0.1:8065/api/v4/system/ping; echo
```
기대 출력: `amolla-mm-postgres (healthy)`, `amolla-mattermost Up`, `{"ActiveSearchBackend":"database","AndroidLatestVersion":"",…,"status":"OK"}`.
실패하면 `docker compose logs --tail 50 mattermost`를 본다. `permission denied`가 나오면 2단계의 `chown`을 다시 한다.

## 4. 터널 + SiteURL (1분)

```bash
cd /srv/hackathon/projects/2026NASA/infra/chat
tmux new -d -s mm-tunnel './tunnel.sh'
sleep 10 && ./tunnel-url.sh             # https://xxxx-xxxx.trycloudflare.com
./set-siteurl.sh
```
- 기대 출력: trycloudflare 주소와 `SiteURL = https://…`. 브라우저로 그 주소를 열면 Mattermost 로그인 화면이 나와야 한다.
- ⚠ quick tunnel 주소는 **cloudflared를 다시 켤 때마다 바뀐다**. 바뀌면 `./tunnel-url.sh` → `./set-siteurl.sh` 순서로 다시 맞추고, ~announce와 카톡에 새 주소를 올린다.
- tmux 대신 쓸 수 있는 `systemd --user` 유닛도 있다. 설치 방법은 `mm-tunnel.service` 주석에 있다. 로그아웃 뒤에도 유지하려면 `loginctl enable-linger`가 필요하다(sudo).

## 5. 프로비저닝 (1–2분)

```bash
./provision.sh
```
기대 출력(요약):
```
== users       created hyle (Hylē) … created daeun (강다은)
== team amolla created
== public channels  created ~announce … created ~random
== bot orchestrator (REST, as hyle)  created bot …  token written to ../orchestrator/.env
== private 1on1 channels  created 1on1-yoonsung … created 1on1-daeun
== done
```
- 다시 실행해도 안전하다. 이미 있는 계정은 건너뛰고, 비밀번호는 처음 만들 때만 기록한다.
- 임시 비밀번호는 `infra/chat/secrets/initial-passwords.txt`에 있다(git 무시, 권한 600). `hyle` 줄로 먼저 로그인해 본다. 나머지는 **각자에게 자기 줄만** 카톡 1:1로 보낸다.

## 6. 오케스트레이터 브리지 (5분)

```bash
cd /srv/hackathon/projects/2026NASA/infra/orchestrator
nano .env      # OPENAI_API_KEY=… , ORCH_MODEL=<계정에서 쓸 수 있는 모델>, (선택) GITHUB_TOKEN=읽기전용 fine-grained
grep -E '^(MM_BOT_TOKEN|OPENAI_API_KEY|ORCH_MODEL)=.+' .env | cut -d= -f1    # 세 줄 나와야 함

# 6a. 오프라인 시험 (키 없이 30초)
python3 -m venv .venv && .venv/bin/pip install -q -r requirements-dev.txt
.venv/bin/python -m pytest -q tests                  # 24 passed
printf 'jieun: 처음인데 뭐부터 해요?\n' | .venv/bin/python bridge.py --dry-run --mock-llm
# 6b. 실제 LLM으로 오프라인 시험 (선택)
printf 'jieun: 처음인데 뭐부터 해요?\n' | .venv/bin/python bridge.py --dry-run

# 6c. 운영: Docker (로그아웃해도 유지)
docker build -t amolla-orchestrator .
mkdir -p /srv/hackathon/db/orchestrator
docker run -d --name amolla-orchestrator --restart unless-stopped --network hackathon-net \
  --env-file .env \
  -e MM_URL=http://amolla-mattermost:8065 \
  -e REPO_DIR=/no-local-repo \
  -e STATE_PATH=/state/context.json \
  -v /srv/hackathon/projects/2026NASA/infra/chat/members.tsv:/repo/infra/chat/members.tsv:ro \
  -v /srv/hackathon/db/orchestrator:/state \
  amolla-orchestrator
sleep 5 && docker logs --tail 5 amolla-orchestrator
```
- 기대 출력: `websocket connected as @orchestrator`.
- `REPO_DIR=/no-local-repo`로 두면 봇이 문서를 GitHub `main`에서 직접 읽는다. 머지된 최신 문서가 5분 안에 반영된다.
- 확인: Mattermost `1:1 김윤성` 채널에서 `@orchestrator 테스트`를 쓰면 답이 와야 한다. Hylē가 `@` 없이 쓴 글에는 봇이 답하지 않는다(우선 지시로 저장된다).
- 대안: venv + `orchestrator.service`(systemd --user). 이때는 `.env`의 `MM_URL=http://127.0.0.1:8065`를 그대로 쓴다.
- 코드를 고친 뒤 재배포: `docker rm -f amolla-orchestrator && docker build -t amolla-orchestrator . && (위 docker run 다시)`.

## 7. GitHub Actions 러너 등록 (5분)

먼저 CI 워크플로를 제자리로 옮긴다([infra/ci/README.md](ci/README.md)). 봇 토큰에는 `workflow` 권한이 없어서 Hylē 계정으로 해야 한다.
```bash
cd /srv/hackathon/projects/2026NASA && git pull --ff-only
mkdir -p .github/workflows && git mv infra/ci/ci.yml .github/workflows/ci.yml
git commit -m "ci: enable self-hosted CI workflow" && git push origin main
```
(VPS에 gh 로그인이 없으면 노트북에서 해도 된다. `gh auth refresh -s workflow`가 필요할 수 있다.)


[infra/runner/REGISTER.md](runner/REGISTER.md)의 1–4절을 따른다. 요약하면: 등록 토큰 → `./config.sh --unattended --replace --url https://github.com/cloudsnuchoi/2026NASA --token … --name amolla-vps --labels hetzner` → `tmux new -d -s runner './run.sh'`. 러너가 online이 되고 `ci`가 초록으로 끝나면 5절을 실행해 main에 `ci-ok` 필수 체크를 더한다.

## 8. (선택) 브라우저 MATLAB 공유 (3분)

`matlab-hyle`(127.0.0.1:8888)를 MATLAB 담당에게 열어 주려면 터널을 하나 더 띄운다.

```bash
tmux new -d -s matlab-tunnel 'cloudflared tunnel --no-autoupdate --url http://127.0.0.1:8888 2>&1 | tee /srv/hackathon/db/matlab-tunnel.log'
sleep 10 && grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' /srv/hackathon/db/matlab-tunnel.log | tail -1
```
- ⚠ 이 주소를 아는 사람은 누구나 VPS의 MATLAB에 들어올 수 있다. 그 MATLAB은 `/srv/hackathon/projects`와 `/srv/hackathon/data`를 쓸 수 있다. matlab-proxy의 토큰 인증(`MWI_ENABLE_TOKEN_AUTH`)이 켜져 있는지 먼저 확인하고(**확인 필요**), 주소는 1on1 채널로만 보낸다. 다 쓰면 `tmux kill-session -t matlab-tunnel`.
- 세션은 하나다. 김윤성과 김우찬이 동시에 쓰면 충돌할 수 있다. 시간대를 나누거나 한 명은 개인 MATLAB에서 작업하게 한다.
- MATLAB 안에서 보이는 경로가 `/srv/hackathon/data`와 다르면, 그 경로를 ~data-matlab 채널 머리말에 적는다.

## 9. 팀에 배포 (5분)

1. ~announce 채널에 공지를 올린다. 채팅 주소, `docs/ONBOARDING.md` 링크, "1:1 채널에서 `안녕하세요`라고 쓰면 봇이 시작합니다"를 넣는다.
2. 아직 GitHub 초대가 안 된 3명(하지민, qlenfnfn@kau.kr 주인, 김윤성)의 GitHub 아이디를 받아 초대한다.
   ```bash
   gh api -X PUT repos/cloudsnuchoi/2026NASA/collaborators/<아이디> -f permission=push
   ```
3. 사람마다 첫 이슈를 `!assign`으로 보낸다. 예:
   - `!assign 지은 #12`
   - `!assign 지민 #13`
   - `!assign 다은 #30`
   - `!assign 윤성 #26`
   - `!assign 우찬 #24`

## 10. 팀원 노트북 agent-loop (Hylē 5분 + 팀원 각 5분)

순서가 중요하다. **1–6단계(채팅 + 오케스트레이터)가 먼저 떠 있어야** 팀원 설치가 성공한다.
1. 개인 액세스 토큰 권한: System Console → User Management → Users → 사람 선택 → Manage Roles → *Allow this account to generate personal access tokens* 체크 (5명). 또는
   `docker exec amolla-mattermost mmctl --local permissions role assign system_user_access_token yoonsung woochan jieun jimin daeun` (이 역할에 대한 mmctl 사용은 미검증 — 실패하면 UI).
2. ~announce에 채팅 주소 + 아래 한 줄 + `infra/agent-loop/README.md` 링크를 올린다.
   - Windows: `irm https://raw.githubusercontent.com/cloudsnuchoi/2026NASA/main/infra/agent-loop/install.ps1 | iex`
   - macOS: `bash -c "$(curl -fsSL https://raw.githubusercontent.com/cloudsnuchoi/2026NASA/main/infra/agent-loop/install.sh)"`
3. 확인: 각 1:1 채널(또는 ~agent-status)에 `🟢 @아이디 agent-loop …` 글이 생기고 3분마다 시각이 바뀐다. 아무 채널에서 `!status` → "노트북 agent-loop" 표.
4. 그다음 9단계의 `!assign`을 보내면, 봇 설명 + `!task #N …`이 같이 가고 노트북이 바로 작업을 시작한다.
- 봇은 check-in이 10분 넘게 끊기면 그 1:1 채널에 ⚠️ 알림을, 작업 실패·커밋 안 된 변경 방치 때 피드백을 1회씩 보낸다 (`AGENT_SILENT_MIN`, `AGENT_FEEDBACK_COOLDOWN_MIN`).
- ~agent-status 채널은 5단계 provision.sh를 다시 실행하면 생긴다 (기존 채널은 그대로). 팀원은 설정에 `"STATUS_CHANNEL": "agent-status"`를 넣으면 그 채널에 check-in한다. 기본은 1:1 채널.

## 재시작·장애 대응

| 증상 | 조치 |
| --- | --- |
| 채팅 주소가 안 열림 | `tmux ls`로 확인. `mm-tunnel`이 없으면 4단계를 다시 하고 새 주소를 공지 |
| 봇이 답 안 함 | `docker logs --tail 50 amolla-orchestrator`. 토큰 오류면 5단계를 다시 실행(토큰 줄을 지우고) 후 컨테이너 재시작. LLM 오류면 `.env` 키·모델 확인 |
| Mattermost 500 | `docker compose -f infra/chat/docker-compose.yml logs --tail 80` |
| CI가 대기만 함 | 러너 확인 `tmux attach -t runner`. 급하면 admin 우회 머지 |
| 디스크 | `du -sh /srv/hackathon/*`. 원본 데이터는 `/srv/hackathon/data/raw` |

정리(해커톤 이후): `docker compose down`(데이터 유지), 러너 `./config.sh remove`, `docker rm -f amolla-orchestrator`.
