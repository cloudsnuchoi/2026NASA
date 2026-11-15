"""RESTORE lane: capture mockup v8 vs docs/demo (static) vs live frontend (local uvicorn) per step.

Usage: /srv/hackathon/venv/bin/python tools/capture_restore.py [--live http://127.0.0.1:8098] [--mockup /srv/hackathon/inbox/mockup-v8.html]
Output: docs/screens/restore/{mockup,demo,live}-{map,crops,results,compare}-{1280,390}.png (viewport captures).
"""

import argparse
import functools
import http.server
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "screens" / "restore"
OUT.mkdir(parents=True, exist_ok=True)
ap = argparse.ArgumentParser()
ap.add_argument("--live", default="http://127.0.0.1:8098")
ap.add_argument("--mockup", default="/srv/hackathon/inbox/mockup-v8.html")
ap.add_argument("--only", default="mockup,demo,live")
a = ap.parse_args()

PORT = 8772
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / "docs"))
handler.log_message = lambda *x, **k: None
srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()


def shot(page, name):
    page.wait_for_timeout(1200)
    page.screenshot(path=str(OUT / f"{name}.png"))
    print("saved", name)


def run_ours(page, kind, base, w):
    page.goto(base)
    page.click("#btn-skip-to-map")
    page.wait_for_function("document.querySelectorAll('.leaflet-interactive').length > 5", timeout=30000)
    page.click("[data-preset='19169']")
    page.wait_for_function("!document.querySelector('#btn-to-crops').disabled && !/…|—/.test(document.querySelector('#env-temp').textContent)", timeout=120000)
    shot(page, f"{kind}-map-{w}")
    page.click("#btn-to-crops")
    page.click("#crop-cards-grid [data-crop='Corn']")
    page.click("#crop-cards-grid [data-crop='Soy']")
    shot(page, f"{kind}-crops-{w}")
    page.click("#btn-confirm-crops")
    page.wait_for_selector("#page-results.active", timeout=180000)
    shot(page, f"{kind}-results-{w}")
    page.evaluate("document.querySelector('#tier2').scrollIntoView()")
    shot(page, f"{kind}-compare-{w}")


def run_mockup(page, w):
    page.goto("file://" + a.mockup)
    page.click("#btn-skip-to-map")
    page.wait_for_timeout(1500)
    page.click("#btn-sample-iowa")
    page.wait_for_timeout(4000)
    shot(page, f"mockup-map-{w}")
    page.click("#btn-to-crops")
    page.wait_for_timeout(500)
    page.click("#btn-reset-crops")
    btns = page.locator("#crop-cards-grid button")
    btns.nth(0).click()
    btns.nth(1).click()
    shot(page, f"mockup-crops-{w}")
    page.click("#btn-confirm-crops")
    page.wait_for_selector("#page-results.active", timeout=120000)
    shot(page, f"mockup-results-{w}")
    page.evaluate("document.querySelector('#all-scenarios-tbody').scrollIntoView()")
    shot(page, f"mockup-compare-{w}")


with sync_playwright() as p:
    b = p.chromium.launch()
    for w, h in ((1280, 900), (390, 844)):
        for kind in a.only.split(","):
            ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=1, is_mobile=w < 500, has_touch=w < 500)
            page = ctx.new_page()
            errs = []
            page.on("pageerror", lambda e, errs=errs: errs.append(str(e)))
            page.on("console", lambda m, errs=errs: m.type == "error" and errs.append("console: " + m.text))
            try:
                if kind == "mockup":
                    run_mockup(page, w)
                elif kind == "demo":
                    run_ours(page, "demo", f"http://127.0.0.1:{PORT}/demo/", w)
                else:
                    run_ours(page, "live", a.live + "/", w)
            except Exception as exc:  # noqa: BLE001
                print("FAIL", kind, w, type(exc).__name__, str(exc)[:300])
                page.screenshot(path=str(OUT / f"_fail-{kind}-{w}.png"))
            print(kind, w, "errors:", errs[:5])
            ctx.close()
    b.close()
srv.shutdown()
