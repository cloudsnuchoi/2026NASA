"""Write docs/demo/live_url.json ({"url", "updated"}) from the quick-tunnel URL in demo_url.txt.

The trycloudflare quick-tunnel URL changes whenever the tunnel restarts, so the static demo on GitHub Pages
reads this file at runtime for its "Live version →" header link (no link if the file is missing or invalid).
The file is rewritten only when the URL changes, so `updated` is the time the URL was first seen.

Usage: python3 tools/update_live_url.py [--src /srv/hackathon/state/status/demo_url.txt] [--out docs/demo/live_url.json]
Exit 0 = written or unchanged, 1 = no valid https URL in --src (existing --out left untouched).
"""

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

KST = timezone(timedelta(hours=9))
DEFAULT_SRC = Path("/srv/hackathon/state/status/demo_url.txt")
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "docs" / "demo" / "live_url.json"


def read_url(src: Path) -> str | None:
    try:
        u = src.read_text(encoding="utf-8").strip().rstrip("/")
    except OSError:
        return None
    return u if u.startswith("https://") and " " not in u and "\n" not in u else None


def update(src: Path, out: Path, now: datetime | None = None) -> bool | None:
    """Return True if written, False if the URL is unchanged, None if src has no valid URL."""
    url = read_url(src)
    if url is None:
        return None
    try:
        if json.loads(out.read_text(encoding="utf-8")).get("url") == url:
            return False
    except (OSError, ValueError, AttributeError):
        pass
    stamp = (now or datetime.now(KST)).astimezone(KST).isoformat(timespec="seconds")
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    tmp.write_text(json.dumps({"url": url, "updated": stamp}, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(out)
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    a = ap.parse_args()
    r = update(a.src, a.out)
    print({True: f"live_url written: {a.out}", False: "live_url unchanged", None: f"no valid https URL in {a.src}"}[r])
    return 1 if r is None else 0


if __name__ == "__main__":
    raise SystemExit(main())
