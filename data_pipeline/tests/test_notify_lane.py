"""infra/matlab/notify.py dedupe + log format, mwatch new-script / group notices, live_status lane states."""
from __future__ import annotations

import importlib.util
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _notify(tmp_path, monkeypatch):
    n = _load("notify_t", "infra/matlab/notify.py")
    monkeypatch.setattr(n, "LOG", tmp_path / "notify.log")
    monkeypatch.setattr(n, "SENT", tmp_path / "notify_sent.json")
    return n


def test_notify_dedupe_and_log_format(tmp_path, monkeypatch):
    n = _notify(tmp_path, monkeypatch)
    posts = []

    def fake_post(msg, root_id):
        posts.append((msg, root_id))
        return f"p{len(posts)}"

    assert n.notify("jimin", "1on1-jimin", "첫 줄\n둘째\t줄", kind="new-script", file="a.m", post_fn=fake_post) == "p1"
    assert n.notify("jimin", "1on1-jimin", "again", kind="new-script", file="a.m", post_fn=fake_post) is None
    assert n.notify("jimin", "1on1-jimin", "other", kind="fixed", file="a.m", post_fn=fake_post) == "p2"
    assert posts[0][0] == "@jimin 첫 줄\n둘째\t줄"  # @mention added, text otherwise untouched
    lines = (tmp_path / "notify.log").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    at, room, text = lines[0].split("\t")
    assert at.endswith("+09:00") and room == "1on1-jimin" and text == "@jimin 첫 줄 ⏎ 둘째 줄"
    sent = json.loads((tmp_path / "notify_sent.json").read_text(encoding="utf-8"))
    assert set(sent) == {"jimin|new-script|a.m", "jimin|fixed|a.m"} and sent["jimin|new-script|a.m"]["post_id"] == "p1"


def test_new_script_template_and_description(tmp_path, monkeypatch):
    n = _notify(tmp_path, monkeypatch)
    f = tmp_path / "ndvi_baresoil_fixed.m"
    f.write_text("function ndvi_baresoil_fixed()\n%NDVI_BARESOIL_FIXED Offline low-NDVI screening.\n", encoding="utf-8")
    assert n.new_script_text("jimin", f) == ("@jimin 🆕 수정본: Offline low-NDVI screening.\n"
                                             "📂 ~/Documents/MATLAB/work/ndvi_baresoil_fixed.m\n"
                                             "▶ 파일을 열고 Run ▶만 눌러 주세요. 오류는 봇이 자동으로 읽습니다.")
    assert not n.is_announceable("artfarm_run_logged.m") and not n.is_announceable("untitled.m")


def _mwatch(tmp_path, monkeypatch):
    m = _load("mwatch_t", "infra/matlab/mwatch.py")
    for k, v in {"OUT": tmp_path / "outputs", "STATE": tmp_path / "mwatch.json", "FIXQ": tmp_path / "fixq",
                 "WORK": tmp_path / "work", "VERIFIED": tmp_path / "mauto_verified.json"}.items():
        monkeypatch.setattr(m, k, v)
    monkeypatch.setattr(m.notify, "LOG", tmp_path / "notify.log")
    monkeypatch.setattr(m.notify, "SENT", tmp_path / "notify_sent.json")
    m._channels.clear()
    posts = []

    def fake_api(method, path, body=None):
        if path.startswith("/teams/name/"):
            return {"id": "team1"}
        if "/channels/name/" in path:
            return {"id": "chan-" + path.rsplit("/", 1)[-1]}
        posts.append(body)
        return {"id": f"post{len(posts)}"}

    monkeypatch.setattr(m, "api", fake_api)
    return m, posts


def test_mwatch_announces_only_new_scripts(tmp_path, monkeypatch):
    m, posts = _mwatch(tmp_path, monkeypatch)
    d = tmp_path / "work" / "yoonsung"
    d.mkdir(parents=True)
    (d / "old.m").write_text("% old\n", encoding="utf-8")
    state: dict = {}
    m.scan_once(state)
    assert posts == []  # first scan is the baseline
    old = time.time() - 60
    for name in ("new_one.m", "artfarm_run_logged.m"):
        (d / name).write_text("% Base MATLAB boxes.\n", encoding="utf-8")
        os.utime(d / name, (old, old))
    m.scan_once(state)
    m.scan_once(state)
    assert [p["message"].splitlines()[0] for p in posts] == ["@yoonsung 🆕 Base MATLAB boxes."]
    assert posts[0]["channel_id"] == "chan-1on1-yoonsung"


def test_group_notice_after_woochan_run_once(tmp_path, monkeypatch):
    m, posts = _mwatch(tmp_path, monkeypatch)
    d = tmp_path / "outputs" / "woochan"
    d.mkdir(parents=True)
    log = {"user": "woochan", "run_id": "20261115_210000", "complete": True,
           "steps": [{"script": "FieldShift_V8_batch", "success": True, "files": []}]}
    (d / "run_log.json").write_text(json.dumps(log), encoding="utf-8")
    state: dict = {}
    assert m.scan_once(state) == [("woochan", "summary")]
    log["run_id"] = "20261115_211000"
    (d / "run_log.json").write_text(json.dumps(log), encoding="utf-8")
    m.scan_once(state)
    group = [p for p in posts if "캡처·붙여넣기 안 하셔도" in p["message"]]
    assert [p["channel_id"] for p in group] == [f"chan-1on1-{u}" for u in ("woochan", "yoonsung", "jimin", "jieun")]
    assert "죄송합니다" in group[0]["message"] and "계수 출처 표" in group[0]["message"]
    assert all("죄송" not in p["message"] for p in group[1:]) and "run_all_jimin.m" in group[2]["message"]
    ev = json.loads((tmp_path / "mauto_verified.json").read_text(encoding="utf-8"))
    assert ev["run_id"] == "20261115_210000" and ev["mwatch_action"] == "summary" and len(ev["group_notice"]) == 4


def test_lane_state_derivation():
    ls = _load("live_status_t", "infra/status/live_status.py")
    d = ls.derive_lane_state
    assert d(True, 3, 2)["state"] == "running"
    assert d(False, 3, 2) == {"state": "waiting-merge", "waits_on": "main에 없는 커밋 3개 (감독 머지)"}
    assert d(False, 0, 2)["state"] == "waiting-notify"
    assert d(False, 0, 0, done=True)["state"] == "done"
    assert d(False, 0, 0)["state"] == "blocked"
    assert d(True, 0, 0, override={"state": "blocked", "waits_on": "Hylē 승인"}) == {"state": "blocked", "waits_on": "Hylē 승인"}
    assert d(True, 0, 0, override={"state": "nonsense"})["state"] == "running"
    md = ls.to_md({"generated_at": "2026-11-15T21:00:00+09:00", "remaining_min": 150, "lanes": [], "blockers": [], "next": [],
                   "ai_models": [], "people": [], "merged_prs": [],
                   "tmux": [{"name": "notify", "model": "m", "task": "t", "last_activity": "21:00", "state": "running", "waits_on": ""}],
                   "lane_states": {"notify": {"state": "running", "waits_on": ""}, "l2": {"state": "waiting-merge", "waits_on": "x"}}})
    assert "| notify | m | t | running | — | 21:00 |" in md and "| l2 | waiting-merge | x |" in md
