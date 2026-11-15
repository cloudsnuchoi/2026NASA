#!/usr/bin/env python3
"""Direct member notices from server bots (no supervisor relay).

notify(user, room, text, kind, file) posts in ``1on1-<user>`` with the orchestrator bot token, always with an
``@<user>`` mention, appends ``<ISO time>\\t<room>\\t<one-line text>`` to /srv/hackathon/state/notify.log and records
the dedupe key ``user|kind|file`` in /srv/hackathon/state/notify_sent.json so the same notice is never sent twice.
The token is read from the orchestrator .env at call time and never printed.

CLI (one-off, step 3 of the NOTIFY lane):  python3 notify.py announce-extras
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable, Optional

KST = dt.timezone(dt.timedelta(hours=9))
LOG = Path(os.environ.get("NOTIFY_LOG", "/srv/hackathon/state/notify.log"))
SENT = Path(os.environ.get("NOTIFY_SENT", "/srv/hackathon/state/notify_sent.json"))
WORK = Path(os.environ.get("NOTIFY_WORK", "/srv/hackathon/data/processed/v1/matlab/work"))
ENV = "/srv/hackathon/projects/2026NASA/infra/orchestrator/.env"
API = "http://127.0.0.1:8065/api/v4"
HELPER = "artfarm_run_logged.m"
_channels: dict[str, str] = {}

NEW_SCRIPT = ("@{user} 🆕 {desc}\n📂 ~/Documents/MATLAB/work/{file}\n"
              "▶ 파일을 열고 Run ▶만 눌러 주세요. 오류는 봇이 자동으로 읽습니다.")
GROUP = ("@{user} 이제 캡처·붙여넣기 안 하셔도 됩니다. run_all_{user}.m을 열고 Run ▶만 누르세요. "
         "오류와 결과는 봇이 자동으로 읽고, 고쳐지면 여기로 알려 드립니다.")
GROUP_WOOCHAN = ("\n그동안 오류 문구와 캡처를 여러 번 붙여 넣게 해 드려 죄송합니다.\n"
                 "남은 일은 하나입니다: 계수 출처 표(guides/woochan.md의 계수 출처 항목)를 채워 주세요.")


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
    if room not in _channels:
        team = api("GET", "/teams/name/" + urllib.parse.quote(_env("MM_TEAM")))
        _channels[room] = api("GET", f"/teams/{team['id']}/channels/name/{urllib.parse.quote(room)}")["id"]
    return _channels[room]


# ------------------------------------------------------------------ dedupe + log
def key(user: str, kind: str, file: str = "") -> str:
    return f"{user}|{kind}|{file}"


def load_sent() -> dict:
    try:
        return json.loads(SENT.read_text(encoding="utf-8"))
    except Exception:
        return {}


def was_sent(user: str, kind: str, file: str = "") -> bool:
    return key(user, kind, file) in load_sent()


def mark_sent(user: str, kind: str, file: str = "", at: str = "", post_id: str = "") -> None:
    sent = load_sent()
    sent[key(user, kind, file)] = {"at": at or now_iso(), "post_id": post_id}
    SENT.parent.mkdir(parents=True, exist_ok=True)
    tmp = SENT.with_suffix(".tmp")
    tmp.write_text(json.dumps(sent, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(SENT)


def now_iso() -> str:
    return dt.datetime.now(KST).isoformat(timespec="seconds")


def one_line(text: str, limit: int = 300) -> str:
    s = " ⏎ ".join(ln.strip() for ln in text.strip().splitlines() if ln.strip()).replace("\t", " ")
    return s if len(s) <= limit else s[: limit - 1] + "…"


def log_line(room: str, text: str, at: str = "") -> str:
    line = f"{at or now_iso()}\t{room}\t{one_line(text)}"
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    return line


def with_mention(user: str, text: str) -> str:
    return text if text.lstrip().startswith(f"@{user}") else f"@{user} {text}"


def notify(user: str, room: str, text: str, kind: str = "info", file: str = "", root_id: str = "",
           post_fn: Optional[Callable[[str, str], str]] = None, dedupe: bool = True) -> Optional[str]:
    """Post once per (user, kind, file). Returns the post id, or None when already sent.

    post_fn(text, root_id) -> post id lets callers (mwatch, fixq) reuse their own channel/thread; default posts in
    ``room`` via the bot token."""
    room = room or f"1on1-{user}"
    if dedupe and was_sent(user, kind, file):
        return None
    msg = with_mention(user, text)
    if post_fn is None:
        pid = api("POST", "/posts", {"channel_id": channel_id(room), "root_id": root_id, "message": msg})["id"]
    else:
        pid = post_fn(msg, root_id)
    log_line(room, msg)
    if dedupe:
        mark_sent(user, kind, file, post_id=pid or "")
    return pid


# ------------------------------------------------------------------ new-script notices
def describe(path: Path) -> str:
    """First %-comment line of a .m file, without the leading %/%% and an all-caps NAME token."""
    try:
        for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
            s = ln.strip()
            if s.startswith("%"):
                s = s.lstrip("%").strip()
                s = re.sub(r"^[A-Z][A-Z0-9_]+\s+", "", s)
                if s:
                    return s
    except OSError:
        pass
    return path.stem


def is_announceable(name: str) -> bool:
    return name.endswith(".m") and name != HELPER and not name.lower().startswith("untitled")


def new_script_text(user: str, path: Path) -> str:
    desc = describe(path)
    if path.stem.endswith("_fixed"):
        desc = "수정본: " + desc
    return NEW_SCRIPT.format(user=user, desc=desc, file=path.name)


def announce_script(user: str, path: Path, post_fn=None) -> Optional[str]:
    kind = "fixed-script" if path.stem.endswith("_fixed") else "new-script"
    return notify(user, f"1on1-{user}", new_script_text(user, path), kind=kind, file=path.name, post_fn=post_fn)


# ------------------------------------------------------------------ step 3 (one-off)
EXTRAS = {"yoonsung": ["yoonsung_nldas_2012.m", "yoonsung_season_anomaly.m", "yoonsung_s2s_box.m"],
          "jimin": ["jimin_growing_season.m", "jimin_ndvi_anomaly.m", "jimin_bare_vs_rye.m"]}


def announce_extras(since_kst=dt.datetime(2026, 11, 15, 20, 0, tzinfo=KST)) -> dict:
    """Send the template for extras not individually announced by a bot since 20:00 KST; backfill the rest."""
    me = api("GET", "/users/me")["id"]
    since = int(since_kst.timestamp() * 1000)
    report: dict = {"sent": [], "backfilled": [], "missing": []}
    for user, files in EXTRAS.items():
        room = f"1on1-{user}"
        posts = sorted(api("GET", f"/channels/{channel_id(room)}/posts?since={since}")["posts"].values(),
                       key=lambda p: p["create_at"])
        bot_posts = [p for p in posts if p["user_id"] == me and not p.get("type")]
        for f in files:
            path = WORK / user / f
            if not path.is_file():
                report["missing"].append(f"{user}/{f}")
                continue
            kind = "new-script"
            if was_sent(user, kind, f):
                continue
            # "individually announced" = a bot post that names this file and no other extra script
            hit = next((p for p in bot_posts if f in p["message"]
                        and not any(o in p["message"] for o in files if o != f)), None)
            if hit:
                at = dt.datetime.fromtimestamp(hit["create_at"] / 1000, KST).isoformat(timespec="seconds")
                log_line(room, "[backfill] " + hit["message"], at=at)
                mark_sent(user, kind, f, at=at, post_id=hit["id"])
                report["backfilled"].append(f"{user}/{f} @ {at}")
            else:
                announce_script(user, path)
                report["sent"].append(f"{user}/{f}")
    return report


if __name__ == "__main__":
    if sys.argv[1:] == ["announce-extras"]:
        print(json.dumps(announce_extras(), ensure_ascii=False, indent=1))
    else:
        print(__doc__)
