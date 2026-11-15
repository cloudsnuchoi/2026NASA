#!/usr/bin/env python3
"""Mattermost <-> LLM orchestrator bridge for team 아몰라 (NASA Space Apps 2026).

Listens on the Mattermost websocket. Replies in private ``1on1-<username>`` channels and
in team channels when @orchestrator is mentioned. Each reply gives: next task, a copy-paste
prompt for Codex/agy CLI, and done criteria. Context = repo docs + read-only GitHub state.

Hylē (HYLE_USERNAME) overrides: a plain message from Hylē in a 1on1 channel is stored as a
priority instruction for that member (the bot stays silent); Hylē can push work with
``!assign``. See infra/orchestrator/README.md.

Run modes:
  python bridge.py                 # live (needs MM_URL, MM_BOT_TOKEN, OPENAI_API_KEY)
  python bridge.py --no-post       # live listen, print replies instead of posting
  python bridge.py --dry-run       # offline REPL: "<username>: message" lines on stdin
  python bridge.py --dry-run --mock-llm   # offline, no API key needed
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

import requests

log = logging.getLogger("orchestrator")
HERE = Path(__file__).resolve().parent
MAX_POST = 15000  # Mattermost hard limit is 16383 chars
DOC_FILES = [
    "AGENTS.md",
    "docs/CHECKLIST.md",
    "docs/PROMPTS.md",
    "docs/SOT.md",
    "docs/PRD.md",
    "docs/TEAM_SPEC.md",
]


# --------------------------------------------------------------------------- config
def load_dotenv(path: Path) -> None:
    """Tiny .env loader (no dependency). Existing env vars win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


@dataclass
class Config:
    mm_url: str = "http://127.0.0.1:8065"
    mm_token: str = ""
    team: str = "amolla"
    hyle: str = "hyle"
    bot_username: str = "orchestrator"
    model: str = ""
    openai_base_url: str = ""
    github_repo: str = "cloudsnuchoi/2026NASA"
    github_token: str = ""
    repo_dir: Path = Path("/srv/hackathon/projects/2026NASA")
    members_tsv: Path = HERE.parent / "chat" / "members.tsv"
    state_path: Path = HERE / "state" / "context.json"
    history_turns: int = 16
    doc_budget: int = 60000
    max_tokens: int = 2500
    agent_silent_min: float = 10.0  # flag a laptop agent-loop silent longer than this
    agent_feedback_cooldown_min: float = 30.0
    auto_dispatch: bool = True  # !assign also posts "!task #N <prompt>" for the member's laptop agent-loop

    @classmethod
    def from_env(cls) -> "Config":
        e = os.environ.get
        c = cls()
        c.mm_url = e("MM_URL", c.mm_url).rstrip("/")
        c.mm_token = e("MM_BOT_TOKEN", "")
        c.team = e("MM_TEAM", c.team)
        c.hyle = e("HYLE_USERNAME", c.hyle)
        c.bot_username = e("BOT_USERNAME", c.bot_username)
        c.model = e("ORCH_MODEL", "")
        c.openai_base_url = e("OPENAI_BASE_URL", "")
        c.github_repo = e("GITHUB_REPO", c.github_repo)
        c.github_token = e("GITHUB_TOKEN", "")
        c.repo_dir = Path(e("REPO_DIR", str(c.repo_dir)))
        c.members_tsv = Path(e("MEMBERS_TSV", str(c.members_tsv)))
        c.state_path = Path(e("STATE_PATH", str(c.state_path)))
        c.history_turns = int(e("HISTORY_TURNS", c.history_turns))
        c.doc_budget = int(e("DOC_BUDGET_CHARS", c.doc_budget))
        c.max_tokens = int(e("ORCH_MAX_TOKENS", c.max_tokens))
        c.agent_silent_min = float(e("AGENT_SILENT_MIN", c.agent_silent_min))
        c.agent_feedback_cooldown_min = float(e("AGENT_FEEDBACK_COOLDOWN_MIN", c.agent_feedback_cooldown_min))
        c.auto_dispatch = e("AUTO_DISPATCH", "1").strip().lower() not in ("0", "false", "no", "")
        return c


@dataclass
class Member:
    username: str
    name: str
    role: str
    area: str
    is_admin: bool = False

    @property
    def uses_git(self) -> bool:
        return "matlab" not in self.area


def load_members(path: Path) -> Dict[str, Member]:
    out: Dict[str, Member] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        u, n, r, a = parts[:4]
        adm = len(parts) > 4 and parts[4].strip() == "yes"
        out[u.strip()] = Member(u.strip(), n.strip(), r.strip(), a.strip(), adm)
    return out


def find_member(members: Dict[str, Member], token: str) -> Optional[Member]:
    t = token.lstrip("@").strip()
    if t in members:
        return members[t]
    for m in members.values():
        if t and (t == m.name or t in m.name or m.name.endswith(t)):
            return m
    return None


# --------------------------------------------------------------------------- context
class DocsContext:
    def __init__(self, cfg: Config, fetch: Callable[[str], str] = None):
        self.cfg = cfg
        self.fetch = fetch or self._fetch_raw
        self._cache: Optional[str] = None
        self._ts = 0.0

    def _fetch_raw(self, rel: str) -> str:
        p = self.cfg.repo_dir / rel
        if p.exists():
            return p.read_text(encoding="utf-8", errors="replace")
        url = f"https://raw.githubusercontent.com/{self.cfg.github_repo}/main/{rel}"
        r = requests.get(url, timeout=20)
        return r.text if r.ok else ""

    def text(self) -> str:
        if self._cache is not None and time.time() - self._ts < 300:
            return self._cache
        budget, chunks = self.cfg.doc_budget, []
        per_file = max(2000, budget // len(DOC_FILES))
        for rel in DOC_FILES:
            try:
                body = self.fetch(rel)
            except Exception as exc:  # network etc.
                log.warning("doc %s: %s", rel, exc)
                body = ""
            if not body:
                continue
            if len(body) > per_file:
                body = body[:per_file] + f"\n…(잘림, 전체는 repo의 {rel})"
            chunks.append(f"### FILE {rel}\n{body}")
        self._cache, self._ts = "\n\n".join(chunks), time.time()
        return self._cache


class GitHubContext:
    """Read-only GitHub REST. Never writes."""

    def __init__(self, cfg: Config, session: Optional[requests.Session] = None):
        self.cfg = cfg
        self.s = session or requests.Session()
        self.s.headers.update({"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
        if cfg.github_token:
            self.s.headers["Authorization"] = f"Bearer {cfg.github_token}"
        self._cache: Dict[str, tuple] = {}

    def _get(self, path: str, accept: str = "", ttl: int = 120):
        key = path + accept
        hit = self._cache.get(key)
        if hit and time.time() - hit[0] < ttl:
            return hit[1]
        url = f"https://api.github.com/repos/{self.cfg.github_repo}{path}"
        headers = {"Accept": accept} if accept else {}
        r = self.s.get(url, headers=headers, timeout=20)
        r.raise_for_status()
        data = r.text if accept.endswith("diff") else r.json()
        self._cache[key] = (time.time(), data)
        return data

    def open_issues(self) -> List[dict]:
        items = self._get("/issues?state=open&per_page=100")
        return [i for i in items if "pull_request" not in i]

    def issues_for(self, member: Member) -> List[dict]:
        """Issues whose body names the member as suggested owner (## 제안 담당)."""
        out = []
        for i in self.open_issues():
            body = i.get("body") or ""
            m = re.search(r"##\s*제안 담당\s*\n(.+?)(\n##|\Z)", body, re.S)
            owners = m.group(1) if m else ""
            if member.name in owners or member.username in owners:
                out.append(i)
        return out

    def issue(self, n: int) -> dict:
        return self._get(f"/issues/{n}", ttl=30)

    def open_prs(self) -> List[dict]:
        return self._get("/pulls?state=open&per_page=50")

    def pr(self, n: int) -> dict:
        return self._get(f"/pulls/{n}", ttl=30)

    def pr_diff(self, n: int, limit: int = 60000) -> str:
        d = self._get(f"/pulls/{n}", accept="application/vnd.github.diff", ttl=30)
        return d if len(d) <= limit else d[:limit] + "\n…(diff 잘림)"

    def ci_state(self, sha: str) -> str:
        try:
            runs = self._get(f"/commits/{sha}/check-runs", ttl=60).get("check_runs", [])
        except Exception:
            return "unknown"
        if not runs:
            return "none"
        if any(r.get("status") != "completed" for r in runs):
            return "running"
        bad = [r["name"] for r in runs if r.get("conclusion") not in ("success", "skipped", "neutral")]
        return "failed: " + ",".join(bad) if bad else "passed"

    def summary(self, member: Optional[Member] = None) -> str:
        lines = []
        try:
            issues = self.issues_for(member) if member else self.open_issues()
            lines.append(f"열린 이슈({'담당 ' + member.name if member else '전체'}): {len(issues)}개")
            for i in issues[:15]:
                labels = ",".join(lb["name"] for lb in i.get("labels", []))
                lines.append(f"- #{i['number']} {i['title']} [{labels}]")
            prs = self.open_prs()
            lines.append(f"열린 PR: {len(prs)}개")
            for p in prs[:15]:
                lines.append(
                    f"- PR #{p['number']} {p['title']} by {p['user']['login']} "
                    f"(CI {self.ci_state(p['head']['sha'])}) {p['html_url']}"
                )
        except Exception as exc:
            lines.append(f"(GitHub 조회 실패: {exc})")
        return "\n".join(lines)


# --------------------------------------------------------------------------- LLM
class LLM:
    def complete(self, system: str, messages: List[dict]) -> str:  # pragma: no cover - interface
        raise NotImplementedError


class OpenAILLM(LLM):
    def __init__(self, cfg: Config):
        from openai import OpenAI  # imported lazily so --mock-llm works without the package

        if not cfg.model:
            raise SystemExit("ORCH_MODEL is required (e.g. a model your OpenAI account can use)")
        kw = {"base_url": cfg.openai_base_url} if cfg.openai_base_url else {}
        self.client = OpenAI(**kw)  # reads OPENAI_API_KEY
        self.cfg = cfg

    def complete(self, system: str, messages: List[dict]) -> str:
        r = self.client.chat.completions.create(
            model=self.cfg.model,
            messages=[{"role": "system", "content": system}] + messages,
            max_completion_tokens=self.cfg.max_tokens,
        )
        return (r.choices[0].message.content or "").strip()


class MockLLM(LLM):
    def __init__(self):
        self.calls: List[dict] = []

    def complete(self, system: str, messages: List[dict]) -> str:
        self.calls.append({"system": system, "messages": messages})
        last = messages[-1]["content"] if messages else ""
        return (
            "**다음 할 일**\n(mock) " + last[:80] + "\n\n**복사-붙여넣기 프롬프트**\n```\n(mock prompt)\n```\n\n"
            "**완료 기준**\n- (mock)\n\n**보고할 것**\n- PR 링크 + 스크린샷"
        )


# --------------------------------------------------------------------------- core
SYSTEM_TEMPLATE = """너는 NASA Space Apps Challenge 2026 서울, 팀 '아몰라'의 중앙 오케스트레이터 에이전트다.
챌린지 07 Field Shift. 마감 2026-11-15 23:59 KST. 지금 {now} KST.
팀원은 GitHub·Codex CLI 경험이 0이다. 설명은 짧고 구체적으로, 한국어로. 식별자·경로·명령은 영어.
총괄은 Hylē(@{hyle}). Hylē의 지시가 항상 너보다 우선한다. 네가 확신 없는 결정(스키마·API·범위 변경)은 "Hylē 확인 필요"라고 쓰고 진행하지 마라.

지금 대화 상대: {name} (@{username}), 역할: {role}, 라벨: {area}.
{git_rule}

매 답변은 아래 형식을 지킨다 (질문에 단순히 답할 때만 짧게):
**다음 할 일** — 한 가지. 관련 이슈 번호.
**복사-붙여넣기 프롬프트** — Codex CLI 또는 agy CLI에 그대로 붙일 프롬프트를 ``` 코드블록 하나로. 첫 줄은 "AGENTS.md, docs/SOT.md, docs/TEAM_SPEC.md를 읽고 이슈 #N 범위만 작업해." 마지막에는 docs/PROMPTS.md의 해당 역할 '마무리 블록'을 그대로 붙인다.
**완료 기준** — 체크리스트 3~5개, 확인 가능한 것.
**보고할 것** — 1:1 채널에 올릴 것 (PR 링크 + 스크린샷, MATLAB은 파일 경로 + 그림).

규칙: 데이터·숫자·DOI·URL을 지어내지 않는다. 모르면 '미확인'. 비밀값(키·비밀번호·토큰)을 요구하거나 채팅에 붙이게 하지 않는다.
PR 리뷰 요청이면: 이슈 범위 준수, SOT 계약 일치, 비밀값/대용량 파일 커밋 여부, 테스트·CI, 화면 문구 규칙을 보고 '머지 가능/수정 필요'와 고칠 프롬프트를 준다. 머지는 Hylē가 한다.

{overrides}
## GitHub 현재 상태 (읽기 전용)
{github}

## 저장소 문서 (발췌)
{docs}
"""

GIT_RULE = "이 사람은 git을 직접 쓰지 않고, Codex/agy가 마무리 블록으로 브랜치·커밋·PR을 만든다. 사람에게 git 명령을 외우게 하지 마라."
MATLAB_RULE = (
    "MATLAB 담당은 git을 쓰지 않는다. 브라우저 MATLAB(VPS)에서 스크립트를 /srv/hackathon/projects/2026NASA/matlab/ 에, "
    "산출은 SOT 4절 경로 /srv/hackathon/data/processed/v{N}/matlab/ 에 저장하고 manifest.json을 남긴다. 커밋은 Hylē/오케스트레이터가 한다. "
    "프롬프트는 MATLAB 코드 생성용(Codex/agy에 붙이고 결과 코드를 MATLAB에 붙여 실행)으로 준다."
)

HELP = """**orchestrator 명령** (메시지 맨 앞에 입력)
- `!help` 이 도움말
- `!status` 이슈·PR·CI 요약
- `!review <PR번호>` PR diff 리뷰
- `!reset` 이 채널 대화 기억 지우기
- (Hylē) `!assign <이름|username> #<이슈> [추가 지시]` 해당 1on1 채널에 작업 지시 보내기
- (Hylē) `!note <이름|username> <지시>` 그 사람 채널에 우선 지시만 저장(답 안 함)
- (Hylē·봇) `!task #<이슈> <지시>` 1on1 채널에 쓰면 그 팀원 노트북의 agent-loop가 실행 (봇은 대답 안 함)
- `!agent` 노트북 agent-loop 상태 묻기 (agent-loop가 답함)
`!assign`은 git 쓰는 팀원에게 `!task`도 자동으로 보내요 (AUTO_DISPATCH=0이면 끔).
1on1 채널에서는 그냥 질문하면 돼요. 팀 채널에서는 @orchestrator 를 붙여 주세요."""


@dataclass
class Incoming:
    channel_id: str
    channel_name: str
    channel_type: str  # O public, P private, D direct
    user_id: str
    username: str
    message: str
    post_id: str = ""
    root_id: str = ""
    mentioned: bool = False
    file_count: int = 0
    agent_kind: str = ""  # set when the post comes from a laptop agent-loop (props.amolla_agent)
    agent_state: str = ""
    agent_props: dict = field(default_factory=dict)


@dataclass
class Outgoing:
    channel: str  # channel id, or "name:<channel-name>" to resolve
    message: str
    root_id: str = ""


@dataclass
class ChannelState:
    history: List[dict] = field(default_factory=list)
    overrides: List[str] = field(default_factory=list)


class Orchestrator:
    def __init__(self, cfg: Config, llm: LLM, gh: GitHubContext, docs: DocsContext, members: Dict[str, Member]):
        self.cfg, self.llm, self.gh, self.docs, self.members = cfg, llm, gh, docs, members
        self.state: Dict[str, ChannelState] = {}
        self.agents: Dict[str, dict] = {}  # member username -> last agent-loop check-in (props + at)
        self._load_state()

    # ---- persistence
    def _load_state(self) -> None:
        try:
            raw = json.loads(self.cfg.state_path.read_text(encoding="utf-8"))
            self.state = {k: ChannelState(**v) for k, v in raw.items()}
        except Exception:
            self.state = {}

    def save_state(self) -> None:
        try:
            self.cfg.state_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.cfg.state_path.with_suffix(".tmp")
            tmp.write_text(
                json.dumps({k: v.__dict__ for k, v in self.state.items()}, ensure_ascii=False, indent=1),
                encoding="utf-8",
            )
            tmp.replace(self.cfg.state_path)
        except Exception as exc:
            log.warning("state save failed: %s", exc)

    def st(self, channel_name: str) -> ChannelState:
        return self.state.setdefault(channel_name, ChannelState())

    # ---- routing
    def member_for_channel(self, channel_name: str) -> Optional[Member]:
        if channel_name.startswith("1on1-"):
            return self.members.get(channel_name[len("1on1-"):])
        return None

    def handle(self, inc: Incoming) -> List[Outgoing]:
        msg = inc.message.strip()
        if inc.agent_kind:  # laptop agent-loop output: remember check-ins, reply only with rule-based feedback
            return self.on_agent(inc) if inc.agent_kind in ("heartbeat", "status") else []
        if msg.lower().startswith(("!task", "!agent")):
            return []  # addressed to the member's laptop agent-loop
        if not msg and not inc.file_count:
            return []
        is_hyle = inc.username == self.cfg.hyle
        one_on_one = self.member_for_channel(inc.channel_name)
        root = inc.root_id or ("" if one_on_one else inc.post_id)

        if msg.startswith("!"):
            return self._command(inc, msg, is_hyle, root)

        if one_on_one is not None:
            if is_hyle and not inc.mentioned:
                self.st(inc.channel_name).overrides.append(f"[{_now()}] {msg}")
                self.st(inc.channel_name).overrides = self.st(inc.channel_name).overrides[-10:]
                self.save_state()
                return []  # Hylē speaks; the bot stays quiet but remembers it as priority
            member = one_on_one
        elif inc.mentioned or inc.channel_type == "D":
            member = self.members.get(inc.username) or Member(inc.username, inc.username, "팀원", "")
        else:
            return []

        text = msg + (f"\n(첨부 파일 {inc.file_count}개 — 봇은 이미지 내용을 못 봄. 필요하면 글로 설명)" if inc.file_count else "")
        if is_hyle and one_on_one is not None:
            text = f"[Hylē 지시] {text}"
        reply = self._ask(inc.channel_name, member, text)
        return [Outgoing(inc.channel_id, reply, root)]

    def _command(self, inc: Incoming, msg: str, is_hyle: bool, root: str) -> List[Outgoing]:
        parts = msg.split(maxsplit=3)
        cmd = parts[0].lower()
        out = lambda text: [Outgoing(inc.channel_id, text, root)]  # noqa: E731
        if cmd == "!help":
            return out(HELP)
        if cmd == "!reset":
            self.state.pop(inc.channel_name, None)
            self.save_state()
            return out("이 채널 대화 기억을 지웠어요. (Hylē 우선 지시도 함께 지워짐)")
        if cmd == "!status":
            member = self.member_for_channel(inc.channel_name)
            return out(self.gh.summary(member) + "\n" + self.agent_summary(inc.channel_name if member else None))
        if cmd == "!review":
            m = re.search(r"\d+", msg[len("!review"):])
            if not m:
                return out("사용법: `!review 12`")
            n = int(m.group())
            try:
                pr = self.gh.pr(n)
                diff = self.gh.pr_diff(n)
                ci = self.gh.ci_state(pr["head"]["sha"])
            except Exception as exc:
                return out(f"PR #{n} 조회 실패: {exc}")
            member = self.member_for_channel(inc.channel_name) or self.members.get(inc.username) or Member(
                inc.username, inc.username, "팀원", ""
            )
            prompt = (
                f"PR #{n} 리뷰해줘. 제목: {pr['title']}\n작성자: {pr['user']['login']}\nCI: {ci}\n"
                f"본문:\n{(pr.get('body') or '')[:3000]}\n\nDIFF:\n{diff}"
            )
            return out(self._ask(inc.channel_name, member, prompt, remember=False))
        if cmd in ("!assign", "!note"):
            if not is_hyle:
                return out(f"`{cmd}`는 Hylē만 쓸 수 있어요.")
            if len(parts) < 3:
                return out("사용법: `!assign 지은 #12 지도부터` / `!note 우찬 오늘은 NEX-GDDP 먼저`")
            target = find_member(self.members, parts[1])
            if not target or target.username == self.cfg.hyle:
                return out(f"팀원을 못 찾았어요: {parts[1]}")
            ch = f"1on1-{target.username}"
            rest = " ".join(parts[2:])
            if cmd == "!note":
                self.st(ch).overrides.append(f"[{_now()}] {rest}")
                self.save_state()
                return out(f"{target.name}님 채널에 우선 지시로 저장했어요.")
            m = re.search(r"#(\d+)", rest)
            issue_txt = ""
            if m:
                try:
                    iss = self.gh.issue(int(m.group(1)))
                    issue_txt = f"\n이슈 #{iss['number']} {iss['title']}\n{(iss.get('body') or '')[:4000]}"
                except Exception as exc:
                    issue_txt = f"\n(이슈 조회 실패: {exc})"
            self.st(ch).overrides.append(f"[{_now()}] !assign {rest}")
            prompt = f"[Hylē 지시] {target.name}님에게 다음 작업을 배정한다: {rest}{issue_txt}\n위 형식으로 작업 지시를 써라."
            reply = self._ask(ch, target, prompt)
            outs = [Outgoing(f"name:{ch}", f"@{target.username} Hylē가 작업을 배정했어요.\n\n{reply}")]
            note = ""
            if self.cfg.auto_dispatch and target.uses_git:
                task_prompt = extract_prompt(reply) or rest
                outs.append(Outgoing(f"name:{ch}", f"!task {('#' + m.group(1) + ' ') if m else ''}{task_prompt}"[:MAX_POST]))
                ag = self.agents.get(target.username)
                fresh = ag and time.time() - ag["at"] < self.cfg.agent_silent_min * 60 and ag.get("state") != "offline"
                note = " 노트북 agent-loop에도 `!task`로 보냈어요" + ("." if fresh else f" (최근 {self.cfg.agent_silent_min:g}분 heartbeat 없음 — 노트북이 꺼져 있을 수 있어요).")
            outs.append(Outgoing(inc.channel_id, f"{target.name}님 1on1 채널(~{ch})로 보냈어요.{note}", root))
            return outs
        return out(f"모르는 명령이에요: {cmd}\n\n{HELP}")

    # ---- laptop agent-loop check-ins
    def _feedback(self, a: dict, kind: str, text: str, now: float) -> List[Outgoing]:
        """One rule-based message to the member's 1on1, rate-limited per kind."""
        user = a["member"]
        if user not in self.members or user == self.cfg.hyle:
            return []
        last = a.setdefault("fb", {}).get(kind, 0)
        if now - last < self.cfg.agent_feedback_cooldown_min * 60:
            return []
        a["fb"][kind] = now
        return [Outgoing(f"name:1on1-{user}", text)]

    def on_agent(self, inc: Incoming, now: Optional[float] = None) -> List[Outgoing]:
        now = now or time.time()
        props = dict(inc.agent_props or {})
        user = props.get("member") or inc.username
        state = props.get("state") or inc.agent_state or "?"
        prev = self.agents.get(user, {})
        a = {**prev, **{k: str(v) for k, v in props.items() if k != "amolla_agent"}}
        a.update(member=user, state=state, at=now, text=inc.message[:300])
        if state != prev.get("state"):
            a["since"] = now
        was_silent = prev.get("silent_flagged", False)
        a["silent_flagged"] = False
        self.agents[user] = a
        outs: List[Outgoing] = []
        if was_silent and state != "offline":
            outs += [Outgoing(f"name:1on1-{user}", f"🟢 @{user} agent-loop 다시 연결됐어요. 고마워요!")] if user in self.members and user != self.cfg.hyle else []
        if state == "error" and prev.get("state") != "error":
            outs += self._feedback(a, "error", f"🔴 @{user} 노트북 작업이 실패했어요. 바로 위 스레드의 마지막 줄을 보고, 모르겠으면 여기에 그대로 붙여 물어보세요. "
                                   f"@{self.cfg.hyle} 참고.", now)
        try:
            dirty = int(a.get("dirty", "0"))
        except ValueError:
            dirty = 0
        if state == "idle" and dirty > 0 and now - a.get("since", now) >= 15 * 60:
            outs += self._feedback(a, "dirty", f"🟡 @{user} 커밋 안 된 파일이 {dirty}개 있어요 (`{a.get('branch', '?')}`). 이대로면 다음 `!task`가 시작되지 않아요. "
                                   "Codex/agy에게 \"지금 변경을 이슈 브랜치에 커밋하고 PR 올려줘\"라고 하거나, 버려도 되면 Hylē에게 물어보세요.", now)
        return outs

    def check_silence(self, now: Optional[float] = None) -> List[Outgoing]:
        """Called every minute by run_live: flag laptops silent > agent_silent_min (once per silence)."""
        now = now or time.time()
        outs: List[Outgoing] = []
        for user, a in self.agents.items():
            if a.get("silent_flagged") or a.get("state") == "offline":
                continue
            if now - a["at"] > self.cfg.agent_silent_min * 60:
                a["silent_flagged"] = True
                mins = int((now - a["at"]) // 60)
                if user in self.members and user != self.cfg.hyle:
                    outs.append(Outgoing(f"name:1on1-{user}", f"⚠️ @{user} 노트북 agent-loop 소식이 {mins}분째 없어요. 노트북이 잠들었거나 터미널이 닫혔을 수 있어요. "
                                         f"한 줄 설치 명령을 다시 실행해 주세요. @{self.cfg.hyle} 참고."))
        return outs

    def agent_summary(self, channel_name: Optional[str] = None, now: Optional[float] = None) -> str:
        """Aggregated laptop check-ins for !status."""
        now = now or time.time()
        if channel_name and channel_name.startswith("1on1-"):
            users = [channel_name[len("1on1-"):]]
        else:
            users = [u for u in self.members if u != self.cfg.hyle] + [u for u in self.agents if u not in self.members or u == self.cfg.hyle]
        lines = [f"노트북 agent-loop (⚠️ = {self.cfg.agent_silent_min:g}분 넘게 소식 없음):"]
        for u in users:
            a = self.agents.get(u)
            name = self.members[u].name if u in self.members else u
            if not a:
                lines.append(f"- {name} (@{u}): ⚪ 기록 없음 (미설치이거나 bridge 재시작 뒤 아직 check-in 없음)")
                continue
            mins = int((now - a["at"]) // 60)
            if a.get("state") == "offline":
                icon = "⚫ 꺼짐"
            elif now - a["at"] > self.cfg.agent_silent_min * 60:
                icon = "⚠️ 응답 없음"
            else:
                icon = {"idle": "🟢", "busy": "🟡", "error": "🔴"}.get(a.get("state", ""), "⚪")
            lines.append(f"- {name} (@{u}): {icon} {a.get('state', '?')} · 작업 {a.get('task', '-')} · `{a.get('branch', '?')}` · "
                         f"{a.get('commit', '?')} · 변경 {a.get('dirty', '?')} · {mins}분 전")
        return "\n".join(lines)

    def build_system(self, channel_name: str, member: Member) -> str:
        ov = self.st(channel_name).overrides
        overrides = ""
        if ov:
            overrides = "## Hylē 우선 지시 (최신이 마지막, 반드시 반영)\n" + "\n".join(f"- {o}" for o in ov[-10:]) + "\n"
        return SYSTEM_TEMPLATE.format(
            now=_now(),
            hyle=self.cfg.hyle,
            name=member.name,
            username=member.username,
            role=member.role,
            area=member.area,
            git_rule=GIT_RULE if member.uses_git else MATLAB_RULE,
            overrides=overrides,
            github=self.gh.summary(member if member.username in self.members else None),
            docs=self.docs.text(),
        )

    def _ask(self, channel_name: str, member: Member, user_text: str, remember: bool = True) -> str:
        st = self.st(channel_name)
        history = st.history[-self.cfg.history_turns:]
        msgs = history + [{"role": "user", "content": user_text}]
        try:
            reply = self.llm.complete(self.build_system(channel_name, member), msgs)
        except Exception as exc:
            log.exception("LLM error")
            return f"⚠️ LLM 호출 실패: {type(exc).__name__}. Hylē에게 알려주세요."
        if not reply:
            reply = "⚠️ 빈 응답이에요. 다시 질문해 주세요."
        if remember:
            st.history = (history + [{"role": "user", "content": user_text[:4000]}, {"role": "assistant", "content": reply[:6000]}])[
                -self.cfg.history_turns:
            ]
            self.save_state()
        return reply


def extract_prompt(reply: str) -> str:
    """First fenced code block of an LLM reply (the copy-paste prompt)."""
    m = re.search(r"```[a-zA-Z]*\n(.*?)```", reply, re.S)
    return m.group(1).strip() if m else ""


def _now() -> str:
    os.environ.setdefault("TZ", "Asia/Seoul")
    try:
        time.tzset()
    except AttributeError:
        pass
    return time.strftime("%m-%d %H:%M")


def split_message(text: str, limit: int = MAX_POST) -> List[str]:
    if len(text) <= limit:
        return [text]
    parts, cur = [], ""
    for line in text.splitlines(keepends=True):
        while len(line) > limit:
            if cur:
                parts.append(cur)
                cur = ""
            parts.append(line[:limit])
            line = line[limit:]
        if len(cur) + len(line) > limit:
            parts.append(cur)
            cur = ""
        cur += line
    if cur:
        parts.append(cur)
    return parts


# --------------------------------------------------------------------------- Mattermost
class Mattermost:
    def __init__(self, cfg: Config, post: bool = True):
        self.cfg, self.do_post = cfg, post
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {cfg.mm_token}"
        self._users: Dict[str, str] = {}
        self._chan_by_name: Dict[str, str] = {}
        self.me = self.api("GET", "/users/me")
        self.team = self.api("GET", f"/teams/name/{cfg.team}")

    def api(self, method: str, path: str, **kw):
        r = self.s.request(method, f"{self.cfg.mm_url}/api/v4{path}", timeout=30, **kw)
        r.raise_for_status()
        return r.json() if r.content else {}

    def username(self, user_id: str) -> str:
        if user_id not in self._users:
            self._users[user_id] = self.api("GET", f"/users/{user_id}").get("username", user_id)
        return self._users[user_id]

    def channel_id(self, ref: str) -> str:
        if not ref.startswith("name:"):
            return ref
        name = ref[5:]
        if name not in self._chan_by_name:
            self._chan_by_name[name] = self.api("GET", f"/teams/{self.team['id']}/channels/name/{name}")["id"]
        return self._chan_by_name[name]

    def send(self, out: Outgoing) -> None:
        for chunk in split_message(out.message):
            if not self.do_post:
                print(f"\n--- [no-post] -> {out.channel} root={out.root_id}\n{chunk}\n")
                continue
            self.api("POST", "/posts", json={"channel_id": self.channel_id(out.channel), "message": chunk, "root_id": out.root_id})

    def channel_name(self, channel_id: str) -> str:
        for name, cid in self._chan_by_name.items():
            if cid == channel_id:
                return name
        name = self.api("GET", f"/channels/{channel_id}").get("name", "")
        self._chan_by_name[name] = channel_id
        return name

    def parse_event(self, ev: dict) -> Optional[Incoming]:
        if ev.get("event") not in ("posted", "post_edited"):
            return None
        data = ev.get("data", {})
        post = json.loads(data.get("post", "{}"))
        props = post.get("props") or {}
        if post.get("user_id") == self.me["id"] or post.get("type"):
            return None
        if props.get("amolla_agent"):  # laptop agent-loop (posts as the member) -> heartbeat bookkeeping only
            return Incoming(
                channel_id=post.get("channel_id", ""),
                channel_name=data.get("channel_name") or self.channel_name(post.get("channel_id", "")),
                channel_type=data.get("channel_type", "P"),
                user_id=post.get("user_id", ""),
                username=self.username(post.get("user_id", "")),
                message=post.get("message", ""),
                post_id=post.get("id", ""),
                agent_kind=str(props.get("amolla_agent")),
                agent_state=str(props.get("state", "")),
                agent_props=props,
            )
        if ev.get("event") != "posted" or props.get("from_bot") == "true":
            return None
        mentions = json.loads(data.get("mentions", "[]") or "[]")
        msg = post.get("message", "")
        mentioned = self.me["id"] in mentions or f"@{self.cfg.bot_username}" in msg
        msg = msg.replace(f"@{self.cfg.bot_username}", "").strip()
        return Incoming(
            channel_id=post.get("channel_id", ""),
            channel_name=data.get("channel_name", ""),
            channel_type=data.get("channel_type", ""),
            user_id=post.get("user_id", ""),
            username=(data.get("sender_name", "") or "").lstrip("@") or self.username(post.get("user_id", "")),
            message=msg,
            post_id=post.get("id", ""),
            root_id=post.get("root_id", ""),
            mentioned=mentioned,
            file_count=len(post.get("file_ids") or []),
        )


async def run_live(orch: Orchestrator, mm: Mattermost) -> None:
    import websockets  # lazy import

    ws_url = re.sub(r"^http", "ws", orch.cfg.mm_url) + "/api/v4/websocket"
    locks: Dict[str, asyncio.Lock] = {}
    backoff = 1
    asyncio.create_task(_silence_watch(orch, mm))
    while True:
        try:
            async with websockets.connect(ws_url, ping_interval=20, ping_timeout=20, max_size=8 * 2**20) as ws:
                await ws.send(json.dumps({"seq": 1, "action": "authentication_challenge", "data": {"token": orch.cfg.mm_token}}))
                log.info("websocket connected as @%s", mm.me["username"])
                backoff = 1
                async for raw in ws:
                    try:
                        inc = mm.parse_event(json.loads(raw))
                    except Exception:
                        log.exception("bad event")
                        continue
                    if inc is None:
                        continue
                    lock = locks.setdefault(inc.channel_id, asyncio.Lock())
                    asyncio.create_task(_process(orch, mm, inc, lock))
        except Exception as exc:
            log.warning("websocket error: %s; reconnect in %ss", exc, backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)


async def _silence_watch(orch: Orchestrator, mm: Mattermost, every: float = 60.0) -> None:
    """Flag laptop agent-loops that stopped checking in (see Orchestrator.check_silence)."""
    while True:
        await asyncio.sleep(every)
        try:
            for o in orch.check_silence():
                await asyncio.to_thread(mm.send, o)
        except Exception:
            log.exception("silence watch failed")


async def _process(orch: Orchestrator, mm: Mattermost, inc: Incoming, lock: asyncio.Lock) -> None:
    async with lock:
        try:
            outs = await asyncio.to_thread(orch.handle, inc)
            for o in outs:
                await asyncio.to_thread(mm.send, o)
        except Exception:
            log.exception("handle failed for post %s", inc.post_id)


def run_dry(orch: Orchestrator, stream=sys.stdin) -> None:
    """Offline REPL. Line format: '<username>[@channel]: message'. Default channel = 1on1-<username>
    (or 1on1-<x> when Hylē writes 'hyle@1on1-jieun: ...'). Use '!' commands as in chat."""
    print("dry-run. 예) 'jieun: 지도 어디서부터?'  'hyle@1on1-jieun: 오늘은 S1만'  'hyle@backend: !assign 우찬 #2'  (Ctrl-D 종료)")
    for line in stream:
        line = line.rstrip("\n")
        if ":" not in line:
            continue
        who, msg = line.split(":", 1)
        user, _, chan = who.strip().partition("@")
        chan = chan or f"1on1-{user}"
        inc = Incoming(chan, chan, "P" if chan.startswith("1on1-") else "O", user, user, msg.strip(),
                       post_id="dry", mentioned="@orchestrator" in msg)
        inc.message = inc.message.replace("@orchestrator", "").strip()
        outs = orch.handle(inc)
        if not outs:
            print("(봇 응답 없음 — 저장만 됨)" if user == orch.cfg.hyle else "(응답 없음)")
        for o in outs:
            print(f"\n--- -> {o.channel}\n{o.message}\n")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="offline REPL on stdin (no Mattermost)")
    ap.add_argument("--mock-llm", action="store_true", help="fake LLM (no API key)")
    ap.add_argument("--no-post", action="store_true", help="live listen but print replies instead of posting")
    ap.add_argument("--env", default=str(HERE / ".env"))
    a = ap.parse_args(argv)
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv(Path(a.env))
    cfg = Config.from_env()
    llm: LLM = MockLLM() if a.mock_llm else OpenAILLM(cfg)
    orch = Orchestrator(cfg, llm, GitHubContext(cfg), DocsContext(cfg), load_members(cfg.members_tsv))
    if a.dry_run:
        run_dry(orch)
        return 0
    if not cfg.mm_token:
        raise SystemExit("MM_BOT_TOKEN missing (run infra/chat/provision.sh)")
    mm = Mattermost(cfg, post=not a.no_post)
    asyncio.run(run_live(orch, mm))
    return 0


if __name__ == "__main__":
    sys.exit(main())
