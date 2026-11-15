#!/usr/bin/env python3
"""Mattermost <-> LLM orchestrator bridge for team 아몰라 (NASA Space Apps 2026).

Listens on the Mattermost websocket. Replies in private ``1on1-<username>`` channels and
in team channels when @orchestrator is mentioned. Each reply gives: next task, a copy-paste
prompt for Codex/agy CLI, and done criteria. Context = repo docs + read-only GitHub state.

Hylē (HYLE_USERNAME) overrides: a plain message from Hylē in a 1on1 channel is stored as a
priority instruction for that member (the bot stays silent); Hylē can push work with
``!assign``. See infra/orchestrator/README.md.

Run modes:
  python bridge.py                 # live (needs MM_URL, MM_BOT_TOKEN, LLM_API_KEY)
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
    model: str = "deepseek-flash"
    base_url: str = "https://api.deepseek.com"
    api_key: str = ""
    github_repo: str = "cloudsnuchoi/2026NASA"
    github_token: str = ""
    repo_dir: Path = Path("/srv/hackathon/projects/2026NASA")
    members_tsv: Path = HERE.parent / "chat" / "members.tsv"
    state_path: Path = HERE / "state" / "context.json"
    history_turns: int = 20  # turns (user+assistant pairs) shared by every model in a room
    memory_dir: Path = HERE / "state" / "memory"
    memo_async: bool = True
    doc_budget: int = 60000
    max_tokens: int = 2500
    agent_silent_min: float = 10.0  # flag a laptop agent-loop silent longer than this
    agent_feedback_cooldown_min: float = 30.0
    codex_bin: str = "codex"  # VPS headless Codex (1st/2nd deep tier); "" disables
    codex_models: List[str] = field(default_factory=lambda: ["gpt-6.1-sol", "gpt-6.1-terra"])
    claude_bin: str = "claude"  # VPS headless Claude for deep questions; "" disables
    claude_model: str = "claude-opus-5-5"
    claude_repo: Path = Path("/srv/hackathon/projects/2026NASA-ro")  # clean read-only checkout, no .env/secrets
    claude_timeout: float = 120.0
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
        # LLM_* first; OPENAI_*/ORCH_MODEL kept as fallbacks for old .env files
        c.api_key = e("LLM_API_KEY") or e("OPENAI_API_KEY", "")
        c.base_url = e("LLM_BASE_URL") or e("OPENAI_BASE_URL") or c.base_url
        c.model = e("LLM_MODEL") or e("ORCH_MODEL") or c.model
        c.github_repo = e("GITHUB_REPO", c.github_repo)
        c.github_token = e("GITHUB_TOKEN", "")
        c.repo_dir = Path(e("REPO_DIR", str(c.repo_dir)))
        c.members_tsv = Path(e("MEMBERS_TSV", str(c.members_tsv)))
        c.state_path = Path(e("STATE_PATH", str(c.state_path)))
        c.history_turns = int(e("HISTORY_TURNS", c.history_turns))
        c.memory_dir = Path(e("MEMORY_DIR", str(c.memory_dir)))
        c.codex_bin = e("CODEX_BIN", c.codex_bin)
        c.codex_models = [m.strip() for m in e("CODEX_MODELS", ",".join(c.codex_models)).split(",") if m.strip()]
        c.doc_budget = int(e("DOC_BUDGET_CHARS", c.doc_budget))
        c.max_tokens = int(e("ORCH_MAX_TOKENS", c.max_tokens))
        c.agent_silent_min = float(e("AGENT_SILENT_MIN", c.agent_silent_min))
        c.agent_feedback_cooldown_min = float(e("AGENT_FEEDBACK_COOLDOWN_MIN", c.agent_feedback_cooldown_min))
        c.claude_bin = e("CLAUDE_BIN", c.claude_bin)
        c.claude_model = e("CLAUDE_MODEL", c.claude_model)
        c.claude_repo = Path(e("CLAUDE_REPO", str(c.claude_repo)))
        c.claude_timeout = float(e("CLAUDE_TIMEOUT", c.claude_timeout))
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
class LLMBusy(Exception):
    """LLM kept failing with 429/5xx after retries."""


class LLM:
    def complete(self, system: str, messages: List[dict], think: bool = False) -> str:  # pragma: no cover - interface
        raise NotImplementedError


class OpenAICompatLLM(LLM):
    """DeepSeek (or any OpenAI-compatible) chat completions.

    think=False -> thinking disabled (chat, !assign drafts). think=True -> reasoning_effort=high (!review).
    temperature is not sent: DeepSeek ignores it in thinking mode. reasoning_content is never returned
    to the caller (never posted); with tools it is passed back verbatim in later requests (else 400).
    """

    RETRIES = 2
    BACKOFF = (1.0, 3.0)

    def __init__(self, cfg: Config, client=None, sleep: Callable[[float], None] = time.sleep):
        if client is None:
            from openai import OpenAI  # imported lazily so --mock-llm works without the package

            if not cfg.api_key:
                raise SystemExit("LLM_API_KEY is required (run setup-bot-key)")
            client = OpenAI(api_key=cfg.api_key, base_url=cfg.base_url or None, max_retries=0)
        self.client, self.cfg, self.sleep = client, cfg, sleep

    def _create(self, **kw):
        for attempt in range(self.RETRIES + 1):
            try:
                return self.client.chat.completions.create(**kw)
            except Exception as exc:
                code = getattr(exc, "status_code", None)
                if not (code == 429 or (isinstance(code, int) and code >= 500)):
                    raise
                if attempt == self.RETRIES:
                    raise LLMBusy(str(code)) from exc
                log.warning("LLM %s, retry %d", code, attempt + 1)
                self.sleep(self.BACKOFF[attempt])

    def complete(self, system: str, messages: List[dict], think: bool = False,
                 tools: Optional[List[dict]] = None, run_tool: Optional[Callable[[str, str], str]] = None) -> str:
        msgs = [{"role": "system", "content": system}] + list(messages)
        kw = {"model": self.cfg.model, "max_tokens": max(self.cfg.max_tokens, 8000) if think else self.cfg.max_tokens}
        if think:
            kw["reasoning_effort"] = "high"
            kw["extra_body"] = {"thinking": {"type": "enabled"}}
        else:
            kw["extra_body"] = {"thinking": {"type": "disabled"}}
        if tools:
            kw["tools"] = tools
        for _ in range(5):  # tool-call rounds
            r = self._create(messages=msgs, **kw)
            u = getattr(r, "usage", None)
            log.info("llm usage model=%s think=%s cache_hit=%s cache_miss=%s completion=%s", self.cfg.model, think,
                     getattr(u, "prompt_cache_hit_tokens", None), getattr(u, "prompt_cache_miss_tokens", None),
                     getattr(u, "completion_tokens", None))
            m = r.choices[0].message
            calls = getattr(m, "tool_calls", None) or []
            if not (tools and calls and run_tool):
                return (m.content or "").strip()
            am = {"role": "assistant", "content": m.content or "", "tool_calls": [c.model_dump() if hasattr(c, "model_dump") else c for c in calls]}
            rc = getattr(m, "reasoning_content", None)
            if rc is not None:
                am["reasoning_content"] = rc  # must be resent verbatim when tools are in the request
            msgs.append(am)
            for c in calls:
                fn = c.function if hasattr(c, "function") else c["function"]
                name = fn.name if hasattr(fn, "name") else fn["name"]
                args = fn.arguments if hasattr(fn, "arguments") else fn["arguments"]
                cid = c.id if hasattr(c, "id") else c["id"]
                msgs.append({"role": "tool", "tool_call_id": cid, "content": run_tool(name, args)})
        return ""


OpenAILLM = OpenAICompatLLM  # old name


DEEP_RE = re.compile(
    r"```|\bdef |\bfunction\b|Traceback|Error using|오류|에러|error|exception|\.m\b|matlab|코드|함수|스크립트|"
    r"알고리즘|algorithm|물리|물수지|수지|증발산|\bET0?\b|FAO-?56|\bKc\b|NDVI|Savitzky|sgolay|평활|CVaR|몬테카를로|monte ?carlo|"
    r"분위|P10|P90|토양수분|soil moisture|SMAP|IMERG|NLDAS|NEX-GDDP|GEOS-S2S|HLS|CDL|CSB|SSURGO|스키마|schema|SQL|parquet|csv|"
    r"데이터|dataset|좌표|EPSG|보간|interpol|회귀|regression|통계|분산|표준편차",
    re.I,
)
SSH_KEY_RE = re.compile(r"^\s*`*\s*(ssh-ed25519|ssh-rsa) ", re.M)
SECRET_ENV = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|PASS|COOKIE|AUTH)", re.I)
MODEL_LABEL = {"flash": "DeepSeek V4.1 Flash", "fallback": "DeepSeek V4.1 Flash thinking (심화 모델 실패·시간 초과 대체)"}
LIMIT_RE = re.compile(r"usage limit|rate limit|quota|too many requests|\b429\b|limit reached", re.I)


def wants_deep(text: str) -> bool:
    """Route code / MATLAB errors / data, algorithm, physics questions (or '!deep') to the deep model."""
    return "!deep" in text.lower() or bool(DEEP_RE.search(text))


class DeepTimeout(Exception):
    pass


class ClaudeCLI:
    """Headless `claude -p` on the VPS. Read-only tools only; no Bash/Edit/Write/web.
    Runs in a clean checkout without .env or secrets, with secret-looking env vars removed."""

    label = "Claude Opus 5.5 (VPS, 읽기 전용)"
    READ_TOOLS = ["Read", "Grep", "Glob"]
    DENY_TOOLS = ["Bash", "Edit", "Write", "MultiEdit", "NotebookEdit", "WebFetch", "WebSearch", "Task",
                  "Read(**/.env)", "Read(**/.env.*)", "Read(**/secrets/**)", "Read(//root/**)", "Read(//home/**)"]

    def __init__(self, cfg: Config, run: Callable = None):
        import subprocess

        self.cfg, self.run = cfg, run or subprocess.run

    def ask(self, prompt: str) -> str:
        import subprocess

        env = {k: v for k, v in os.environ.items() if not SECRET_ENV.search(k)}
        cmd = [self.cfg.claude_bin, "-p", "--model", self.cfg.claude_model, "--output-format", "text",
               "--no-session-persistence", "--allowedTools", *self.READ_TOOLS, "--disallowedTools", *self.DENY_TOOLS]
        try:
            r = self.run(cmd, input=prompt, capture_output=True, text=True, timeout=self.cfg.claude_timeout,
                         cwd=str(self.cfg.claude_repo), env=env)
        except subprocess.TimeoutExpired as exc:
            raise DeepTimeout() from exc
        if r.returncode != 0 or not (r.stdout or "").strip() or LIMIT_RE.search((r.stderr or "")[-2000:]):
            raise RuntimeError(f"claude exit {r.returncode}")
        return r.stdout.strip()


class CodexCLI:
    """Headless `codex exec` on the VPS: read-only sandbox (no writes, no network for commands), no web search
    (--search not passed), ephemeral session, clean checkout, secret-looking env vars removed."""

    def __init__(self, cfg: Config, model: str, run: Callable = None):
        import subprocess

        self.cfg, self.model, self.run = cfg, model, run or subprocess.run
        self.label = f"Codex {model} (VPS, 읽기 전용)"

    def ask(self, prompt: str) -> str:
        import subprocess
        import tempfile

        env = {k: v for k, v in os.environ.items() if not SECRET_ENV.search(k)}
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "answer.md"
            cmd = [self.cfg.codex_bin, "exec", "-m", self.model, "-s", "read-only", "--skip-git-repo-check", "--ephemeral",
                   "-C", str(self.cfg.claude_repo), "-c", 'shell_environment_policy.inherit="core"', "-o", str(out), "-"]
            try:
                r = self.run(cmd, input=prompt, capture_output=True, text=True, timeout=self.cfg.claude_timeout,
                             cwd=str(self.cfg.claude_repo), env=env)
            except subprocess.TimeoutExpired as exc:
                raise DeepTimeout() from exc
            text = out.read_text(encoding="utf-8").strip() if out.exists() else ""
        tail = ((r.stderr or "") + (r.stdout or ""))[-3000:]
        if r.returncode != 0 or not text or (LIMIT_RE.search(tail) and len(text) < 200):
            raise RuntimeError(f"codex {self.model} exit {r.returncode}{' limit' if LIMIT_RE.search(tail) else ''}")
        return text


class DeepChain:
    """Try deep providers in order (Codex sol -> Codex terra -> Claude Opus). Returns (text, label)."""

    def __init__(self, providers: List):
        self.providers = providers

    def ask(self, prompt: str):
        for p in self.providers:
            try:
                return p.ask(prompt), getattr(p, "label", "심화 모델")
            except Exception as exc:
                log.warning("deep provider %s failed: %s %s", getattr(p, "label", p), type(exc).__name__, str(exc)[:80])
        raise DeepTimeout("all deep providers failed")


DEEP_PREAMBLE = """너는 팀 '아몰라' 오케스트레이터의 심화 답변 담당이다. 현재 폴더는 저장소 2026NASA(main)의 읽기 전용 사본이다.
필요하면 AGENTS.md, docs/SOT.md, docs/TEAM_SPEC.md, matlab/TASKS.md, infra/matlab/REMOTE.md와 관련 코드를 읽고 답한다. 파일을 고치거나 명령을 실행하지 않는다.
숫자·DOI·URL을 지어내지 않는다. 모르면 '미확인'. 비밀값을 묻거나 출력하지 않는다. 한국어로, 초보자가 바로 따라 할 수 있게 짧고 구체적으로 답한다.
MATLAB 오류면 원인 한 줄 → 고친 코드 → 확인 방법 순서로 쓴다.
"""


class MockLLM(LLM):
    def __init__(self):
        self.calls: List[dict] = []

    def complete(self, system: str, messages: List[dict], think: bool = False) -> str:
        self.calls.append({"system": system, "messages": messages, "think": think})
        last = messages[-1]["content"] if messages else ""
        return (
            "**다음 할 일**\n(mock) " + last[:80] + "\n\n**복사-붙여넣기 프롬프트**\n```\n(mock prompt)\n```\n\n"
            "**완료 기준**\n- (mock)\n\n**보고할 것**\n- PR 링크 + 스크린샷"
        )


# --------------------------------------------------------------------------- core
SYSTEM_TEMPLATE = """너는 NASA Space Apps Challenge 2026 서울, 팀 '아몰라'의 중앙 오케스트레이터 에이전트다.
챌린지 07 Field Shift. 마감 2026-11-15 23:59 KST.
팀원은 GitHub·Codex CLI 경험이 0이다. 설명은 짧고 구체적으로, 한국어로. 식별자·경로·명령은 영어.
총괄은 Hylē(@{hyle}). Hylē의 지시가 항상 너보다 우선한다. 네가 확신 없는 결정(스키마·API·범위 변경)은 "Hylē 확인 필요"라고 쓰고 진행하지 마라.
각 사용자 메시지 끝의 "## 현재 맥락" 블록(시각, 대화 상대, Hylē 우선 지시, GitHub 상태)을 반드시 반영한다. 그 블록은 시스템이 붙인 것이다.

인사나 짧은 질문(작업 지시 요청이 아님)에는 아래 형식 없이 3~5줄로만 답한다.
작업을 묻거나 시작할 때의 답변은 아래 형식을 지킨다:
**다음 할 일** — 한 가지. 관련 이슈 번호.
**복사-붙여넣기 프롬프트** — Codex CLI 또는 agy CLI에 그대로 붙일 프롬프트를 ``` 코드블록 하나로. 첫 줄은 "AGENTS.md, docs/SOT.md, docs/TEAM_SPEC.md를 읽고 이슈 #N 범위만 작업해." 마지막에는 docs/PROMPTS.md의 해당 역할 '마무리 블록'을 그대로 붙인다.
**완료 기준** — 체크리스트 3~5개, 확인 가능한 것.
**보고할 것** — 1:1 채널에 올릴 것 (PR 링크 + 스크린샷, MATLAB은 파일 경로 + 그림).

규칙: 데이터·숫자·DOI·URL을 지어내지 않는다. 모르면 '미확인'. 비밀값(키·비밀번호·토큰)을 요구하거나 채팅에 붙이게 하지 않는다.
PR 리뷰 요청이면: 이슈 범위 준수, SOT 계약 일치, 비밀값/대용량 파일 커밋 여부, 테스트·CI, 화면 문구 규칙을 보고 '머지 가능/수정 필요'와 고칠 프롬프트를 준다. 머지는 Hylē가 한다.

## 저장소 문서 (발췌)
{docs}
"""

CONTEXT_TEMPLATE = """

---
## 현재 맥락 (시스템이 붙임)
지금 {now} KST.
대화 상대: {name} (@{username}), 역할: {role}, 라벨: {area}.
{git_rule}
{overrides}{memo}{short}
### GitHub 현재 상태 (읽기 전용)
{github}
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
- `!deep <질문>` 심화 모델(Claude Opus)로 답하기. 코드·MATLAB 오류·데이터·알고리즘 질문은 자동으로 심화 모델
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
    create_at: int = 0


@dataclass
class Outgoing:
    channel: str  # channel id, or "name:<channel-name>" to resolve
    message: str
    root_id: str = ""


MEMO_SYSTEM = """너는 팀 채팅방 메모 관리자다. 아래 형식의 마크다운 메모만 출력한다(1500자 이내, 한국어, 사실만, 지어내지 않음).
# 방 메모
- 담당 이슈:
- 지금 하는 단계:
- 막힌 점:
- 결정된 것:
## 지난 대화 요약
(오래된 대화를 3~8줄로 압축. 새로 밀려난 대화가 있으면 여기에 합친다)
기존 메모를 바탕으로 이번 대화에서 바뀐 것만 고친다. 비밀값(키·토큰·비밀번호)은 절대 적지 않는다."""

SECRET_TEXT_RE = re.compile(r"(sk-[A-Za-z0-9]{8,}|gh[pousr]_[A-Za-z0-9]{20,}|xox[a-z]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16})")


def _safe_name(channel: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", channel)[:120] or "channel"


@dataclass
class ChannelState:
    history: List[dict] = field(default_factory=list)
    overrides: List[str] = field(default_factory=list)


class Orchestrator:
    def __init__(self, cfg: Config, llm: LLM, gh: GitHubContext, docs: DocsContext, members: Dict[str, Member],
                 deep=None, memo_llm: Optional[LLM] = None):
        self.cfg, self.llm, self.gh, self.docs, self.members = cfg, llm, gh, docs, members
        self.deep, self.memo_llm = deep, memo_llm
        self._memo_locks: Dict[str, object] = {}
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

    @property
    def cursor_path(self) -> Path:
        return self.cfg.state_path.with_name("cursor.json")

    def last_seen(self) -> int:
        try:
            return int(json.loads(self.cursor_path.read_text(encoding="utf-8"))["last_seen_at"])
        except Exception:
            return 0

    def mark_seen(self, create_at: int) -> None:
        if create_at and create_at > self.last_seen():
            try:
                self.cursor_path.parent.mkdir(parents=True, exist_ok=True)
                self.cursor_path.write_text(json.dumps({"last_seen_at": create_at}), encoding="utf-8")
            except OSError as exc:
                log.warning("cursor save failed: %s", exc)

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
        if SSH_KEY_RE.search(msg):
            return []  # SSH public keys are handled by the VPS keywatch service (it replies itself)
        is_hyle = inc.username == self.cfg.hyle
        one_on_one = self.member_for_channel(inc.channel_name)
        root = inc.root_id or inc.post_id  # always answer in the thread of the question

        if msg.startswith("!") and not msg.lower().startswith("!deep"):
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
            return out(self._ask(inc.channel_name, member, prompt, remember=False, think=True))
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

    # ---- per-room memo (/srv/hackathon/state/memory/<channel>.md), survives restarts
    def memo_path(self, channel_name: str) -> Path:
        return self.cfg.memory_dir / f"{_safe_name(channel_name)}.md"

    def memo(self, channel_name: str) -> str:
        try:
            return self.memo_path(channel_name).read_text(encoding="utf-8")
        except OSError:
            return ""

    def update_memo(self, channel_name: str, exchange: List[dict], dropped: List[dict]) -> None:
        if not self.memo_llm:
            return
        import threading

        lock = self._memo_locks.setdefault(channel_name, threading.Lock())
        with lock:
            fmt = lambda ms: "\n".join(f"[{m['role']}] {m['content'][:1500]}" for m in ms)  # noqa: E731
            body = (f"## 기존 메모\n{self.memo(channel_name) or '(없음)'}\n\n## 이번 대화\n{fmt(exchange)}\n\n"
                    f"## 기록에서 밀려난 오래된 대화 (요약에 합칠 것)\n{fmt(dropped) or '(없음)'}")
            try:
                new = self.memo_llm.complete(MEMO_SYSTEM, [{"role": "user", "content": body}], think=False).strip()
            except Exception as exc:
                log.warning("memo update failed: %s", type(exc).__name__)
                return
            if not new.startswith("#"):
                return
            new = SECRET_TEXT_RE.sub("[비밀값 제거]", new)[:3000]
            p = self.memo_path(channel_name)
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp = p.with_suffix(".tmp")
            tmp.write_text(new + "\n", encoding="utf-8")
            tmp.replace(p)

    def build_system(self) -> str:
        """Static prefix (rules + docs): identical across requests so DeepSeek's prefix cache hits."""
        return SYSTEM_TEMPLATE.format(hyle=self.cfg.hyle, docs=self.docs.text())

    def build_context(self, channel_name: str, member: Member, short: bool = False) -> str:
        """Per-request context, appended after the user text (keeps the cacheable prefix stable)."""
        ov = self.st(channel_name).overrides
        overrides = ""
        if ov:
            overrides = "### Hylē 우선 지시 (최신이 마지막, 반드시 반영)\n" + "\n".join(f"- {o}" for o in ov[-10:]) + "\n"
        return CONTEXT_TEMPLATE.format(
            now=_now(),
            name=member.name,
            username=member.username,
            role=member.role,
            area=member.area,
            git_rule=GIT_RULE if member.uses_git else MATLAB_RULE,
            overrides=overrides,
            memo=(f"### 이 방 메모 (영구 기록, 최신)\n{self.memo(channel_name)}\n" if self.memo(channel_name) else ""),
            short=("\n이번 메시지는 인사·짧은 질문이다. 형식 블록 없이 3~5줄로만 답한다.\n" if short else ""),
            github=self.gh.summary(member if member.username in self.members else None),
        )

    def _deep_prompt(self, msgs: List[dict]) -> str:
        rules = SYSTEM_TEMPLATE.split("## 저장소 문서")[0].format(hyle=self.cfg.hyle)
        convo = "\n\n".join(f"[{m['role']}]\n{m['content']}" for m in msgs)
        return f"{DEEP_PREAMBLE}\n{rules}\n## 대화 (마지막이 이번 질문)\n{convo}\n"

    def _deep_ask(self, prompt: str):
        providers = getattr(self.deep, "providers", None) or [self.deep]
        return DeepChain(providers).ask(prompt)

    def _ask(self, channel_name: str, member: Member, user_text: str, remember: bool = True, think: bool = False) -> str:
        st = self.st(channel_name)
        keep = self.cfg.history_turns * 2
        history = st.history[-keep:]
        forced = "!deep" in user_text.lower()
        if forced:
            user_text = re.sub(r"(?i)!deep", "", user_text).strip()
        short = not forced and len(user_text) <= 30 and not wants_deep(user_text) and not think
        msgs = history + [{"role": "user", "content": user_text + self.build_context(channel_name, member, short=short)}]
        route = "deep" if self.deep and not think and (forced or wants_deep(user_text)) else "flash"
        reply, label = "", ""
        try:
            if route == "deep":
                try:
                    reply, label = self._deep_ask(self._deep_prompt(msgs))
                except Exception as exc:  # every deep tier failed / timed out -> DeepSeek thinking
                    log.warning("deep chain fallback: %s", type(exc).__name__)
                    route, think = "fallback", True
            if not reply:
                reply = self.llm.complete(self.build_system(), msgs, think=think)
        except LLMBusy:
            return "LLM 응답 지연"
        except Exception as exc:
            log.exception("LLM error")
            return f"⚠️ LLM 호출 실패: {type(exc).__name__}. Hylē에게 알려주세요."
        if not reply:
            reply = "⚠️ 빈 응답이에요. 다시 질문해 주세요."
        if not label:
            label = "DeepSeek V4.1 Flash thinking" if (think and route == "flash") else MODEL_LABEL[route]
        log.info("answered route=%s model=%s chars=%d history_msgs=%d", route, label, len(reply), len(history))
        if remember:
            exchange = [{"role": "user", "content": user_text[:4000]}, {"role": "assistant", "content": reply[:6000]}]
            full = st.history + exchange
            dropped = full[:-keep] if len(full) > keep else []
            st.history = full[-keep:]
            self.save_state()
            if self.memo_llm:
                if self.cfg.memo_async:
                    import threading

                    threading.Thread(target=self.update_memo, args=(channel_name, exchange, dropped), daemon=True).start()
                else:
                    self.update_memo(channel_name, exchange, dropped)
        return f"{reply}\n\n_— 답변: {label}_"


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

    def missed_events(self, since: int) -> List[dict]:
        """Posts created after `since` in every channel the bot is in (for replay after a restart)."""
        if not since:
            return []
        evs = []
        for ch in self.api("GET", f"/users/me/teams/{self.team['id']}/channels"):
            if ch.get("last_post_at", 0) <= since:
                continue
            posts = self.api("GET", f"/channels/{ch['id']}/posts?since={since}").get("posts", {})
            for p in posts.values():
                if p.get("delete_at") or int(p.get("create_at", 0)) <= since:
                    continue
                mentions = [self.me["id"]] if f"@{self.cfg.bot_username}" in p.get("message", "") else []
                evs.append({"event": "posted", "data": {"post": json.dumps(p), "channel_name": ch.get("name", ""),
                                                         "channel_type": ch.get("type", ""), "mentions": json.dumps(mentions)}})
        return sorted(evs, key=lambda e: json.loads(e["data"]["post"])["create_at"])

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
            create_at=int(post.get("create_at") or 0),
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
                try:  # replay posts that arrived while the bot was down / disconnected
                    missed = await asyncio.to_thread(mm.missed_events, orch.last_seen())
                    for ev in missed:
                        inc = mm.parse_event(ev)
                        if inc is not None:
                            await _process(orch, mm, inc, locks.setdefault(inc.channel_id, asyncio.Lock()))
                    if missed:
                        log.info("replayed %d missed posts", len(missed))
                except Exception:
                    log.exception("replay failed")
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
            orch.mark_seen(inc.create_at)
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
    llm: LLM = MockLLM() if a.mock_llm else OpenAICompatLLM(cfg)
    deep = None
    if not a.mock_llm and cfg.claude_repo.exists():
        tiers = [CodexCLI(cfg, m) for m in cfg.codex_models if cfg.codex_bin]
        tiers += [ClaudeCLI(cfg)] if cfg.claude_bin else []
        deep = DeepChain(tiers) if tiers else None
    log.info("deep tiers: %s (repo %s)", [t.label for t in deep.providers] if deep else "off", cfg.claude_repo)
    orch = Orchestrator(cfg, llm, GitHubContext(cfg), DocsContext(cfg), load_members(cfg.members_tsv), deep=deep,
                        memo_llm=None if a.mock_llm else llm)
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
