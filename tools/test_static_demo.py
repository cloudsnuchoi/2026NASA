"""E2E check of the static GitHub Pages demo with the live API blocked.

Usage: /srv/hackathon/venv/bin/python tools/test_static_demo.py
Serves docs/ on 127.0.0.1:8771, aborts every request to the live API (trycloudflare, :8090, :8095),
runs the 4 presets (Corn+Soy and Corn+Soy+Wheat), one /explain, one custom polygon.
Screenshots -> docs/screens/static/.
"""

import functools
import http.server
import sys
import threading
from pathlib import Path

import pytest

sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "screens" / "static"
SHOTS.mkdir(parents=True, exist_ok=True)
PORT = 8771

handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / "docs"))
handler.log_message = lambda *a, **k: None
srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()

PRESETS = {"19169": "story-ia", "17113": "mclean-il", "31109": "lancaster-ne", "39159": "union-oh"}
fails, blocked = [], []


def block(route):
    blocked.append(route.request.url)
    route.abort()


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1400, "height": 1000})
    ctx.route("**/*trycloudflare.com/**", block)
    ctx.route("http://127.0.0.1:8090/**", block)
    ctx.route("http://127.0.0.1:8095/**", block)
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))

    def start():
        page.goto(f"http://127.0.0.1:{PORT}/demo/")
        page.wait_for_selector("#static-banner", timeout=15000)
        page.click("#btn-skip-to-map")
        page.wait_for_function("document.querySelectorAll('.leaflet-interactive').length > 5", timeout=15000)

    for i, (fips, slug) in enumerate(PRESETS.items()):
        for crops in (["Corn", "Soy"], ["Corn", "Soy", "Wheat"]):
            start()
            page.click(f"[data-preset='{fips}']")
            page.click("#btn-to-crops")
            for c in crops:
                page.click(f"[data-crop='{c}']")
            page.click("#btn-run")
            page.wait_for_selector("#page-results.active", timeout=30000)
            t1, t2 = page.inner_text("#tier1"), page.inner_text("#tier2")
            banner = page.inner_text("#static-banner")
            ok = ("screening estimate" in t1.lower() and "Strategy A" in t2 and "unavailable" not in (t1 + t2)
                  and "static snapshot, generated 2026-11-15" in banner)
            tag = f"{slug}-{'-'.join(c.lower() for c in crops)}"
            if i == 0 and len(crops) == 2:
                page.click("[data-explain='A']")
                page.wait_for_function("document.querySelector('.explain-out').textContent.length > 80", timeout=10000)
                ex = page.inner_text(".explain-out")
                ok = ok and "AI-generated" in ex
                print("explain:", ex[:120].replace("\n", " "))
            page.wait_for_timeout(1500)
            page.screenshot(path=str(SHOTS / f"{tag}.png"), full_page=True)
            print("PASS" if ok else "FAIL", tag)
            if not ok:
                fails.append(tag)

    # custom polygon (not a preset) -> needs live server
    start()
    page.evaluate("window.__artfarmMap.setView([40.0, -95.0], 12)")
    box = page.locator("#map").bounding_box()
    for dx, dy in ((-80, -80), (80, -80), (80, 80), (-80, 80)):
        page.mouse.click(box["x"] + box["width"] / 2 + dx, box["y"] + box["height"] / 2 + dy)
    page.click("#btn-to-crops")
    page.click("[data-crop='Corn']")
    page.click("[data-crop='Soy']")
    page.click("#btn-run")
    page.wait_for_selector("#page-results.active", timeout=30000)
    t1 = page.inner_text("#tier1")
    ok = "needs the live server" in t1
    page.screenshot(path=str(SHOTS / "custom-polygon-needs-live.png"), full_page=True)
    print("PASS" if ok else "FAIL", "custom-polygon")
    if not ok:
        fails.append("custom")
    b.close()

print("blocked live-API requests:", len(blocked), "page errors:", errs)
srv.shutdown()
sys.exit(1 if fails or errs else 0)
