"""End-to-end test: mock Mattermost HTTP API + fake agent + fake gh + temp git repo (no network)."""
import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import agent_loop as al  # noqa: E402

TOKEN = "mmtok_SECRET_123456"


class FakeMM:
    """Just enough of /api/v4 for agent_loop."""

    def __init__(self):
        self.posts = {}
        self.n = 0
        self.lock = threading.Lock()
        self.users = {"u-me": "jieun", "u-bot": "orchestrator", "u-hyle": "hyle", "u-x": "stranger"}

    def add(self, user_id, message, root_id="", props=None, channel_id="c1"):
        with self.lock:
            self.n += 1
            pid = f"p{self.n}"
            self.posts[pid] = {"id": pid, "user_id": user_id, "channel_id": channel_id, "message": message,
                               "root_id": root_id, "props": props or {}, "create_at": int(time.time() * 1000) + self.n,
                               "update_at": 0, "delete_at": 0}
            return self.posts[pid]

    def handler(self):
        mm = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, code, obj):
                b = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)

            def _auth(self):
                if self.headers.get("Authorization") != f"Bearer {TOKEN}":
                    self._send(401, {"message": "bad token"})
                    return False
                return True

            def _body(self):
                n = int(self.headers.get("Content-Length") or 0)
                return json.loads(self.rfile.read(n) or b"null")

            def do_GET(self):
                if not self._auth():
                    return
                u = urlparse(self.path)
                p = u.path
                if p == "/api/v4/users/me":
                    return self._send(200, {"id": "u-me", "username": "jieun"})
                if p == "/api/v4/teams/name/amolla":
                    return self._send(200, {"id": "t1"})
                if p == "/api/v4/teams/t1/channels/name/1on1-jieun":
                    return self._send(200, {"id": "c1"})
                if p == "/api/v4/teams/t1/channels/name/agent-status":
                    return self._send(200, {"id": "c2"})
                if p == "/api/v4/channels/c1/posts":
                    since = int(parse_qs(u.query).get("since", ["0"])[0])
                    with mm.lock:
                        ps = {k: v for k, v in mm.posts.items()
                              if v["channel_id"] == "c1" and max(v["create_at"], v["update_at"]) > since}
                    return self._send(200, {"order": list(ps), "posts": ps})
                self._send(404, {})

            def do_POST(self):
                if not self._auth():
                    return
                p, body = urlparse(self.path).path, self._body()
                if p == "/api/v4/users/usernames":
                    return self._send(200, [{"id": k, "username": v} for k, v in mm.users.items() if v in body])
                if p == "/api/v4/posts":
                    assert body["channel_id"] in ("c1", "c2")
                    return self._send(201, mm.add("u-me", body["message"], body.get("root_id", ""), body.get("props"), body["channel_id"]))
                self._send(404, {})

            def do_PUT(self):
                if not self._auth():
                    return
                p, body = urlparse(self.path).path, self._body()
                pid = p.split("/")[4]
                with mm.lock:
                    mm.edits = getattr(mm, "edits", 0) + 1
                    mm.posts[pid].update(message=body["message"], props=body.get("props", {}), update_at=int(time.time() * 1000))
                    return self._send(200, mm.posts[pid])

        return H


@pytest.fixture
def server():
    mm = FakeMM()
    srv = ThreadingHTTPServer(("127.0.0.1", 0), mm.handler())
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield mm, f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def git(cwd, *a):
    return subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path, monkeypatch):
    bare = tmp_path / "remote.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(bare))
    work = tmp_path / "2026NASA"
    git(tmp_path, "clone", "-q", str(bare), str(work))
    git(work, "config", "user.email", "t@example.com")
    git(work, "config", "user.name", "t")
    git(work, "checkout", "-q", "-b", "main")
    (work / "README.md").write_text("hi\n")
    git(work, "add", ".")
    git(work, "commit", "-q", "-m", "init")
    git(work, "push", "-q", "-u", "origin", "main")
    # fake gh: logs argv, prints a PR URL for "pr create", nothing for "pr list"
    bindir = tmp_path / "bin"
    bindir.mkdir()
    ghlog = tmp_path / "gh.log"
    gh = bindir / "gh"
    gh.write_text(f"#!/bin/sh\necho \"$@\" >> {ghlog}\n"
                  "case \"$1 $2\" in \"pr create\") echo https://github.com/cloudsnuchoi/2026NASA/pull/99;; esac\n")
    gh.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    return work, bare, ghlog


def make_cfg(url, work, agent_cmd):
    return al.Config(mm_url=url, mm_token=TOKEN, agent="echo", agent_cmd=agent_cmd, repo_dir=str(work),
                     poll_sec=0.2, heartbeat_min=0.02, progress_sec=999, timeout_min=1)


def wait_for(pred, t=20):
    end = time.time() + t
    while time.time() < end:
        if pred():
            return True
        time.sleep(0.1)
    return False


def start_loop(cfg):
    mm = al.MM(cfg)
    mm.connect()
    loop = al.AgentLoop(cfg, mm)
    loop.started -= 1
    th = threading.Thread(target=loop.run, daemon=True)
    th.start()
    return loop, th


def test_message_to_run_to_reply_with_pr(server, repo):
    fake, url = server
    work, bare, ghlog = repo
    writer = [sys.executable, "-c",
              "import sys,pathlib;p=sys.stdin.read();pathlib.Path('hello.txt').write_text('done\\n');"
              "print('SUMMARY: feat(#12): add hello');print('prompt has block:', '[agent-loop' in p, '#12' in p)"]
    cfg = make_cfg(url, work, writer)
    loop, th = start_loop(cfg)
    assert wait_for(lambda: any((p["props"] or {}).get("amolla_agent") == "heartbeat" for p in fake.posts.values()))
    fake.add("u-x", "!task #12 ignore me (not allowed)")
    task = fake.add("u-bot", "!task #12 S1 지도 화면")
    assert wait_for(lambda: any(p["root_id"] == task["id"] and p["message"].startswith("✅") for p in fake.posts.values())), \
        json.dumps(fake.posts, ensure_ascii=False, indent=1)
    replies = [p["message"] for p in fake.posts.values() if p["root_id"] == task["id"]]
    final = replies[-1]
    assert "pull/99" in final and "prompt has block: True True" in final
    assert any(r.startswith("📥") for r in replies) and any(r.startswith("▶️") for r in replies)
    # one job only, the stranger's message was ignored
    assert sum(r.startswith("📥") for r in [p["message"] for p in fake.posts.values()]) == 1
    # branch pushed to the remote with the file
    branches = git(bare, "branch", "--list", "feat/12-*")
    assert "feat/12-s1" in branches
    log = ghlog.read_text()
    assert "issue comment 12" in log and "STATUS: 🟢 진행 중" in log and "STATUS: 🟡 리뷰 대기" in log
    assert "pr create" in log and "Closes #12" in log
    # status transitions + no token leak
    msgs = "\n".join(p["message"] for p in fake.posts.values())
    assert "STATUS busy" in msgs and "STATUS idle" in msgs and TOKEN not in msgs
    loop.stop.set()


def test_queue_and_failure(server, repo):
    fake, url = server
    work, _, _ = repo
    slow_fail = [sys.executable, "-c", "import sys,time;sys.stdin.read();time.sleep(1);print('boom');sys.exit(3)"]
    cfg = make_cfg(url, work, slow_fail)
    loop, _ = start_loop(cfg)
    a = fake.add("u-hyle", "!task 첫번째")
    b = fake.add("u-hyle", "!task 두번째")
    assert wait_for(lambda: sum(p["message"].startswith("❌ 실패") for p in fake.posts.values()) == 2, 30)
    rb = [p["message"] for p in fake.posts.values() if p["root_id"] == b["id"]]
    assert "대기열" in rb[0]
    assert any("exit 3" in p["message"] for p in fake.posts.values() if p["root_id"] == a["id"])
    assert "STATUS error" in "\n".join(p["message"] for p in fake.posts.values())
    loop.stop.set()


def test_dirty_repo_refuses(server, repo):
    fake, url = server
    work, _, _ = repo
    (work / "README.md").write_text("local edit\n")
    loop, _ = start_loop(make_cfg(url, work, [sys.executable, "-c", "print(1)"]))
    t = fake.add("u-bot", "!task #3 x")
    assert wait_for(lambda: any(p["root_id"] == t["id"] and "커밋 안 된 변경" in p["message"] for p in fake.posts.values()))
    loop.stop.set()


def test_parse_and_safety():
    assert al.parse_task("!task #12 지도", "!task") == (12, "지도")
    assert al.parse_task("!TASK do it", "!task") == (None, "do it")
    assert al.parse_task("hello", "!task") is None
    assert "***" in al.redact("token=abcdefghijk ghp_" + "a" * 30)
    c = al.Config(agent_cmd=["codex", "exec", "--dangerously-bypass-approvals-and-sandbox", "-"])
    with pytest.raises(SystemExit):
        c.command()
    assert al.Config(agent="codex").command()[0][:4] == ["codex", "exec", "--sandbox", "workspace-write"]
    assert al.Config(agent="agy").command() == (["agy", "-p", "{prompt}"], "arg")


def test_checkin_snapshot_status_channel_and_feedback_pickup(server, repo):
    fake, url = server
    work, _, _ = repo
    (work / "wip.txt").write_text("x")  # 1 uncommitted file -> dirty=1
    cfg = make_cfg(url, work, [sys.executable, "-c", "print(1)"])
    cfg.status_channel = "agent-status"
    loop, _ = start_loop(cfg)
    hbp = lambda: [p for p in fake.posts.values() if (p["props"] or {}).get("amolla_agent") == "heartbeat"]  # noqa: E731
    assert wait_for(lambda: hbp())
    h = hbp()[0]
    assert h["channel_id"] == "c2"  # dedicated #agent-status channel
    pr = h["props"]
    assert pr["member"] == "jieun" and pr["branch"] == "main" and pr["dirty"] == "1" and pr["state"] == "idle"
    assert pr["commit"].startswith(git(work, "rev-parse", "--short", "HEAD")) and "init" in pr["commit"]
    assert "`main`" in h["message"] and "커밋 안 된 파일 1개" in h["message"]
    # periodic check-in: heartbeat_min=0.02 (~1.2 s) -> the same post is edited again and again
    assert wait_for(lambda: getattr(fake, "edits", 0) >= 2, 10)
    assert len(hbp()) == 1
    # feedback (not !task) from the orchestrator is picked up and counted in the next check-in
    fake.add("u-bot", "S1 지도는 fixtures 먼저 붙이고 API는 나중에 해요")
    fake.add("u-x", "spam from a stranger")
    assert wait_for(lambda: loop.notes_total == 1)
    assert "fixtures 먼저" in loop.notes[0] and "@orchestrator" in loop.notes[0]
    assert wait_for(lambda: hbp()[0]["props"].get("notes") == "1", 10)
    loop.stop.set()


def test_feedback_goes_into_next_prompt(server, repo):
    fake, url = server
    work, _, _ = repo
    dump = [sys.executable, "-c", "import sys;p=sys.stdin.read();print('HAS_FEEDBACK', '지도는 MapLibre' in p and '최근 중앙 에이전트' in p)"]
    loop, _ = start_loop(make_cfg(url, work, dump))
    fake.add("u-hyle", "지도는 MapLibre로 통일해요")
    assert wait_for(lambda: loop.notes_total == 1)
    t = fake.add("u-hyle", "!task 지도 정리")
    assert wait_for(lambda: any(p["root_id"] == t["id"] and "HAS_FEEDBACK True" in p["message"] for p in fake.posts.values()))
    loop.stop.set()
