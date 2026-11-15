"""matlab/autorun: static checks for the .m files + mwatch behaviour with a fake Mattermost API."""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

from data_pipeline.tests.test_matlab_static import INTERACTIVE, _analyse, _code_lines

ROOT = Path(__file__).resolve().parents[2]
AUTORUN = ROOT / "matlab" / "autorun"
M_FILES = sorted(AUTORUN.glob("*.m"))
USERS = ("woochan", "yoonsung", "jimin", "jieun")


def test_all_runners_present() -> None:
    names = {p.name for p in M_FILES}
    assert "artfarm_run_logged.m" in names
    for u in USERS:
        assert f"run_all_{u}.m" in names


@pytest.mark.parametrize("path", M_FILES, ids=lambda p: p.name)
def test_autorun_static(path: Path) -> None:
    a = _analyse(path)
    assert not a["unclosed"] and a["paren"] == 0
    assert not INTERACTIVE.search("\n".join(_code_lines(path)))
    assert path.stem not in a["functions"][1:], "file name equals a local function"
    if path.name.startswith("run_all_"):
        assert a["is_script"] and not a["functions"], "run_all must be a plain script"
        text = path.read_text(encoding="utf-8")
        assert "artfarm_run_logged(" in text and "cd(" in text and "addpath(" in text
    else:
        assert a["functions"][0] == path.stem
        text = path.read_text(encoding="utf-8")
        for needle in ("rehash", "clear(name)", "getReport(ME, 'extended', 'hyperlinks', 'off')",
                       "run_log.json", "run_history.jsonl", "jsonencode", "readtable"):
            assert needle in text, needle


# ---------------------------------------------------------------- mwatch
def _load_mwatch(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("mwatch", ROOT / "infra" / "matlab" / "mwatch.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    monkeypatch.setattr(m, "OUT", tmp_path / "outputs")
    monkeypatch.setattr(m, "STATE", tmp_path / "state" / "mwatch.json")
    monkeypatch.setattr(m, "FIXQ", tmp_path / "fixq")
    monkeypatch.setattr(m, "HOST_ROOT", str(tmp_path / "host"))
    m._channels.clear()
    calls = []

    def fake_api(method, path, body=None):
        calls.append((method, path, body))
        if path.startswith("/teams/name/"):
            return {"id": "team1"}
        if "/channels/name/" in path:
            return {"id": "chan-" + path.rsplit("/", 1)[-1]}
        if method == "POST" and path == "/posts":
            return {"id": f"post{len(calls)}", "channel_id": body["channel_id"]}
        raise AssertionError(path)

    monkeypatch.setattr(m, "api", fake_api)
    return m, calls


def _write_log(tmp_path, user, steps, run_id="20261115_204500", complete=True):
    d = tmp_path / "outputs" / user
    d.mkdir(parents=True, exist_ok=True)
    (d / "run_log.json").write_text(json.dumps({"user": user, "run_id": run_id, "complete": complete,
                                                "steps": steps}), encoding="utf-8")


def test_failure_enqueues_valid_job_once(tmp_path, monkeypatch):
    m, calls = _load_mwatch(tmp_path, monkeypatch)
    _write_log(tmp_path, "jimin", [
        {"script": "ndvi_baresoil", "resolved": "ndvi_baresoil_fixed", "success": True, "files": []},
        {"script": "jimin_ndvi_anomaly", "resolved": "jimin_ndvi_anomaly", "success": False,
         "error_id": "MATLAB:undefinedVarOrFunction", "error_message": "Unrecognized function 'foo'",
         "error_report": "Error in jimin_ndvi_anomaly (line 12)", "files": []}])
    state: dict = {}
    assert m.scan_once(state) == [("jimin", "fix")]
    assert m.scan_once(state) == []  # handled exactly once
    assert m.scan_once(json.loads(m.STATE.read_text())) == []  # also after restart
    jobs = list((tmp_path / "fixq").glob("*.json"))
    assert len(jobs) == 1 and jobs[0].name.endswith("_jimin.json")
    job = json.loads(jobs[0].read_text(encoding="utf-8"))
    posts = [c for c in calls if c[0] == "POST"]
    assert len(posts) == 1 and "jimin_ndvi_anomaly 오류 → 서버가 고치는 중" in posts[0][2]["message"]
    for k in ("user", "room", "channel_id", "root_id", "post_id", "message"):
        assert job[k]
    assert job["room"] == "1on1-jimin" and job["channel_id"] == "chan-1on1-jimin"
    assert job["post_id"] == job["root_id"] == f"post{len(calls)}"  # real post id just created
    assert job["script"] == "jimin_ndvi_anomaly.m"
    assert "Unrecognized function 'foo'" in job["message"] and "line 12" in job["message"]


def test_success_posts_summary_once(tmp_path, monkeypatch):
    m, calls = _load_mwatch(tmp_path, monkeypatch)
    csv_host = tmp_path / "host" / "v1/matlab/outputs/yoonsung/drought_compare_2012_summary.csv"
    csv_host.parent.mkdir(parents=True)
    csv_host.write_text("county_fips,pearson_r_precip_vs_deficit,n_for_r\n17113,-0.865331917755845,4\n"
                        "19169,-0.865331917755845,4\n", encoding="utf-8")
    base = "/data/processed/v1/matlab/outputs/yoonsung/"
    _write_log(tmp_path, "yoonsung", [
        {"script": "drought_compare_2012", "resolved": "drought_compare_2012", "success": True, "seconds": 3.2,
         "files": [{"path": base + "drought_compare_2012_summary.csv", "bytes": 120, "rows": 2},
                   {"path": base + "drought_compare_2012.png", "bytes": 50000, "rows": None}]},
        {"script": "yoonsung_s2s_box", "resolved": "yoonsung_s2s_box", "success": True, "seconds": 1, "files": []}])
    state: dict = {}
    assert m.scan_once(state) == [("yoonsung", "summary")]
    assert m.scan_once(state) == []
    posts = [c for c in calls if c[0] == "POST"]
    assert len(posts) == 1
    msg = posts[0][2]["message"]
    assert msg.startswith("@yoonsung") and "2행" in msg and "pearson_r_precip_vs_deficit = -0.865, n=4" in msg
    assert base + "drought_compare_2012.png" in msg
    assert not list((tmp_path / "fixq").glob("*.json"))


def test_incomplete_log_waits_and_new_run_handled(tmp_path, monkeypatch):
    m, calls = _load_mwatch(tmp_path, monkeypatch)
    step = {"script": "slide_figures", "success": True, "files": []}
    _write_log(tmp_path, "jieun", [step], run_id="r1", complete=False)
    state: dict = {}
    assert m.scan_once(state) == []
    _write_log(tmp_path, "jieun", [step], run_id="r1", complete=True)
    assert m.scan_once(state) == [("jieun", "summary")]
    _write_log(tmp_path, "jieun", [step], run_id="r2", complete=True)
    assert m.scan_once(state) == [("jieun", "summary")]


def test_worker_mentions_run_all_and_accepts_script():
    text = (ROOT / "infra" / "matlab" / "fixq_worker.py").read_text(encoding="utf-8")
    assert "run_all_{user}.m` 을 다시 Run ▶" in text and "닫았다 열 필요 없이" in text
    assert 'job.get("script")' in text
