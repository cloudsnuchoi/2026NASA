# ruff: noqa: E701, E702, E731
"""UX mobile check (docs/UX-AUDIT.md): screenshots + touch-target / font / overflow audit.

Usage: /srv/hackathon/venv/bin/python infra/web/ux/mobile_check.py <base-url> <out-dir> [360,390,768] [--no-run]
Hits /api/quick, /api/simulate etc. once per width (public demo is rate-limited to 60 req/min).
"""

import json
import sys
import time
from playwright.sync_api import sync_playwright

URL = sys.argv[1].rstrip("/") + "/"
OUT = sys.argv[2]
WIDTHS = [int(w) for w in (sys.argv[3] if len(sys.argv) > 3 else "360,390,768").split(",")]
RUN = "--no-run" not in sys.argv
AUDIT_JS = r"""
() => {
  const vis = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && e.closest('.app-page.active, #toast') !== null; };
  const small = [...document.querySelectorAll('button, a, input, select, [role=button], .leaflet-control a')]
    .filter(vis).map(e => { const r = e.getBoundingClientRect(); return {t: (e.innerText || e.getAttribute('aria-label') || e.title || e.tagName).trim().slice(0,40), w: Math.round(r.width), h: Math.round(r.height)}; })
    .filter(o => o.w < 44 || o.h < 44);
  const fonts = {};
  document.querySelectorAll('.app-page.active *').forEach(e => { if (!vis(e)) return;
    if (![...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) return;
    const f = parseFloat(getComputedStyle(e).fontSize); if (f < 12) fonts[f] = (fonts[f] || 0) + 1; });
  const overflow = [...document.querySelectorAll('.app-page.active *')].filter(e => { const r = e.getBoundingClientRect(); return r.right > innerWidth + 1 && vis(e); })
    .slice(0, 8).map(e => e.tagName + '.' + (e.className.baseVal ?? e.className).toString().slice(0, 50));
  return { docW: document.documentElement.scrollWidth, vw: innerWidth, small_targets: small, small_fonts_px: fonts, overflow };
}"""
report = {}
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in WIDTHS:
        r = report[w] = {}
        ctx = b.new_context(
            viewport={"width": w, "height": 844 if w < 700 else 1024}, device_scale_factor=1.5, is_mobile=w < 700, has_touch=True
        )
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(URL, wait_until="networkidle")
        time.sleep(1)
        pg.screenshot(type="jpeg", quality=70, path=f"{OUT}/{w}-01-first-screen.jpg")
        r["story"] = pg.evaluate(AUDIT_JS)
        pg.screenshot(type="jpeg", quality=70, path=f"{OUT}/{w}-02-story-full.jpg", full_page=True)
        pg.click("#btn-skip-to-map")
        time.sleep(2.5)
        pg.screenshot(type="jpeg", quality=70, path=f"{OUT}/{w}-03-map.jpg", full_page=True)
        r["map"] = pg.evaluate(AUDIT_JS)
        # touch vertices: zoom into a non-pilot area and tap 4 corners
        pg.evaluate("window.__artfarmMap.setView([40.2,-89.0],15)")
        time.sleep(2)
        box = pg.locator("#map").bounding_box()
        cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        d = min(box["width"], box["height"]) * 0.25
        for dx, dy in [(-d, -d), (d, -d), (d, d), (-d, d)]:
            pg.touchscreen.tap(cx + dx, cy + dy)
            time.sleep(0.35)
        r["touch_vertices"] = pg.inner_text("#m-vertices")
        r["touch_area"] = pg.inner_text("#m-area")
        r["tier"] = pg.inner_text("#m-tier")
        pg.locator("#map").scroll_into_view_if_needed()
        pg.screenshot(type="jpeg", quality=70, path=f"{OUT}/{w}-04-map-touch-4.jpg", full_page=True)
        # preset
        pg.click("#btn-clear")
        pg.click('[data-preset="19169"]')
        time.sleep(2)
        r["preset_tier"] = pg.inner_text("#m-tier")
        pg.click("#btn-to-crops")
        time.sleep(1)
        pg.click('[data-crop="Corn"]')
        pg.click('[data-crop="Soy"]')
        pg.screenshot(type="jpeg", quality=70, path=f"{OUT}/{w}-05-crops.jpg", full_page=True)
        r["crops"] = pg.evaluate(AUDIT_JS)
        if RUN:
            pg.click("#btn-run")
            time.sleep(1.2)
            pg.screenshot(type="jpeg", quality=70, path=f"{OUT}/{w}-06-loading.jpg")
            pg.wait_for_selector("#page-results.active", timeout=120000)
            time.sleep(2.5)
            pg.screenshot(type="jpeg", quality=70, path=f"{OUT}/{w}-07-results-top.jpg")
            pg.screenshot(type="jpeg", quality=70, path=f"{OUT}/{w}-08-results-full.jpg", full_page=True)
            r["results"] = pg.evaluate(AUDIT_JS)
            r["card_x"] = pg.evaluate(
                "[...document.querySelectorAll('#tier2 article')].map(a=>{const q=a.getBoundingClientRect();return [Math.round(q.x),Math.round(q.width)]})"
            )
            r["tier1_text_has_gap"] = pg.evaluate("document.querySelector('#tier1').innerText.slice(0,200)")
        r["errors"] = errs
        ctx.close()
    b.close()
print(json.dumps(report, indent=1, ensure_ascii=False))
