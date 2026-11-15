"""Unit tests for bridge.py with mocked LLM, GitHub and Mattermost (no network)."""
import io
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bridge  # noqa: E402
from bridge import ClaudeCLI, CodexCLI, Config, DeepChain, DeepTimeout, Mattermost, Incoming, LLMBusy, wants_deep, MockLLM, OpenAICompatLLM, Orchestrator, find_member, load_members, split_message  # noqa: E402,I001


def full(call):
    return call["system"] + "\n".join(m["content"] for m in call["messages"])

MEMBERS_TSV = Path(__file__).resolve().parents[2] / "chat" / "members.tsv"


class FakeGH:
    def __init__(self):
        self.issue_calls = []

    def summary(self, member=None):
        return f"open issues for {member.name if member else 'all'}: #12"

    def issue(self, n):
        self.issue_calls.append(n)
        return {"number": n, "title": "[frontend] S0–S3", "body": "## 제안 담당\n고지은"}

    def pr(self, n):
        return {"title": "feat: map", "user": {"login": "jieun-Ribby"}, "body": "Closes #12", "head": {"sha": "abc"}}

    def pr_diff(self, n):
        return "diff --git a/frontend/x b/frontend/x\n+hello"

    def ci_state(self, sha):
        return "passed"


class FakeDocs:
    def text(self):
        return "### FILE AGENTS.md\nrules"


@pytest.fixture
def orch(tmp_path):
    cfg = Config(state_path=tmp_path / "state.json", members_tsv=MEMBERS_TSV)
    return Orchestrator(cfg, MockLLM(), FakeGH(), FakeDocs(), load_members(MEMBERS_TSV))


def inc(user, chan, msg, mentioned=False, ctype=None):
    return Incoming("cid-" + chan, chan, ctype or ("P" if chan.startswith("1on1-") else "O"), "uid", user, msg,
                    post_id="p1", mentioned=mentioned)


def test_members_loaded():
    m = load_members(MEMBERS_TSV)
    assert set(m) == {"hyle", "yoonsung", "woochan", "jieun", "jimin", "daeun"}
    assert m["hyle"].is_admin and not m["jieun"].is_admin
    assert not m["yoonsung"].uses_git and m["daeun"].uses_git and not m["jieun"].uses_git  # jieun/jimin: MATLAB tonight
    assert find_member(m, "지은").username == "jieun"
    assert find_member(m, "@woochan").name == "김우찬"


def test_member_message_in_1on1_gets_reply(orch):
    outs = orch.handle(inc("jieun", "1on1-jieun", "지도 어디서부터 해요?"))
    assert len(outs) == 1 and outs[0].channel == "cid-1on1-jieun"
    sys_prompt = full(orch.llm.calls[-1])
    assert "고지은" in sys_prompt and "UI/UX A" in sys_prompt
    assert "MATLAB 담당은 git을 쓰지 않는다" in sys_prompt  # jieun has MATLAB work tonight (Hylē 18:57)


def test_matlab_member_gets_no_git_rule(orch):
    orch.handle(inc("yoonsung", "1on1-yoonsung", "POWER 데이터 어떻게 받아요?"))
    sys_prompt = full(orch.llm.calls[-1])
    assert "MATLAB 담당은 git을 쓰지 않는다" in sys_prompt


def test_hyle_plain_message_is_override_and_silent(orch):
    assert orch.handle(inc("hyle", "1on1-jieun", "오늘은 S1까지만")) == []
    assert orch.llm.calls == []
    orch.handle(inc("jieun", "1on1-jieun", "다음 뭐 해요?"))
    assert "오늘은 S1까지만" in full(orch.llm.calls[-1])
    assert "Hylē 우선 지시" in full(orch.llm.calls[-1])


def test_hyle_mention_in_1on1_gets_reply(orch):
    outs = orch.handle(inc("hyle", "1on1-jieun", "지은님한테 S2 프롬프트 줘", mentioned=True))
    assert len(outs) == 1
    assert orch.llm.calls[-1]["messages"][-1]["content"].startswith("[Hylē 지시]")


def test_team_channel_requires_mention(orch):
    assert orch.handle(inc("jimin", "backend", "안녕")) == []
    outs = orch.handle(inc("jimin", "backend", "카드 디자인 질문", mentioned=True))
    assert len(outs) == 1 and outs[0].root_id == "p1"  # replies in thread


def test_bot_ignores_empty(orch):
    assert orch.handle(inc("jimin", "1on1-jimin", "   ")) == []


def test_assign_only_hyle(orch):
    outs = orch.handle(inc("jieun", "backend", "!assign 우찬 #2"))
    assert "Hylē만" in outs[0].message


def test_assign_pushes_to_member_channel(orch):
    outs = orch.handle(inc("hyle", "backend", "!assign 지은 #12 지도부터"))
    assert outs[0].channel == "name:1on1-jieun"
    assert outs[0].message.startswith("@jieun")
    assert outs[-1].channel == "cid-backend"
    assert orch.gh.issue_calls == [12]
    assert any("#12" in o for o in orch.st("1on1-jieun").overrides)


def test_note_and_unknown_member(orch):
    assert "못 찾" in orch.handle(inc("hyle", "backend", "!note 누구 테스트"))[0].message
    assert "저장" in orch.handle(inc("hyle", "backend", "!note 우찬 NEX-GDDP 먼저"))[0].message
    assert orch.st("1on1-woochan").overrides


def test_review_uses_diff_and_not_remembered(orch):
    outs = orch.handle(inc("jieun", "1on1-jieun", "!review 7"))
    assert len(outs) == 1
    content = orch.llm.calls[-1]["messages"][-1]["content"]
    assert "DIFF" in content and "CI: passed" in content
    assert orch.st("1on1-jieun").history == []


def test_help_status_reset(orch):
    assert "!assign" in orch.handle(inc("jieun", "1on1-jieun", "!help"))[0].message
    assert "고지은" in orch.handle(inc("jieun", "1on1-jieun", "!status"))[0].message
    orch.handle(inc("jieun", "1on1-jieun", "질문"))
    assert orch.st("1on1-jieun").history
    orch.handle(inc("jieun", "1on1-jieun", "!reset"))
    assert "1on1-jieun" not in orch.state or not orch.st("1on1-jieun").history


def test_state_persists(tmp_path):
    cfg = Config(state_path=tmp_path / "s.json", members_tsv=MEMBERS_TSV)
    o1 = Orchestrator(cfg, MockLLM(), FakeGH(), FakeDocs(), load_members(MEMBERS_TSV))
    o1.handle(inc("hyle", "1on1-daeun", "복셀은 30x30"))
    o2 = Orchestrator(cfg, MockLLM(), FakeGH(), FakeDocs(), load_members(MEMBERS_TSV))
    assert "복셀은 30x30" in o2.st("1on1-daeun").overrides[0]


def test_llm_failure_is_reported(orch):
    class Boom(MockLLM):
        def complete(self, s, m, think=False):
            raise RuntimeError("down")
    orch.llm = Boom()
    out = orch.handle(inc("jieun", "1on1-jieun", "질문"))[0].message
    assert "LLM 호출 실패" in out


def test_split_message():
    text = ("가" * 100 + "\n") * 400
    parts = split_message(text, limit=1000)
    assert all(len(p) <= 1000 for p in parts) and "".join(parts) == text
    assert split_message("short") == ["short"]


def test_parse_event_filters_own_and_detects_mention():
    mm = bridge.Mattermost.__new__(bridge.Mattermost)
    mm.cfg = Config()
    mm.me = {"id": "bot", "username": "orchestrator"}
    mm._users = {}

    def ev(user_id, msg, mentions=None, chan="uiux-design"):
        data = {"post": json.dumps({"id": "p", "user_id": user_id, "channel_id": "c", "message": msg}),
                "channel_name": chan, "channel_type": "O", "sender_name": "@jimin"}
        if mentions is not None:
            data["mentions"] = json.dumps(mentions)
        return {"event": "posted", "data": data}

    assert mm.parse_event(ev("bot", "hi")) is None
    assert mm.parse_event({"event": "typing"}) is None
    i = mm.parse_event(ev("u1", "@orchestrator 도와줘", ["bot"]))
    assert i.mentioned and i.message == "도와줘" and i.username == "jimin"
    assert not mm.parse_event(ev("u1", "그냥 대화")).mentioned


def test_dry_run_repl(orch, capsys):
    bridge.run_dry(orch, io.StringIO("jieun: 안녕\nhyle@1on1-jieun: 우선 S1\nhyle@backend: !assign 지은 #12\n"))
    out = capsys.readouterr().out
    assert "1on1-jieun" in out and "저장만" in out and "name:1on1-jieun" in out


# ---- laptop agent-loop integration (infra/agent-loop)
def test_assign_dispatches_task_to_laptop_agent(orch):
    outs = orch.handle(inc("hyle", "backend", "!assign 다은 #30 복셀부터"))
    tasks = [o for o in outs if o.message.startswith("!task")]
    assert len(tasks) == 1 and tasks[0].channel == "name:1on1-daeun"
    assert tasks[0].message.startswith("!task #30 ") and "(mock prompt)" in tasks[0].message
    assert "heartbeat 없음" in outs[-1].message


def test_assign_no_task_for_matlab_or_when_disabled(orch):
    outs = orch.handle(inc("hyle", "backend", "!assign 우찬 #2"))
    assert not any(o.message.startswith("!task") for o in outs)
    orch.cfg.auto_dispatch = False
    outs = orch.handle(inc("hyle", "backend", "!assign 지은 #12"))
    assert not any(o.message.startswith("!task") for o in outs)


def test_agent_posts_are_silent_and_feed_status(orch):
    hb = inc("jieun", "1on1-jieun", "🟢 online · agent-loop", ctype="P")
    hb.agent_kind, hb.agent_state = "heartbeat", "idle"
    assert orch.handle(hb) == []
    reply = inc("jieun", "1on1-jieun", "✅ 완료 PR ...")
    reply.agent_kind = "reply"
    assert orch.handle(reply) == []
    assert orch.handle(inc("hyle", "1on1-jieun", "!task #12 지도")) == []
    assert orch.handle(inc("jieun", "1on1-jieun", "!agent")) == []
    st = orch.handle(inc("jieun", "1on1-jieun", "!status"))[0].message
    assert "고지은 (@jieun): 🟢 idle" in st
    st_all = orch.handle(inc("hyle", "backend", "!status"))[0].message
    assert "하지민 (@jimin): ⚪ 기록 없음" in st_all


def test_parse_event_agent_loop_posts():
    mm = bridge.Mattermost.__new__(bridge.Mattermost)
    mm.cfg = Config()
    mm.me = {"id": "bot", "username": "orchestrator"}
    mm._users = {"u1": "jieun"}
    mm._chan_by_name = {"1on1-jieun": "c1"}
    post = {"id": "p", "user_id": "u1", "channel_id": "c1", "message": "🟢 online",
            "props": {"amolla_agent": "heartbeat", "state": "busy"}}
    for evname in ("posted", "post_edited"):
        i = mm.parse_event({"event": evname, "data": {"post": json.dumps(post)}})
        assert i.agent_kind == "heartbeat" and i.agent_state == "busy" and i.channel_name == "1on1-jieun"
    human = dict(post, props={})
    assert mm.parse_event({"event": "post_edited", "data": {"post": json.dumps(human)}}) is None


def hb(user, state="idle", chan=None, **props):
    i = inc(user, chan or f"1on1-{user}", f"{state} heartbeat")
    i.agent_kind, i.agent_state = "heartbeat", state
    i.agent_props = {"amolla_agent": "heartbeat", "state": state, "member": user, **props}
    return i


def test_checkin_aggregation_from_shared_status_channel(orch):
    assert orch.handle(hb("jimin", "busy", chan="agent-status", task="#13 S4", branch="feat/13-s4",
                          commit="abc1234 feat: s4 (2 minutes ago)", dirty="3")) == []
    st = orch.handle(inc("hyle", "backend", "!status"))[0].message
    assert "하지민 (@jimin): 🟡 busy · 작업 #13 S4 · `feat/13-s4` · abc1234 feat: s4 (2 minutes ago) · 변경 3 · 0분 전" in st


def test_silence_flag_once_and_recovery(orch):
    t0 = 1_000_000.0
    orch.on_agent(hb("daeun"), now=t0)
    assert orch.check_silence(now=t0 + 9 * 60) == []
    outs = orch.check_silence(now=t0 + 11 * 60)
    assert len(outs) == 1 and outs[0].channel == "name:1on1-daeun" and "11분째" in outs[0].message and "@hyle" in outs[0].message
    assert orch.check_silence(now=t0 + 12 * 60) == []  # once per silence
    assert "⚠️ 응답 없음" in orch.agent_summary(now=t0 + 12 * 60)
    back = orch.on_agent(hb("daeun"), now=t0 + 13 * 60)
    assert any("다시 연결" in o.message for o in back)
    orch.on_agent(hb("daeun", "offline"), now=t0 + 14 * 60)
    assert orch.check_silence(now=t0 + 60 * 60) == []  # clean shutdown is not "silent"


def test_feedback_on_error_and_stale_dirty(orch):
    t0 = 2_000_000.0
    orch.on_agent(hb("jieun", "busy"), now=t0)
    err = orch.on_agent(hb("jieun", "error"), now=t0 + 60)
    assert len(err) == 1 and err[0].channel == "name:1on1-jieun" and "실패" in err[0].message
    assert orch.on_agent(hb("jieun", "error"), now=t0 + 240) == []  # no repeat while still error
    orch.on_agent(hb("jieun", "idle", dirty="2", branch="feat/12-x"), now=t0 + 300)
    assert orch.on_agent(hb("jieun", "idle", dirty="2", branch="feat/12-x"), now=t0 + 300 + 10 * 60) == []
    d = orch.on_agent(hb("jieun", "idle", dirty="2", branch="feat/12-x"), now=t0 + 300 + 16 * 60)
    assert len(d) == 1 and "커밋 안 된 파일이 2개" in d[0].message
    assert orch.on_agent(hb("jieun", "idle", dirty="2"), now=t0 + 300 + 19 * 60) == []  # cooldown


# ---- DeepSeek client behaviour (fake client, no network)
class _Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class FakeClient:
    def __init__(self, responses):
        self.responses, self.requests = list(responses), []
        self.chat = _Obj(completions=_Obj(create=self.create))

    def create(self, **kw):
        self.requests.append(kw)
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def _resp(content, reasoning=None, tool_calls=None):
    msg = _Obj(content=content, reasoning_content=reasoning, tool_calls=tool_calls)
    usage = _Obj(prompt_cache_hit_tokens=10, prompt_cache_miss_tokens=5, completion_tokens=3)
    return _Obj(choices=[_Obj(message=msg)], usage=usage)


def _err(code):
    e = Exception(f"http {code}")
    e.status_code = code
    return e


def test_thinking_off_by_default_and_on_for_review(orch):
    fc = FakeClient([_resp("hi", reasoning="secret thoughts")])
    llm = OpenAICompatLLM(Config(), client=fc, sleep=lambda s: None)
    assert llm.complete("S", [{"role": "user", "content": "u"}]) == "hi"
    req = fc.requests[0]
    assert req["extra_body"] == {"thinking": {"type": "disabled"}} and "reasoning_effort" not in req
    assert "temperature" not in req and req["model"] == "deepseek-flash"
    fc2 = FakeClient([_resp("ok", reasoning="r")])
    out = OpenAICompatLLM(Config(), client=fc2, sleep=lambda s: None).complete("S", [{"role": "user", "content": "u"}], think=True)
    assert out == "ok" and "r" not in out
    assert fc2.requests[0]["reasoning_effort"] == "high"
    orch.handle(inc("jieun", "1on1-jieun", "!review 7"))
    assert orch.llm.calls[-1]["think"] is True
    orch.handle(inc("jieun", "1on1-jieun", "안녕"))
    assert orch.llm.calls[-1]["think"] is False


def test_reasoning_content_resent_with_tools():
    call = _Obj(id="c1", function=_Obj(name="lookup", arguments="{}"))
    fc = FakeClient([_resp("", reasoning="R1", tool_calls=[call]), _resp("final", reasoning="R2")])
    llm = OpenAICompatLLM(Config(), client=fc, sleep=lambda s: None)
    out = llm.complete("S", [{"role": "user", "content": "u"}], think=True, tools=[{"type": "function"}], run_tool=lambda n, a: "42")
    assert out == "final"
    second = fc.requests[1]["messages"]
    assert second[-2]["role"] == "assistant" and second[-2]["reasoning_content"] == "R1"
    assert second[-1] == {"role": "tool", "tool_call_id": "c1", "content": "42"}


def test_retry_429_5xx_then_busy_message(orch):
    sleeps = []
    fc = FakeClient([_err(429), _err(503), _resp("ok")])
    assert OpenAICompatLLM(Config(), client=fc, sleep=sleeps.append).complete("S", []) == "ok" and sleeps == [1.0, 3.0]
    fc = FakeClient([_err(500), _err(502), _err(503)])
    with pytest.raises(LLMBusy):
        OpenAICompatLLM(Config(), client=fc, sleep=lambda s: None).complete("S", [])
    fc = FakeClient([_err(401)])
    with pytest.raises(Exception) as ei:
        OpenAICompatLLM(Config(), client=fc, sleep=lambda s: None).complete("S", [])
    assert not isinstance(ei.value, LLMBusy)

    class Busy(MockLLM):
        def complete(self, s, m, think=False):
            raise LLMBusy("429")
    orch.llm = Busy()
    assert orch.handle(inc("jieun", "1on1-jieun", "질문"))[0].message == "LLM 응답 지연"


def test_static_prefix_is_stable_and_context_after_user_text(orch):
    orch.handle(inc("jieun", "1on1-jieun", "하나"))
    orch.handle(inc("yoonsung", "1on1-yoonsung", "둘"))
    a, b = orch.llm.calls[-2], orch.llm.calls[-1]
    assert a["system"] == b["system"]  # cacheable prefix identical across members
    assert b["messages"][-1]["content"].startswith("둘") and "## 현재 맥락" in b["messages"][-1]["content"]
    assert "## 현재 맥락" not in orch.st("1on1-jieun").history[0]["content"]


def test_env_fallbacks(monkeypatch):
    for k in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "OPENAI_API_KEY", "OPENAI_BASE_URL", "ORCH_MODEL"):
        monkeypatch.delenv(k, raising=False)
    c = Config.from_env()
    assert c.model == "deepseek-flash" and c.base_url == "https://api.deepseek.com" and c.api_key == ""
    monkeypatch.setenv("OPENAI_API_KEY", "old")
    monkeypatch.setenv("ORCH_MODEL", "m-old")
    c = Config.from_env()
    assert c.api_key == "old" and c.model == "m-old"
    monkeypatch.setenv("LLM_API_KEY", "new")
    monkeypatch.setenv("LLM_MODEL", "m-new")
    c = Config.from_env()
    assert c.api_key == "new" and c.model == "m-new"


# ---- model routing (Claude deep vs DeepSeek flash)
class FakeDeep:
    def __init__(self, reply="deep answer", exc=None, label="Claude Opus 5.5 (VPS, 읽기 전용)"):
        self.reply, self.exc, self.prompts, self.label = reply, exc, [], label

    def ask(self, prompt):
        self.prompts.append(prompt)
        if self.exc:
            raise self.exc
        return self.reply


def test_wants_deep_routing():
    assert not wants_deep("안녕하세요") and not wants_deep("다음 뭐 해요?")
    assert wants_deep("Error using sgolayfilt 이거 왜 나와요") and wants_deep("NDVI 평활 창 크기?") and wants_deep("!deep 그냥")


def test_greeting_uses_flash_and_labels(orch):
    orch.deep = FakeDeep()
    out = orch.handle(inc("jieun", "1on1-jieun", "안녕하세요"))[0].message
    assert orch.deep.prompts == [] and out.endswith("_— 답변: DeepSeek V4.1 Flash_")


def test_matlab_error_goes_to_claude_with_repo_context(orch):
    orch.deep = FakeDeep("원인: 창 크기가 짝수")
    out = orch.handle(inc("woochan", "1on1-woochan", "Error using sgolayfilt: frame length must be odd"))[0]
    assert out.message.startswith("원인") and "Claude Opus 5.5" in out.message
    assert "matlab/TASKS.md" in orch.deep.prompts[0] and "frame length" in orch.deep.prompts[0]
    assert orch.llm.calls == []  # DeepSeek not called


def test_deep_flag_and_timeout_fallback_to_thinking(orch):
    orch.deep = FakeDeep(exc=DeepTimeout())
    out = orch.handle(inc("jieun", "1on1-jieun", "!deep 질문"))[0].message
    assert orch.llm.calls[-1]["think"] is True and "!deep" not in orch.llm.calls[-1]["messages"][-1]["content"]
    assert "심화 모델 실패·시간 초과 대체" in out


def test_reply_in_thread_and_ssh_key_ignored(orch):
    i = inc("woochan", "1on1-woochan", "질문 있어요")
    i.post_id = "p9"
    assert orch.handle(i)[0].root_id == "p9"
    assert orch.handle(inc("woochan", "1on1-woochan", "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIabc amolla-vps")) == []


def test_claude_cli_is_read_only_and_strips_secrets(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_API_KEY", "sk-secret")
    monkeypatch.setenv("MM_BOT_TOKEN", "tok")
    monkeypatch.setenv("HOME", "/home/x")
    seen = {}

    def run(cmd, **kw):
        seen.update(cmd=cmd, **kw)
        return type("R", (), {"returncode": 0, "stdout": "ok", "stderr": ""})()
    cli = ClaudeCLI(Config(claude_repo=tmp_path), run=run)
    assert cli.ask("hello") == "ok"
    cmd = seen["cmd"]
    assert cmd[:4] == ["claude", "-p", "--model", "claude-opus-5-5"]
    allowed = cmd[cmd.index("--allowedTools") + 1:cmd.index("--disallowedTools")]
    assert allowed == ["Read", "Grep", "Glob"] and "Bash" in cmd and "Write" in cmd
    assert "LLM_API_KEY" not in seen["env"] and "MM_BOT_TOKEN" not in seen["env"] and seen["env"]["HOME"] == "/home/x"
    assert seen["timeout"] == 120.0 and seen["cwd"] == str(tmp_path) and "sk-secret" not in seen["input"]

    import subprocess

    def slow(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, 120)
    with pytest.raises(DeepTimeout):
        ClaudeCLI(Config(claude_repo=tmp_path), run=slow).ask("x")


# ---- deep chain (Codex sol -> terra -> Claude), shared history, room memo, replay
def test_codex_cli_read_only_flags_and_env(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENET_API_KEY", "x")
    seen = {}

    def run(cmd, **kw):
        seen.update(cmd=cmd, **kw)
        Path(cmd[cmd.index("-o") + 1]).write_text("sol answer", encoding="utf-8")
        return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
    cli = CodexCLI(Config(claude_repo=tmp_path), "gpt-6.1-sol", run=run)
    assert cli.ask("q") == "sol answer" and cli.label.startswith("Codex gpt-6.1-sol")
    cmd = seen["cmd"]
    assert cmd[:4] == ["codex", "exec", "-m", "gpt-6.1-sol"]
    assert cmd[cmd.index("-s") + 1] == "read-only" and "--ephemeral" in cmd and "--search" not in cmd
    assert cmd[cmd.index("-C") + 1] == str(tmp_path) and cmd[-1] == "-"
    assert "OPENET_API_KEY" not in seen["env"] and seen["timeout"] == 120.0


def test_codex_limit_and_failure_detected(tmp_path):
    def limited(cmd, **kw):
        return type("R", (), {"returncode": 1, "stdout": "", "stderr": "You've hit your usage limit"})()
    with pytest.raises(RuntimeError):
        CodexCLI(Config(claude_repo=tmp_path), "gpt-6.1-sol", run=limited).ask("q")


def test_chain_order_sol_terra_claude_then_deepseek(orch):
    sol = FakeDeep(exc=RuntimeError("limit"), label="Codex gpt-6.1-sol (VPS, 읽기 전용)")
    terra = FakeDeep(exc=DeepTimeout(), label="Codex gpt-6.1-terra (VPS, 읽기 전용)")
    claude = FakeDeep("claude says", label="Claude Opus 5.5 (VPS, 읽기 전용)")
    orch.deep = DeepChain([sol, terra, claude])
    out = orch.handle(inc("woochan", "1on1-woochan", "!deep NDVI 결측 처리"))[0].message
    assert out.startswith("claude says") and out.endswith("_— 답변: Claude Opus 5.5 (VPS, 읽기 전용)_")
    assert len(sol.prompts) == len(terra.prompts) == len(claude.prompts) == 1
    orch.deep = DeepChain([FakeDeep("sol says", label="Codex gpt-6.1-sol (VPS, 읽기 전용)"), claude])
    assert orch.handle(inc("woochan", "1on1-woochan", "!deep 다시"))[0].message.endswith("Codex gpt-6.1-sol (VPS, 읽기 전용)_")
    orch.deep = DeepChain([FakeDeep(exc=RuntimeError("x")), FakeDeep(exc=RuntimeError("y"))])
    assert "심화 모델 실패" in orch.handle(inc("woochan", "1on1-woochan", "!deep 또"))[0].message


def test_shared_history_20_turns_reaches_both_models(orch):
    for i in range(25):
        orch.handle(inc("jieun", "1on1-jieun", f"질문 {i} 이야기"))
    assert len(orch.st("1on1-jieun").history) == 40  # 20 turns kept
    assert len(orch.llm.calls[-1]["messages"]) == 41  # 20 turns + current
    orch.deep = FakeDeep("deep")
    orch.handle(inc("jieun", "1on1-jieun", "!deep 이어서"))
    assert "질문 24 이야기" in orch.deep.prompts[0] and "질문 5 이야기" in orch.deep.prompts[0]


def test_room_memo_written_updated_and_injected(tmp_path):
    cfg = Config(state_path=tmp_path / "s.json", memory_dir=tmp_path / "memory", memo_async=False, members_tsv=MEMBERS_TSV)

    class MemoLLM(MockLLM):
        def complete(self, system, messages, think=False):
            self.calls.append({"system": system, "messages": messages})
            return "# 방 메모\n- 담당 이슈: #24\n- 지금 하는 단계: SG 평활\n- 키 sk-abcdefghijklmnop\n"
    memo = MemoLLM()
    o = Orchestrator(cfg, MockLLM(), FakeGH(), FakeDocs(), load_members(MEMBERS_TSV), memo_llm=memo)
    o.handle(inc("woochan", "1on1-woochan", "담당 이슈 뭐야?"))
    text = (tmp_path / "memory" / "1on1-woochan.md").read_text(encoding="utf-8")
    assert "#24" in text and "sk-abc" not in text and "[비밀값 제거]" in text
    o2 = Orchestrator(cfg, MockLLM(), FakeGH(), FakeDocs(), load_members(MEMBERS_TSV))  # after restart
    o2.handle(inc("woochan", "1on1-woochan", "그거 첫 단계"))
    assert "SG 평활" in o2.llm.calls[-1]["messages"][-1]["content"]
    assert "이번 대화" in memo.calls[0]["messages"][0]["content"]


def test_short_question_gets_short_hint(orch):
    orch.handle(inc("jieun", "1on1-jieun", "안녕"))
    assert "3~5줄로만" in orch.llm.calls[-1]["messages"][-1]["content"]
    orch.handle(inc("jieun", "1on1-jieun", "S2 화면에 토양 요약 카드를 넣으려는데 어떤 API 필드를 써야 하고 단위 표기는 어떻게 하나요"))
    assert "형식 블록 없이" not in orch.llm.calls[-1]["messages"][-1]["content"]


def test_cursor_and_missed_events(tmp_path):
    o = Orchestrator(Config(state_path=tmp_path / "s.json", members_tsv=MEMBERS_TSV), MockLLM(), FakeGH(), FakeDocs(),
                     load_members(MEMBERS_TSV))
    assert o.last_seen() == 0
    o.mark_seen(1000)
    o.mark_seen(500)
    assert o.last_seen() == 1000
    mm = Mattermost.__new__(Mattermost)
    mm.cfg, mm.me, mm.team, mm._users = Config(), {"id": "bot"}, {"id": "t"}, {"u": "woochan"}
    posts = {"a": {"id": "a", "create_at": 1500, "message": "질문", "user_id": "u", "channel_id": "c"},
             "b": {"id": "b", "create_at": 900, "message": "old", "user_id": "u", "channel_id": "c"},
             "d": {"id": "d", "create_at": 1600, "message": "gone", "user_id": "u", "channel_id": "c", "delete_at": 5}}
    calls = []

    def api(method, path, **kw):
        calls.append(path)
        if path.startswith("/users/me/teams"):
            return [{"id": "c", "name": "1on1-woochan", "type": "P", "last_post_at": 1600},
                    {"id": "q", "name": "random", "type": "O", "last_post_at": 10}]
        return {"posts": posts}
    mm.api = api
    evs = mm.missed_events(1000)
    assert [json.loads(e["data"]["post"])["id"] for e in evs] == ["a"]
    assert not any("/channels/q/" in c for c in calls)
    assert mm.parse_event(evs[0]).create_at == 1500
    assert mm.missed_events(0) == []


# ---- progress placeholder, design channel, onboarding facts
class FakeNotifier:
    def __init__(self):
        self.events = []

    def typing(self, ch, root):
        self.events.append(("typing", ch, root))

    def placeholder(self, ch, root, text):
        self.events.append(("placeholder", ch, root, text))
        return "ph1"

    def edit(self, pid, text):
        self.events.append(("edit", pid, text))


def test_placeholder_then_answer_edits_it(orch):
    orch.notifier = FakeNotifier()
    i = inc("jieun", "1on1-jieun", "안녕")
    i.post_id = "q1"
    out = orch.handle(i)[0]
    kinds = [e[0] for e in orch.notifier.events]
    assert kinds[:2] == ["typing", "placeholder"]
    assert orch.notifier.events[1][2] == "q1" and "⏳ 답변 준비 중… (DeepSeek V4.1 Flash)" in orch.notifier.events[1][3]
    assert out.edit_id == "ph1" and out.root_id == "q1"


def test_deep_placeholder_shows_tier_switches(orch):
    orch.notifier = FakeNotifier()
    orch.cfg.progress_every = 0.01
    import time as _t

    class Slow(FakeDeep):
        def ask(self, prompt):
            _t.sleep(0.05)
            return super().ask(prompt)
    orch.deep = DeepChain([FakeDeep(exc=RuntimeError("limit"), label="Codex gpt-6.1-sol (VPS, 읽기 전용)"),
                           Slow("terra ok", label="Codex gpt-6.1-terra (VPS, 읽기 전용)")])
    out = orch.handle(inc("woochan", "1on1-woochan", "!deep NDVI 결측"))[0]
    texts = [e[-1] for e in orch.notifier.events if e[0] in ("placeholder", "edit")]
    assert any("gpt-6.1-sol" in t for t in texts) and any("gpt-6.1-terra" in t for t in texts)
    assert any("아직 생각 중" in t for t in texts)
    assert out.message.startswith("terra ok") and out.edit_id == "ph1"


def test_design_channel_answers_questions_with_deep_by_default(orch):
    orch.deep = FakeDeep("sol design", label="Codex gpt-6.1-sol (VPS, 읽기 전용)")
    out0 = orch.handle(inc("jieun", "uiux-design", "수익 칸은 빼는 게 좋겠어요"))[0]  # no mention, no '?': still answered
    assert out0.message.startswith("sol design")
    out = orch.handle(inc("jieun", "uiux-design", "S4에서 수익 % 칸 빼도 될까?"))[0]
    assert out.message.startswith("sol design") and len(orch.deep.prompts) == 2
    out2 = orch.handle(inc("jimin", "uiux-design", "안녕", mentioned=True))[0]
    assert "gpt-6.1-sol" in out2.message  # even short greetings use the deep model here


def test_onboarding_order_in_static_context_without_ip(orch):
    sysmsg = orch.build_system()
    assert "공개키" in sysmsg and "자동" in sysmsg and "서버 주소를 모른다" in sysmsg
    assert not re.search(r"\b\d{1,3}(\.\d{1,3}){3}\b", sysmsg.split("## 저장소 문서")[0])


def test_design_channel_ignores_bot_and_agent_posts():
    mm = Mattermost.__new__(Mattermost)
    mm.cfg, mm.me, mm._users = Config(), {"id": "bot"}, {"u": "jieun"}
    own = {"event": "posted", "data": {"post": json.dumps({"id": "1", "user_id": "bot", "message": "답", "channel_id": "c"}), "channel_name": "uiux-design"}}
    other_bot = {"event": "posted", "data": {"post": json.dumps({"id": "2", "user_id": "x", "message": "hi", "channel_id": "c", "props": {"from_bot": "true"}}),
                                             "channel_name": "uiux-design"}}
    assert mm.parse_event(own) is None and mm.parse_event(other_bot) is None


def test_design_memo_prompt_tracks_decisions(tmp_path):
    cfg = Config(state_path=tmp_path / "s.json", memory_dir=tmp_path / "m", memo_async=False, members_tsv=MEMBERS_TSV)
    memo = MockLLM()
    o = Orchestrator(cfg, MockLLM(), FakeGH(), FakeDocs(), load_members(MEMBERS_TSV), memo_llm=memo)
    o.deep = FakeDeep("ok")
    o.handle(inc("jimin", "uiux-design", "S5 배지 넣기로 해요"))
    assert "PRD 논의방" in memo.calls[-1]["messages"][0]["content"]


# ---- quality fixes: MATLAB paths, toolbox/token rules, guide template, screenshots
def test_static_context_has_matlab_paths_rules_and_template(orch):
    s = orch.build_system().split("## 저장소 문서")[0]
    assert "/data/processed/v1/inputs/" in s and "서버 바깥 경로" in s
    assert "Add-On 탐색기" in s and "브라우저 MATLAB 접속 토큰" in s
    for mark in ("✅ 할 일", "📘 방법", "📋 명세", "🎯 이슈", "📮 완료 보고"):
        assert mark in s
    assert "matlab/TASKS.md" in bridge.DOC_FILES and "infra/matlab/REMOTE.md" in bridge.DOC_FILES


def test_screenshot_goes_to_flash_vision_not_cli(orch):
    class N(FakeNotifier):
        def fetch_images(self, ids):
            return ["data:image/png;base64,AAAA"]
    orch.notifier = N()
    orch.deep = FakeDeep("should not be used")
    i = inc("yoonsung", "1on1-yoonsung", "Error using parquetwrite 이거 왜 나요")
    i.file_ids, i.file_count = ["f1"], 1
    out = orch.handle(i)[0]
    assert orch.deep.prompts == []
    content = orch.llm.calls[-1]["messages"][-1]["content"]
    assert isinstance(content, list) and content[1]["type"] == "image_url" and "첨부 이미지 1장" in content[0]["text"]
    assert "DeepSeek V4.1 Flash" in out.message
    assert isinstance(orch.st("1on1-yoonsung").history[-2]["content"], str)  # history keeps text only


# ---- batching: debounce rapid posts, queue posts sent while answering
def test_batcher_debounces_and_queues_during_answer(orch):
    import asyncio as aio

    from bridge import Batcher

    seen, notes = [], []
    orch.note_extra = lambda ch, n: notes.append(n)

    async def fake_process(o, mm, inc, lock):
        seen.append(inc.message)
        await aio.sleep(0.2)  # "generating"

    async def scenario():
        b = Batcher(orch, None, {}, delay=0.05, process=fake_process)
        mk = lambda m, i: Incoming("c", "1on1-jieun", "P", "u1", "jieun", m, post_id=f"p{i}", create_at=i)  # noqa: E731
        b.add(mk("첫째", 1))
        b.add(mk("둘째", 2))           # within debounce -> same batch
        await aio.sleep(0.1)           # now answering batch 1
        b.add(mk("셋째", 3))
        b.add(mk("넷째", 4))           # queued while answering
        b.add(Incoming("c", "1on1-jieun", "P", "u1", "jieun", "!help", post_id="p5"))  # command bypasses
        await aio.sleep(0.6)
    aio.run(scenario())
    assert seen[0] == "첫째\n둘째"
    assert "!help" in seen
    follow = [s for s in seen if s.startswith("(앞 답변을 만드는 동안 보낸 추가 메시지)")]
    assert follow and follow[0].endswith("셋째\n넷째")
    assert notes == [1, 2]


def test_note_extra_updates_placeholder(orch):
    orch.notifier = FakeNotifier()
    import threading
    orch.active["c"] = {"pid": "ph1", "label": "Codex gpt-6.1-sol", "stop": threading.Event(), "extra": 0}
    orch.note_extra("c", 2)
    assert orch.notifier.events[-1][0] == "edit" and "추가 메시지 2개 받음, 이어서 답할게요" in orch.notifier.events[-1][2]


def test_matlab_error_in_matlab_room_enqueues_fix_job(tmp_path, orch):
    orch.cfg.fix_queue = tmp_path / "fixq"
    out = orch.handle(inc("woochan", "1on1-woochan", "[1/20] FAILED (USGS): timed out 고쳐"))[0].message
    jobs = list((tmp_path / "fixq").glob("*_woochan.json"))
    assert len(jobs) == 1 and "서버 에이전트가 **스크립트를 직접 고쳐**" in out
    job = json.loads(jobs[0].read_text(encoding="utf-8"))
    assert job["user"] == "woochan" and "FAILED" in job["message"]
    orch.handle(inc("jieun", "1on1-jieun", "안녕"))
    assert len(list((tmp_path / "fixq").glob("*.json"))) == 1  # greetings are not fix jobs
