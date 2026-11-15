#!/usr/bin/env python3
"""agent-loop: 팀원 노트북의 상시 에이전트 (team 아몰라, NASA Space Apps 2026).

Watches the member's private Mattermost channel (``1on1-<username>``). When an allowed user
(default: the ``orchestrator`` bot and ``hyle``) posts a message starting with ``!task``, it runs
the local coding agent (Codex CLI or Antigravity ``agy``) non-interactively in REPO_DIR, then
commits, pushes and opens a PR (``Closes #N``) and posts STATUS comments on the issue.
Progress and the final result are posted back as a thread reply on the ``!task`` message.

Only stdlib + requests. Config: env vars override ~/.amolla-agent.json.

  python agent_loop.py              # run (keep the terminal open)
  python agent_loop.py --setup      # interactive config (also done by install.sh / install.ps1)
  python agent_loop.py --set-url https://new-addr.trycloudflare.com   # chat address changed
  python agent_loop.py --check      # test login + channel, then exit

Chat commands (in the 1:1 channel, from an allowed user):
  !task #12 <지시>      run a job for issue 12 (issue optional: "!task <지시>")
  !agent status         reply with current state and queue
Safety: the agent keeps its own approval/sandbox defaults (see AGENT_CMD); the loop never adds
"dangerously-*" / "bypass" flags, never prints tokens, never merges, never force-pushes.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import platform
import queue
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import requests

VERSION = "1.0"
CONFIG_PATH = Path(os.environ.get("AMOLLA_AGENT_CONFIG", str(Path.home() / ".amolla-agent.json")))
PROP = "amolla_agent"  # post prop so bridge.py can tell agent-loop posts from human posts

# Command templates. {prompt} = whole prompt as ONE argv item; "-" + stdin when PROMPT_VIA=stdin.
# codex exec defaults to a read-only sandbox, so workspace-write is required to edit files.
# It keeps network off inside the sandbox; that is why git push / gh run in the loop, not in the agent.
DEFAULT_CMDS = {
    "codex": {"cmd": ["codex", "exec", "--sandbox", "workspace-write", "-"], "via": "stdin"},
    # agy headless: -p runs one prompt and exits; file edits in the workspace are allowed by default,
    # shell commands that need approval are soft-denied (no prompt). See antigravity.google/docs/cli/headless
    "agy": {"cmd": ["agy", "-p", "{prompt}"], "via": "arg"},
    # test/demo agent: prints the prompt head
    "echo": {"cmd": [sys.executable, "-c", "import sys;d=sys.stdin.read();print('ECHO-AGENT got', len(d), 'chars');print(d[-200:])"], "via": "stdin"},
}
FORBIDDEN_FLAGS = ("--dangerously", "bypass-approvals", "--yolo", "danger-full-access")

INSTRUCTION_BLOCK = """[agent-loop 고정 지시 — 반드시 지켜]
너는 팀 '아몰라'(NASA Space Apps 2026, 챌린지 07 Field Shift) 저장소에서 일하는 코딩 에이전트다.
현재 폴더가 저장소 루트다. 먼저 AGENTS.md, docs/SOT.md, docs/TEAM_SPEC.md를 읽고 {issue_scope} 범위만 작업해.
- 브랜치는 이미 `{branch}`로 준비돼 있다. 브랜치를 바꾸지 마.
- git commit / git push / gh pr create / gh issue comment 는 하지 마. 작업이 끝나면 agent-loop가 대신
  커밋하고 push하고 "Closes #{issue}" PR을 열고 docs/PROMPTS.md 형식의 STATUS 댓글을 남긴다.
- 비밀값(키·토큰·비밀번호)을 파일에 쓰거나 출력하지 마. .env 파일을 커밋 대상에 만들지 마. 100MB 넘는 파일 금지.
- 파일 삭제·대량 이동·의존성 대규모 변경처럼 되돌리기 어려운 일은 하지 말고 마지막 요약에 "확인 필요"로 적어.
- 데이터·숫자·DOI·URL을 지어내지 마. 모르면 '미확인'.
- 마지막 출력은 한국어 요약 5줄 이내: 무엇을 바꿨는지, 어떻게 확인했는지, 남은 일/막힌 점.
첫 줄에 커밋 메시지로 쓸 한 줄 요약을 `SUMMARY: <영문 conventional commit 제목>` 형식으로 출력해.
[작업 지시]
"""

SECRET_PATTERNS = [
    re.compile(r"(gh[pousr]_[A-Za-z0-9]{20,})"),
    re.compile(r"(github_pat_[A-Za-z0-9_]{20,})"),
    re.compile(r"(sk-[A-Za-z0-9_\-]{16,})"),
    re.compile(r"(AIza[0-9A-Za-z_\-]{30,})"),
    re.compile(r"(?i)((?:token|api[_-]?key|password|secret)\s*[=:]\s*)(\S{8,})"),
]


# --------------------------------------------------------------------------- config
@dataclass
class Config:
    mm_url: str = ""
    mm_token: str = ""
    team: str = "amolla"
    channel: str = ""  # e.g. 1on1-jieun ; default 1on1-<my username>
    agent: str = "codex"  # codex | agy | echo
    agent_cmd: List[str] = field(default_factory=list)  # override template
    prompt_via: str = ""  # stdin | arg (with override)
    repo_dir: str = str(Path.home() / "2026NASA")
    allow_users: List[str] = field(default_factory=lambda: ["orchestrator", "hyle"])
    trigger: str = "!task"
    git_mode: str = "loop"  # loop: loop does branch/commit/push/PR/STATUS ; agent: agent does it ; off
    github_repo: str = "cloudsnuchoi/2026NASA"
    poll_sec: float = 4.0
    heartbeat_min: float = 3.0  # check-in with the orchestrator every 3–5 min
    status_channel: str = ""  # "" = my 1:1 channel; e.g. "agent-status" for a shared board channel
    progress_sec: float = 90.0
    timeout_min: float = 60.0

    KEYS = {
        "MM_URL": "mm_url", "MM_TOKEN": "mm_token", "MM_TEAM": "team", "CHANNEL": "channel", "AGENT": "agent",
        "AGENT_CMD": "agent_cmd", "PROMPT_VIA": "prompt_via", "REPO_DIR": "repo_dir", "ALLOW_USERS": "allow_users",
        "TRIGGER": "trigger", "GIT_MODE": "git_mode", "GITHUB_REPO": "github_repo", "POLL_SEC": "poll_sec",
        "HEARTBEAT_MIN": "heartbeat_min", "STATUS_CHANNEL": "status_channel", "PROGRESS_SEC": "progress_sec", "TIMEOUT_MIN": "timeout_min",
    }

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> "Config":
        c = cls()
        raw: Dict[str, object] = {}
        if path.exists():
            raw.update(json.loads(path.read_text(encoding="utf-8")))
        for k in cls.KEYS:
            if os.environ.get(k):
                raw[k] = os.environ[k]
        for k, attr in cls.KEYS.items():
            if k not in raw or raw[k] in (None, ""):
                continue
            v, cur = raw[k], getattr(c, attr)
            if isinstance(cur, list) and isinstance(v, str):
                v = json.loads(v) if v.strip().startswith("[") else [x.strip() for x in v.split(",") if x.strip()]
            elif isinstance(cur, float):
                v = float(v)
            setattr(c, attr, v)
        c.mm_url = c.mm_url.rstrip("/")
        return c

    def save(self, path: Path = CONFIG_PATH) -> None:
        data = {k: getattr(self, a) for k, a in self.KEYS.items()}
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass

    def command(self) -> tuple:
        if self.agent_cmd:
            cmd, via = list(self.agent_cmd), self.prompt_via or ("arg" if "{prompt}" in self.agent_cmd else "stdin")
        else:
            d = DEFAULT_CMDS.get(self.agent)
            if not d:
                raise SystemExit(f"AGENT must be one of {list(DEFAULT_CMDS)} (or set AGENT_CMD)")
            cmd, via = list(d["cmd"]), d["via"]
        bad = [x for x in cmd if any(f in x for f in FORBIDDEN_FLAGS)]
        if bad and os.environ.get("AGENT_ALLOW_DANGEROUS") != "1":
            raise SystemExit(f"위험한 플래그는 쓰지 않아요: {bad} (정말 필요하면 본인이 AGENT_ALLOW_DANGEROUS=1)")
        return cmd, via


def redact(text: str, extra: List[str] = ()) -> str:
    for s in extra:
        if s and len(s) >= 6:
            text = text.replace(s, "***")
    for p in SECRET_PATTERNS:
        text = p.sub(lambda m: (m.group(1) + "***") if m.lastindex and m.lastindex > 1 else "***", text)
    return text


def log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


# --------------------------------------------------------------------------- Mattermost
class MM:
    def __init__(self, cfg: Config, session: Optional[requests.Session] = None):
        self.cfg = cfg
        self.s = session or requests.Session()
        self.s.headers["Authorization"] = f"Bearer {cfg.mm_token}"
        self.me: dict = {}
        self.channel_id = ""
        self.status_channel_id = ""
        self.allow_ids: Dict[str, str] = {}

    def api(self, method: str, path: str, **kw):
        r = self.s.request(method, f"{self.cfg.mm_url}/api/v4{path}", timeout=30, **kw)
        if r.status_code == 401:
            raise PermissionError("토큰이 틀렸거나 만료됐어요 (401). 새 개인 액세스 토큰으로 --setup 다시 실행")
        r.raise_for_status()
        return r.json() if r.content else {}

    def connect(self) -> None:
        self.me = self.api("GET", "/users/me")
        if not self.cfg.channel:
            self.cfg.channel = f"1on1-{self.me['username']}"
        team = self.api("GET", f"/teams/name/{self.cfg.team}")
        self.channel_id = self.api("GET", f"/teams/{team['id']}/channels/name/{self.cfg.channel}")["id"]
        self.status_channel_id = self.channel_id
        if self.cfg.status_channel and self.cfg.status_channel != self.cfg.channel:
            try:
                self.status_channel_id = self.api("GET", f"/teams/{team['id']}/channels/name/{self.cfg.status_channel}")["id"]
            except Exception as exc:
                log(f"~{self.cfg.status_channel} 채널을 못 찾아서 heartbeat는 1:1 채널에 올려요 ({type(exc).__name__})")
        users = self.api("POST", "/users/usernames", json=self.cfg.allow_users)
        self.allow_ids = {u["id"]: u["username"] for u in users}

    def post(self, message: str, root_id: str = "", kind: str = "reply", extra: Optional[dict] = None, channel_id: str = "") -> dict:
        props = {PROP: kind}
        props.update(extra or {})
        msg = redact(message, [self.cfg.mm_token])[:15000]
        return self.api("POST", "/posts", json={"channel_id": channel_id or self.channel_id, "message": msg,
                                                "root_id": root_id, "props": props})

    def edit(self, post_id: str, message: str, extra: Optional[dict] = None) -> dict:
        props = {PROP: "heartbeat"}
        props.update(extra or {})
        return self.api("PUT", f"/posts/{post_id}/patch", json={"message": redact(message, [self.cfg.mm_token]), "props": props})

    def new_posts(self, since_ms: int) -> List[dict]:
        d = self.api("GET", f"/channels/{self.channel_id}/posts", params={"since": since_ms})
        posts = d.get("posts", {}) or {}
        return sorted(posts.values(), key=lambda p: p.get("create_at", 0))


# --------------------------------------------------------------------------- jobs
@dataclass
class Job:
    post_id: str
    root_id: str
    issue: Optional[int]
    text: str
    by: str


def parse_task(message: str, trigger: str) -> Optional[tuple]:
    m = message.strip()
    if not m.lower().startswith(trigger.lower()):
        return None
    body = m[len(trigger):].strip()
    mi = re.match(r"#(\d+)\b\s*", body)
    issue = int(mi.group(1)) if mi else None
    if mi:
        body = body[mi.end():]
    return issue, body.strip()


def slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (s[:30].strip("-") or "task")


class Runner:
    """Git + agent execution. Separate so tests can use a temp repo."""

    def __init__(self, cfg: Config, say):
        self.cfg, self.say = cfg, say
        self.repo = Path(cfg.repo_dir).expanduser()
        self.proc: Optional[subprocess.Popen] = None

    def sh(self, *args: str, check: bool = True, timeout: int = 180) -> str:
        exe = shutil.which(args[0]) or args[0]
        r = subprocess.run([exe, *args[1:]], cwd=self.repo, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        if check and r.returncode != 0:
            raise RuntimeError(f"`{' '.join(args[:3])}` 실패: {(r.stderr or r.stdout).strip()[-600:]}")
        return (r.stdout or "").strip()

    def status_comment(self, issue: Optional[int], state: str, work: str, pct: int, nxt: str = "", blocked: str = "") -> None:
        if not issue or self.cfg.git_mode != "loop":
            return
        body = f"STATUS: {state}\n작업: {work}\n진행률: {pct}%\n"
        if blocked:
            body += f"막힌 점: {blocked}\n"
        if nxt:
            body += f"다음: {nxt}\n"
        body += f"\n<sub>agent-loop · {socket.gethostname()} · {self.cfg.agent}</sub>"
        try:
            self.sh("gh", "issue", "comment", str(issue), "-R", self.cfg.github_repo, "--body", body)
        except Exception as exc:  # STATUS failure must not kill the job
            self.say(f"(STATUS 댓글 실패: {redact(str(exc))[:200]})")

    def prepare_branch(self, job: Job) -> str:
        if self.cfg.git_mode != "loop":
            return self.sh("git", "rev-parse", "--abbrev-ref", "HEAD")
        if self.sh("git", "status", "--porcelain"):
            raise RuntimeError("저장소에 커밋 안 된 변경이 있어요. 먼저 정리해 주세요 (git status). 작업을 시작하지 않았어요.")
        cur = self.sh("git", "rev-parse", "--abbrev-ref", "HEAD")
        prefix = f"feat/{job.issue}-" if job.issue else None
        if prefix and cur.startswith(prefix):
            self.sh("git", "pull", "--ff-only", check=False)
            return cur
        self.sh("git", "checkout", "main")
        self.sh("git", "pull", "--ff-only")
        existing = [b.strip("* ").strip() for b in self.sh("git", "branch", "--list", f"{prefix}*").splitlines()] if prefix else []
        if existing:
            self.sh("git", "checkout", existing[0])
            return existing[0]
        name = f"feat/{job.issue}-{slug(job.text)}" if job.issue else f"feat/agent-{time.strftime('%m%d-%H%M%S')}-{slug(job.text)}"
        self.sh("git", "checkout", "-b", name)
        return name

    def run_agent(self, prompt: str, on_line) -> int:
        cmd, via = self.cfg.command()
        exe = shutil.which(cmd[0])
        if not exe:
            raise RuntimeError(f"`{cmd[0]}` 명령을 찾을 수 없어요. 설치·로그인 후 다시 켜 주세요.")
        if via == "arg" and exe.lower().endswith((".cmd", ".bat")):
            # Windows batch shims re-parse arguments through cmd.exe (newlines, & | < > break or inject).
            # Hand the agent a short pointer instead and keep the real prompt in .git/ (never committed).
            task_file = self.repo / ".git" / "amolla-task.md"
            task_file.write_text(prompt, encoding="utf-8")
            prompt = "Read the file .git/amolla-task.md in this repository and follow it exactly. Do not commit that file."
        argv = [exe] + [prompt if x == "{prompt}" else x for x in cmd[1:]]
        self.proc = subprocess.Popen(argv, cwd=self.repo, stdin=subprocess.PIPE if via == "stdin" else subprocess.DEVNULL,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                     encoding="utf-8", errors="replace", bufsize=1)
        if via == "stdin":
            try:
                self.proc.stdin.write(prompt)
                self.proc.stdin.close()
            except BrokenPipeError:
                pass
        deadline = time.time() + self.cfg.timeout_min * 60
        killer = threading.Timer(self.cfg.timeout_min * 60, lambda: self.proc and self.proc.kill())
        killer.daemon = True
        killer.start()
        try:
            for line in self.proc.stdout:
                on_line(line.rstrip("\n"))
            rc = self.proc.wait()
        finally:
            killer.cancel()
        if time.time() > deadline:
            on_line(f"(시간 초과 {self.cfg.timeout_min:.0f}분 — 중단함)")
            return 124
        return rc

    def finish_git(self, job: Job, branch: str, summary_line: str) -> str:
        """Commit + push + PR. Returns PR URL or a short note."""
        if self.cfg.git_mode != "loop":
            return ""
        if not self.sh("git", "status", "--porcelain"):
            return "(변경 없음 — 커밋/PR 안 만듦)"
        self.sh("git", "add", "-A")
        staged = self.sh("git", "diff", "--cached", "--name-only").splitlines()
        risky = [f for f in staged if re.search(r"(^|/)\.env($|\.)|\.pem$|id_rsa|secrets?/", f) and not f.endswith(".example")]
        if risky:
            self.sh("git", "reset", "-q")
            raise RuntimeError(f"비밀값일 수 있는 파일이 있어서 커밋을 멈췄어요: {risky}. 직접 확인해 주세요.")
        title = summary_line or (f"feat(#{job.issue}): {slug(job.text).replace('-', ' ')}" if job.issue else "chore: agent-loop task")
        self.sh("git", "commit", "-q", "-m", title[:72], "-m", f"agent-loop ({self.cfg.agent}) for {'#' + str(job.issue) if job.issue else 'task'}")
        self.sh("git", "push", "-u", "origin", branch, timeout=300)
        existing = self.sh("gh", "pr", "list", "-R", self.cfg.github_repo, "--head", branch, "--json", "url", "-q", ".[0].url", check=False)
        if existing:
            return existing
        body = (f"Closes #{job.issue}\n\n" if job.issue else "") + f"지시: {job.text[:1500]}\n\n자동 생성: agent-loop ({self.cfg.agent}). 머지는 Hylē가 한다."
        return self.sh("gh", "pr", "create", "-R", self.cfg.github_repo, "--base", "main", "--head", branch,
                       "--title", title[:72], "--body", body, timeout=120).splitlines()[-1]


def git_snapshot(repo: Path) -> Dict[str, str]:
    """branch, last commit, uncommitted file count. Never raises (heartbeat must not die)."""
    out = {"branch": "?", "commit": "?", "dirty": "?"}

    def g(*a: str) -> str:
        r = subprocess.run([shutil.which("git") or "git", "-C", str(repo), *a], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""

    try:
        out["branch"] = g("rev-parse", "--abbrev-ref", "HEAD") or "?"
        out["commit"] = (g("log", "-1", "--format=%h %s (%cr)") or "?")[:90]
        st = g("status", "--porcelain")
        out["dirty"] = str(len([x for x in st.splitlines() if x.strip()])) if st is not None else "?"
    except Exception:
        pass
    return out


class AgentLoop:
    def __init__(self, cfg: Config, mm: MM):
        self.cfg, self.mm = cfg, mm
        self.q: "queue.Queue[Job]" = queue.Queue()
        self.state = "idle"
        self.current: Optional[Job] = None
        self.hb_post = ""
        self.stop = threading.Event()
        self.started = int(time.time() * 1000)
        self.notes: List[str] = []  # recent feedback from orchestrator/Hylē (not !task)
        self.notes_total = 0

    # ---- status
    def task_label(self) -> str:
        if not self.current:
            return "-"
        return f"#{self.current.issue} {self.current.text[:40]}" if self.current.issue else self.current.text[:50]

    def snapshot(self) -> Dict[str, str]:
        snap = git_snapshot(Path(self.cfg.repo_dir).expanduser())
        snap.update(state=self.state, task=self.task_label(), queue=str(self.q.qsize()), agent=self.cfg.agent,
                    member=str(self.mm.me.get("username", "")), notes=str(self.notes_total),
                    every_min=f"{self.cfg.heartbeat_min:g}", ts=str(int(time.time())))
        return snap

    def heartbeat_text(self, snap: Optional[Dict[str, str]] = None) -> str:
        s = snap or self.snapshot()
        icon = {"idle": "🟢", "busy": "🟡", "error": "🔴"}.get(self.state, "⚪")
        return (f"{icon} **@{s['member']}** agent-loop · {s['agent']} · **{s['state']}** · 작업: {s['task']} · 대기 {s['queue']}\n"
                f"`{s['branch']}` · {s['commit']} · 커밋 안 된 파일 {s['dirty']}개 · 피드백 {s['notes']}건 · "
                f"{time.strftime('%H:%M')} KST (매 {s['every_min']}분 갱신)")

    def set_state(self, state: str, note: str = "") -> None:
        changed = state != self.state
        self.state = state
        if changed:
            try:
                self.mm.post(f"STATUS {state}{(' — ' + note) if note else ''}", kind="status", extra={"state": state})
            except Exception as exc:
                log(f"status post failed: {exc}")
        self.heartbeat()

    def heartbeat(self) -> None:
        """Check-in: one post per laptop, edited in place (bridge.py reads posted + post_edited)."""
        try:
            extra = self.snapshot()
            text = self.heartbeat_text(extra)
            if self.hb_post:
                try:
                    self.mm.edit(self.hb_post, text, extra)
                    return
                except requests.HTTPError:
                    self.hb_post = ""
            self.hb_post = self.mm.post(text, kind="heartbeat", extra=extra, channel_id=self.mm.status_channel_id).get("id", "")
        except Exception as exc:
            log(f"heartbeat failed: {exc}")

    # ---- polling
    def handle_post(self, p: dict) -> None:
        if p.get("user_id") == self.mm.me.get("id") and (p.get("props") or {}).get(PROP):
            return  # our own loop output
        who = self.mm.allow_ids.get(p.get("user_id", ""))
        msg = (p.get("message") or "").strip()
        if not who:
            return
        if msg.lower().startswith("!agent"):
            self.mm.post(self.heartbeat_text(), root_id=p.get("root_id") or p["id"])
            return
        parsed = parse_task(msg, self.cfg.trigger)
        if not parsed:
            if msg and p.get("channel_id", self.mm.channel_id) == self.mm.channel_id:
                self.notes = (self.notes + [f"[{time.strftime('%H:%M')} @{who}] {msg[:500]}"])[-3:]
                self.notes_total += 1
                log(f"\a📩 @{who}: {msg[:300]}")  # bell + show in the terminal so the member sees it
            return
        issue, text = parsed
        if not text and not issue:
            self.mm.post("사용법: `!task #12 지도 화면부터`", root_id=p["id"])
            return
        job = Job(p["id"], p.get("root_id") or p["id"], issue, text or f"이슈 #{issue}를 처리해", who)
        busy = self.current is not None
        self.q.put(job)
        self.mm.post(f"📥 받음 ({'대기열 ' + str(self.q.qsize()) + '번째' if busy else '곧 시작'}) · {self.cfg.agent} · by @{who}", root_id=job.root_id)
        self.heartbeat()

    def poll_forever(self) -> None:
        since = self.started
        seen: set = set()
        last_hb = 0.0
        fails = 0
        while not self.stop.is_set():
            try:
                for p in self.mm.new_posts(since):
                    since = max(since, p.get("create_at", since))
                    if p["id"] in seen or p.get("delete_at"):
                        continue
                    seen.add(p["id"])
                    if p.get("create_at", 0) < self.started:
                        continue
                    self.handle_post(p)
                if len(seen) > 5000:
                    seen = set(list(seen)[-1000:])
                if fails:
                    log("채팅 서버 다시 연결됨")
                fails = 0
                if time.time() - last_hb > self.cfg.heartbeat_min * 60:
                    self.heartbeat()
                    last_hb = time.time()
            except PermissionError as exc:
                log(str(exc))
                self.stop.wait(60)
            except Exception as exc:
                fails += 1
                if fails in (1, 5) or fails % 30 == 0:
                    log(f"채팅 서버 연결 실패 ({type(exc).__name__}). 주소가 바뀌었으면: python agent_loop.py --set-url <새주소>")
                self.stop.wait(min(60, self.cfg.poll_sec * fails))
                continue
            self.stop.wait(self.cfg.poll_sec)

    # ---- worker
    def work_forever(self) -> None:
        while not self.stop.is_set():
            try:
                job = self.q.get(timeout=1)
            except queue.Empty:
                continue
            self.current = job
            self.set_state("busy", f"#{job.issue}" if job.issue else job.text[:40])
            ok = self.run_job(job)
            self.current = None
            self.set_state("idle" if ok else "error", "" if ok else "마지막 작업 실패 — 스레드 확인")

    def run_job(self, job: Job) -> bool:
        say = lambda m: self.mm.post(m, root_id=job.root_id)  # noqa: E731
        runner = Runner(self.cfg, say)
        t0 = time.time()
        try:
            branch = runner.prepare_branch(job)
            say(f"▶️ 시작 · `{branch}` · {self.cfg.agent}")
            runner.status_comment(job.issue, "🟢 진행 중", job.text[:80], 10, "에이전트 작업 중")
            scope = f"이슈 #{job.issue}" if job.issue else "아래 지시"
            prompt = INSTRUCTION_BLOCK.format(issue_scope=scope, branch=branch, issue=job.issue or "N") + job.text
            if self.notes:
                prompt += "\n[참고: 최근 중앙 에이전트/Hylē 피드백 — 지시와 충돌하면 지시가 우선]\n" + "\n".join(self.notes)
            if job.issue:
                prompt += f"\n(이슈 본문은 `gh issue view {job.issue} -R {self.cfg.github_repo}` 로 볼 수 있음. 못 쓰면 지시만 따라.)"
            if self.cfg.git_mode == "agent":
                prompt = prompt.replace("- git commit / git push / gh pr create / gh issue comment 는 하지 마.",
                                        "- 끝나면 커밋하고 push하고 \"Closes #N\" PR을 열고 docs/PROMPTS.md 형식 STATUS 댓글을 남겨.")
            lines: List[str] = []
            last_progress = [time.time()]

            def on_line(line: str) -> None:
                print("   │", redact(line, [self.cfg.mm_token])[:300], flush=True)
                lines.append(line)
                if time.time() - last_progress[0] > self.cfg.progress_sec:
                    last_progress[0] = time.time()
                    tail = "\n".join(x[:160] for x in lines[-4:] if x.strip())
                    say(f"⏳ {int(time.time() - t0) // 60}분째 진행 중\n```\n{tail}\n```")

            rc = runner.run_agent(prompt, on_line)
            out = "\n".join(lines)
            m = re.search(r"^SUMMARY:\s*(.+)$", out, re.M)
            summary_line = m.group(1).strip() if m else ""
            tail = "\n".join(x[:200] for x in lines[-25:])
            if rc != 0:
                runner.status_comment(job.issue, "🔴 막힘", job.text[:80], 30, "Hylē 확인", f"에이전트 종료 코드 {rc}")
                say(f"❌ 실패 (exit {rc}, {int(time.time() - t0) // 60}분)\n```\n{tail}\n```")
                return False
            pr = runner.finish_git(job, branch, summary_line)
            if pr.startswith("http"):
                runner.status_comment(job.issue, "🟡 리뷰 대기", job.text[:80], 100, f"리뷰 대기 {pr}")
            say(f"✅ 완료 (exit 0, {int(time.time() - t0) // 60}분){(' · PR ' + pr) if pr else ''}\n```\n{tail}\n```")
            return True
        except Exception as exc:
            msg = redact(str(exc), [self.cfg.mm_token])
            runner.status_comment(job.issue, "🔴 막힘", job.text[:80], 0, "Hylē 확인", msg[:200])
            try:
                say(f"❌ 오류: {msg[:1500]}")
            except Exception:
                pass
            log(f"job error: {msg}")
            return False

    def run(self) -> None:
        threading.Thread(target=self.work_forever, daemon=True).start()
        log(f"agent-loop 시작 · ~{self.cfg.channel} · {self.cfg.agent} · {self.cfg.repo_dir}. 이 창을 닫지 마세요 (Ctrl+C 종료)")
        self.heartbeat()
        try:
            self.poll_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop.set()
            try:
                if self.hb_post:
                    self.mm.edit(self.hb_post, f"⚫ offline · agent-loop · @{self.mm.me.get('username')} · {time.strftime('%H:%M')} KST", dict(self.snapshot(), state="offline"))
            except Exception:
                pass
            log("종료")


# --------------------------------------------------------------------------- CLI
def setup(cfg: Config) -> Config:
    print("== agent-loop 설정 (Enter = [기본값]) ==")
    url = input(f"채팅 주소 (예: https://xxxx.trycloudflare.com) [{cfg.mm_url}]: ").strip() or cfg.mm_url
    tok = getpass.getpass("Mattermost 개인 액세스 토큰 (입력해도 화면에 안 보임): ").strip() or cfg.mm_token
    agent = (input(f"에이전트 codex / agy [{cfg.agent}]: ").strip() or cfg.agent).lower()
    repo = input(f"저장소 폴더 [{cfg.repo_dir}]: ").strip() or cfg.repo_dir
    cfg.mm_url, cfg.mm_token, cfg.agent, cfg.repo_dir = url.rstrip("/"), tok, agent, repo
    cfg.save()
    print(f"저장함: {CONFIG_PATH} (토큰 포함 — 다른 사람에게 보내지 마세요)")
    return cfg


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--setup", action="store_true")
    ap.add_argument("--set-url")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    cfg = Config.load()
    if a.setup:
        cfg = setup(cfg)
    if a.set_url:
        cfg.mm_url = a.set_url.rstrip("/")
        cfg.save()
        print(f"채팅 주소 바꿈: {cfg.mm_url}")
    if not cfg.mm_url or not cfg.mm_token:
        print("설정이 없어요. 먼저: python agent_loop.py --setup")
        return 2
    cfg.command()  # validate agent choice early
    if cfg.git_mode == "loop" and not (Path(cfg.repo_dir).expanduser() / ".git").exists():
        print(f"저장소 폴더가 아니에요: {cfg.repo_dir}. 설치 스크립트를 다시 실행하거나 REPO_DIR을 고쳐 주세요.")
        return 2
    mm = MM(cfg)
    try:
        mm.connect()
    except Exception as exc:
        print(f"채팅 연결 실패: {redact(str(exc), [cfg.mm_token])}\n주소({cfg.mm_url})·토큰·채널(~{cfg.channel or '1on1-<내아이디>'})을 확인하세요.")
        return 1
    print(f"연결 OK: @{mm.me['username']} · ~{cfg.channel} · 지시 허용: {', '.join(mm.allow_ids.values()) or '(없음!)'} · {platform.system()}")
    if a.check:
        return 0
    AgentLoop(cfg, mm).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
