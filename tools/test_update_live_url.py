import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import update_live_url as u  # noqa: E402

T0 = datetime(2026, 11, 15, 13, 0, tzinfo=timezone.utc)
T1 = datetime(2026, 11, 15, 14, 0, tzinfo=timezone.utc)


def test_writes_then_unchanged_then_new_url(tmp_path):
    src, out = tmp_path / "demo_url.txt", tmp_path / "demo" / "live_url.json"
    src.write_text("https://a-b-c.trycloudflare.com/\n")
    assert u.update(src, out, T0) is True
    assert json.loads(out.read_text()) == {"url": "https://a-b-c.trycloudflare.com", "updated": "2026-11-15T22:00:00+09:00"}
    assert u.update(src, out, T1) is False  # same URL keeps the first-seen timestamp
    assert json.loads(out.read_text())["updated"] == "2026-11-15T22:00:00+09:00"
    src.write_text("https://d-e-f.trycloudflare.com")
    assert u.update(src, out, T1) is True
    assert json.loads(out.read_text())["url"] == "https://d-e-f.trycloudflare.com"


def test_invalid_or_missing_src_leaves_out_alone(tmp_path):
    out = tmp_path / "live_url.json"
    out.write_text('{"url": "https://keep.example", "updated": "x"}')
    assert u.update(tmp_path / "missing.txt", out) is None
    bad = tmp_path / "bad.txt"
    bad.write_text("http://insecure.example")
    assert u.update(bad, out) is None
    assert json.loads(out.read_text())["url"] == "https://keep.example"
