"""Unit tests for bridge.py with mocked LLM, GitHub and Mattermost (no network)."""
import io
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bridge  # noqa: E402
from bridge import Config, Incoming, MockLLM, Orchestrator, find_member, load_members, split_message  # noqa: E402,I001

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
    assert not m["yoonsung"].uses_git and m["jieun"].uses_git
    assert find_member(m, "지은").username == "jieun"
    assert find_member(m, "@woochan").name == "김우찬"


def test_member_message_in_1on1_gets_reply(orch):
    outs = orch.handle(inc("jieun", "1on1-jieun", "지도 어디서부터 해요?"))
    assert len(outs) == 1 and outs[0].channel == "cid-1on1-jieun"
    sys_prompt = orch.llm.calls[-1]["system"]
    assert "고지은" in sys_prompt and "UI/UX A" in sys_prompt
    assert "Codex/agy가 마무리 블록" in sys_prompt  # git members get git rule


def test_matlab_member_gets_no_git_rule(orch):
    orch.handle(inc("yoonsung", "1on1-yoonsung", "POWER 데이터 어떻게 받아요?"))
    sys_prompt = orch.llm.calls[-1]["system"]
    assert "MATLAB 담당은 git을 쓰지 않는다" in sys_prompt


def test_hyle_plain_message_is_override_and_silent(orch):
    assert orch.handle(inc("hyle", "1on1-jieun", "오늘은 S1까지만")) == []
    assert orch.llm.calls == []
    orch.handle(inc("jieun", "1on1-jieun", "다음 뭐 해요?"))
    assert "오늘은 S1까지만" in orch.llm.calls[-1]["system"]
    assert "Hylē 우선 지시" in orch.llm.calls[-1]["system"]


def test_hyle_mention_in_1on1_gets_reply(orch):
    outs = orch.handle(inc("hyle", "1on1-jieun", "지은님한테 S2 프롬프트 줘", mentioned=True))
    assert len(outs) == 1
    assert orch.llm.calls[-1]["messages"][-1]["content"].startswith("[Hylē 지시]")


def test_team_channel_requires_mention(orch):
    assert orch.handle(inc("jimin", "uiux-design", "안녕")) == []
    outs = orch.handle(inc("jimin", "uiux-design", "카드 디자인 질문", mentioned=True))
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
        def complete(self, s, m):
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
    outs = orch.handle(inc("hyle", "backend", "!assign 지은 #12 지도부터"))
    tasks = [o for o in outs if o.message.startswith("!task")]
    assert len(tasks) == 1 and tasks[0].channel == "name:1on1-jieun"
    assert tasks[0].message.startswith("!task #12 ") and "(mock prompt)" in tasks[0].message
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
    assert "~1on1-jieun: 🟢 idle" in st
    st_all = orch.handle(inc("hyle", "backend", "!status"))[0].message
    assert "~1on1-jimin: 기록 없음" in st_all


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
