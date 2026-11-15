#!/usr/bin/env python3
"""MATLAB run-log watcher (VPS, tmux mwatch). Members only press Run on run_all_<name>.m.

Every 30 s: read outputs/<name>/run_log.json (written by matlab/autorun/artfarm_run_logged.m).
New completed log ->
  * any step failed: post a short bot message in 1on1-<name>, then enqueue a fixq job (same JSON shape as the bot,
    root_id/post_id = that real post id) for infra/matlab/fixq_worker.py;
  * all succeeded: post a result summary (@mention, rows/files, 1-2 key numbers) in 1on1-<name>.
Also watches work/<name>/: a NEW .m (incl. fixq's *_fixed.m "수정본"; not the artfarm_run_logged.m helper) gets the
approved "🆕 ... Run ▶" notice. Every post goes through infra/matlab/notify.py (notify.log + dedupe).
The first collected woochan run_log (MAUTO verification) triggers ONE group notice to all 4 rooms and writes
/srv/hackathon/state/status/mauto_verified.json.
State (/srv/hackathon/state/mwatch.json) makes each log handled exactly once. The bot token is never printed.
"""
from __future__ import annotations

import csv
import json
import datetime as dt
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import notify  # noqa: E402

OUT = Path(os.environ.get("MWATCH_OUT", "/srv/hackathon/data/processed/v1/matlab/outputs"))
STATE = Path(os.environ.get("MWATCH_STATE", "/srv/hackathon/state/mwatch.json"))
FIXQ = Path(os.environ.get("MWATCH_FIXQ", "/srv/hackathon/state/fixq"))
WORK = Path(os.environ.get("MWATCH_WORK", "/srv/hackathon/data/processed/v1/matlab/work"))
VERIFIED = Path(os.environ.get("MWATCH_VERIFIED", "/srv/hackathon/state/status/mauto_verified.json"))
SETTLE_S = 20  # a new .m must be untouched this long before it is announced (no half-written files)
ENV = "/srv/hackathon/projects/2026NASA/infra/orchestrator/.env"
API = "http://127.0.0.1:8065/api/v4"
USERS = ("woochan", "yoonsung", "jimin", "jieun")
CONTAINER_ROOT, HOST_ROOT = "/data/processed", "/srv/hackathon/data/processed"
STALE_S = 900  # an incomplete log untouched this long (MATLAB stopped mid-run) is handled anyway
_channels: dict[str, str] = {}


def _env(key: str) -> str:
    vals = [ln.split("=", 1)[1].strip() for ln in open(ENV, encoding="utf-8") if ln.startswith(key + "=")]
    return vals[-1] if vals else ""


def api(method: str, path: str, body=None):
    req = urllib.request.Request(API + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + _env("MM_BOT_TOKEN"),
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def channel_id(room: str) -> str:
    if room in _channels:
        return _channels[room]
    cid = ""
    try:
        team = api("GET", "/teams/name/" + urllib.parse.quote(_env("MM_TEAM")))
        cid = api("GET", f"/teams/{team['id']}/channels/name/{urllib.parse.quote(room)}")["id"]
    except Exception:
        for p in sorted((FIXQ / "done").glob("*.json"), reverse=True):  # fallback: earlier bot jobs
            try:
                j = json.loads(p.read_text(encoding="utf-8"))
                if j.get("room") == room and j.get("channel_id"):
                    cid = j["channel_id"]
                    break
            except Exception:
                continue
    if cid:
        _channels[room] = cid
    return cid


def post(cid: str, text: str, root_id: str = "") -> str:
    return api("POST", "/posts", {"channel_id": cid, "root_id": root_id, "message": text})["id"]


def say(user: str, text: str, kind: str, file: str, root_id: str = "") -> str:
    """Post in 1on1-<user> through notify (logged + deduped). Returns the post id (also when already sent)."""
    room = f"1on1-{user}"
    cid = channel_id(room)
    if not cid:
        raise RuntimeError(f"no channel for {room}")
    pid = notify.notify(user, room, text, kind=kind, file=file, root_id=root_id,
                        post_fn=lambda msg, rid: post(cid, msg, rid))
    if pid is None:
        pid = (notify.load_sent().get(notify.key(user, kind, file)) or {}).get("post_id", "")
    return pid


def host(p: str) -> Path:
    return Path(HOST_ROOT + p[len(CONTAINER_ROOT):]) if p.startswith(CONTAINER_ROOT) else Path(p)


def _steps(log: dict) -> list[dict]:
    s = log.get("steps") or []
    return [s] if isinstance(s, dict) else list(s)


def _files(step: dict) -> list[dict]:
    f = step.get("files") or []
    return [f] if isinstance(f, dict) else list(f)


def key_numbers(path: Path) -> list[str]:
    """1-2 headline numbers from a result CSV: Pearson r (+ n) if present, else nothing."""
    out = []
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
    except Exception:
        return out
    if not rows:
        return out
    for col in rows[0]:
        if col.lower().startswith("pearson_r"):
            vals = [r[col] for r in rows if r.get(col) not in ("", "NaN", None)]
            if vals:
                n_col = next((c for c in rows[0] if c.lower().startswith("n_for_r")), None)
                n = f", n={rows[0][n_col]}" if n_col and rows[0].get(n_col) else ""
                out.append(f"{col} = {float(vals[0]):.3f}{n}")
            break
    return out


def summary_text(user: str, log: dict) -> str:
    lines = [f"@{user} ✅ **MATLAB 실행 완료** (run `{log.get('run_id', '')}`) — 모든 스크립트가 성공했어요."]
    for st in _steps(log):
        files = _files(st)
        lines.append(f"- **{st.get('resolved') or st.get('script')}** ({float(st.get('seconds') or 0):.0f}초, 파일 {len(files)}개)")
        for f in files:
            p = f.get("path", "")
            name = p.rsplit("/", 1)[-1]
            if name.lower().endswith(".csv"):
                rows = f.get("rows")
                extra = key_numbers(host(p))
                lines.append(f"  - `{name}`: {rows if rows is not None else '?'}행" + (" · " + " · ".join(extra) if extra else ""))
            elif name.lower().endswith(".png"):
                lines.append(f"  - 그림 `{p}`")
            else:
                lines.append(f"  - `{name}` ({f.get('bytes', '?')} bytes)")
    lines.append("결과 파일은 위 경로(컨테이너 기준)에 있어요. 고칠 게 없으면 여기서 끝!")
    return "\n".join(lines)


def error_text(log: dict, failed: list[dict]) -> str:
    parts = []
    for st in failed:
        parts.append(f"[run_all 실행 로그] {st.get('resolved') or st.get('script')} 실패\n"
                     f"error_id: {st.get('error_id', '')}\nmessage: {st.get('error_message', '')}\n"
                     f"report:\n{(st.get('error_report') or '')[:3000]}\n"
                     f"output tail:\n{(st.get('output_tail') or '')[-1500:]}")
    return "\n\n".join(parts)


def handle(user: str, log: dict) -> str:
    room = f"1on1-{user}"
    cid = channel_id(room)
    if not cid:
        raise RuntimeError(f"no channel for {room}")
    run_key = f"{log.get('run_id', '')}@{len(_steps(log))}"
    failed = [s for s in _steps(log) if not s.get("success")]
    if failed:
        names = ", ".join(str(s.get("resolved") or s.get("script")) for s in failed)
        pid = say(user, f"🤖 실행 로그를 받았어요: {names} 오류 → 서버가 고치는 중", "error", run_key)
        first = failed[0]
        script = str(first.get("resolved") or first.get("script") or "")
        job = {"user": user, "room": room, "channel_id": cid, "root_id": pid, "post_id": pid,
               "message": error_text(log, failed), "images": 0, "at": time.time(),
               "source": "mwatch", "run_id": log.get("run_id", ""),
               "script": script if script.endswith(".m") else script + ".m"}
        FIXQ.mkdir(parents=True, exist_ok=True)
        tmp = FIXQ / f".{int(time.time() * 1000)}_{user}.tmp"
        tmp.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
        tmp.rename(FIXQ / f"{int(time.time() * 1000)}_{user}.json")
        return "fix"
    say(user, summary_text(user, log), "result", run_key)
    return "summary"


GROUP_USERS = ("woochan", "yoonsung", "jimin", "jieun")


def group_notice(log_path: Path, log: dict, action: str) -> None:
    """MAUTO verified: woochan's own run_all run was collected -> tell all 4 rooms once (dedupe in notify)."""
    if VERIFIED.exists():
        return
    sent = []
    for u in GROUP_USERS:
        text = notify.GROUP.format(user=u) + (notify.GROUP_WOOCHAN if u == "woochan" else "")
        try:
            pid = say(u, text, "group", "run_all")
            sent.append({"user": u, "post_id": pid})
        except Exception as exc:
            sent.append({"user": u, "error": type(exc).__name__})
    VERIFIED.parent.mkdir(parents=True, exist_ok=True)
    VERIFIED.write_text(json.dumps({
        "verified_at": dt.datetime.now(notify.KST).isoformat(timespec="seconds"),
        "run_log": str(log_path), "run_log_mtime": dt.datetime.fromtimestamp(log_path.stat().st_mtime, notify.KST)
        .isoformat(timespec="seconds"), "run_id": log.get("run_id"), "user": log.get("user"),
        "steps": [{"script": s.get("resolved") or s.get("script"), "success": bool(s.get("success"))} for s in _steps(log)],
        "mwatch_action": action, "evidence": "fixq job enqueued" if action == "fix" else "result summary posted",
        "group_notice": sent}, ensure_ascii=False, indent=1), encoding="utf-8")


def is_real_woochan_log(log: dict) -> bool:
    """Written by artfarm_run_logged.m via run_all_woochan.m: user field, a real run_id, at least one step."""
    return log.get("user") == "woochan" and str(log.get("run_id", "")) not in ("", "unknown") and bool(_steps(log))


def scan_scripts(state: dict) -> list[tuple[str, str]]:
    """Announce .m files that appeared in work/<name>/ since the last scan (first scan = baseline, no posts)."""
    out = []
    seen_all = state.setdefault("mfiles", {})
    for user in USERS:
        d = WORK / user
        if not d.is_dir():
            continue
        names = sorted(p.name for p in d.glob("*.m") if p.is_file())
        if user not in seen_all:
            seen_all[user] = names
            continue
        seen = set(seen_all[user])
        for name in names:
            p = d / name
            if name in seen or time.time() - p.stat().st_mtime < SETTLE_S:
                continue
            if notify.is_announceable(name) and p.stat().st_size > 0:
                kind = "fixed-script" if p.stem.endswith("_fixed") else "new-script"
                try:
                    say(user, notify.new_script_text(user, p), kind, name)
                except Exception as exc:
                    print(f"{time.strftime('%H:%M:%S')} {user}: announce {name} failed {type(exc).__name__}", flush=True)
                    continue
                out.append((user, name))
            seen_all[user] = sorted(seen | {name})
            seen.add(name)
    return out


def scan_once(state: dict) -> list[tuple[str, str]]:
    done = []
    for user in USERS:
        p = OUT / user / "run_log.json"
        if not p.is_file():
            continue
        mtime = p.stat().st_mtime
        try:
            log = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue  # being written; retry next tick
        key = f"{log.get('run_id', '')}@{len(_steps(log))}"
        if state.get(user) == key:
            continue
        if not log.get("complete") and time.time() - mtime < STALE_S:
            continue
        try:
            action = handle(user, log)
        except Exception as exc:
            print(f"{time.strftime('%H:%M:%S')} {user}: handle failed {type(exc).__name__}", flush=True)
            continue
        state[user] = key
        save(state)
        print(f"{time.strftime('%H:%M:%S')} {user}: {key} -> {action}", flush=True)
        done.append((user, action))
        if user == "woochan" and is_real_woochan_log(log):
            try:
                group_notice(p, log, action)
            except Exception as exc:
                print(f"{time.strftime('%H:%M:%S')} group notice failed {type(exc).__name__}", flush=True)
    scan_scripts(state)
    save(state)
    return done


def save(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state), encoding="utf-8")


def main() -> None:
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    print(f"mwatch started; watching {OUT}", flush=True)
    while True:
        try:
            scan_once(state)
        except Exception as exc:
            print("scan failed", type(exc).__name__, flush=True)
        time.sleep(30)


if __name__ == "__main__":
    main()
