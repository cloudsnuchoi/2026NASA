# ruff: noqa: E701, E702, E731
"""UX error-state check: /api/quick mocked 429 -> plain-language message + information gap + Retry -> real result.

Usage: /srv/hackathon/venv/bin/python infra/web/ux/error_check.py <base-url> <out-dir>
"""

import sys
import time
from playwright.sync_api import sync_playwright

URL = sys.argv[1].rstrip("/") + "/"
OUT = sys.argv[2]
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    fail = {"on": True}

    def handler(route):
        if fail["on"]:
            route.fulfill(status=429, content_type="application/json", body='{"detail":"rate limit: 60 requests/min"}')
        else:
            route.continue_()

    pg.route("**/api/quick", handler)
    pg.goto(URL + "#map", wait_until="networkidle")
    time.sleep(1.5)
    pg.evaluate("window.__artfarmMap.setView([40.2,-89.0],15)")
    time.sleep(1.5)
    box = pg.locator("#map").bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    for dx, dy in [(-60, -60), (60, -60), (60, 60), (-60, 60)]:
        pg.touchscreen.tap(cx + dx, cy + dy)
        time.sleep(0.3)
    pg.click("#btn-to-crops")
    pg.click('[data-crop="Corn"]')
    pg.click('[data-crop="Wheat"]')
    pg.click("#btn-run")
    pg.wait_for_selector("#page-results.active", timeout=60000)
    time.sleep(1)
    t = pg.inner_text("#tier1")
    print("ERR STATE:", t[:300].replace("\n", " | "))
    assert "Too many requests" in t and "Information gap" in t
    pg.screenshot(type="jpeg", quality=70, path=f"{OUT}/390-09-error-429.jpg")
    fail["on"] = False
    pg.click("[data-retry]")
    pg.wait_for_selector("#page-results.active", timeout=120000)
    time.sleep(1.5)
    t = pg.inner_text("#tier1")
    print("AFTER RETRY:", t[:120].replace("\n", " | "))
    assert "Quick Screen for your field" in t
    print("nav:", pg.inner_text("#results-nav").replace("\n", " | "), "| tier2:", pg.inner_text("#tier2")[:80])
    print("errors", errs)
    assert not errs
    b.close()
