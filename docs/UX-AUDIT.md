# ART FARM UX audit (2026-11-15, UX lane)

Scope: the public demo (the tunnel URL in `state/status/demo_url.txt`) and `frontend/` on `origin/main` @ `bb5f690`, checked 20:17–20:40 KST. Method: source reading (`frontend/index.html`, `frontend/app.js`), Chromium/Playwright captures at 360, 390 and 768 px (touch emulation, DPR 2), and WCAG 2.x contrast ratios computed from the actual Tailwind/hex colours with alpha blending (script output reproduced below). All screenshots are in `docs/screens/mobile/` (JPEG, full-page captures downscaled 50 %, others 75 %). Everything in the "measured" columns comes from the capture run; nothing is estimated.

## 1. Summary

The demo works end to end on phones: no horizontal overflow at 360/390/768 px, four touch taps place four vertices and compute area (`4 / 4`, 35.8–58.7 ha in the test), the Story IA preset reaches Tier 1 + Tier 2, no JS errors. The honesty labels (screening estimate, relative-index tooltip, "possible range (scenario)", S7 checklist, AI-image badges) are present and visible.

The main weaknesses are presentation, not correctness:

1. **The first screen does not say what the tool does.** The hero headline is a slogan ("Standing Beside Farmers, Guided by Orbital Data."); the actual job ("compare crop-rotation options before planting") is the second clause of a paragraph, and the only CTA in the hero is a small "Launch Tool →" pill at the top right.
2. **The pilot-field results page is 16,600 px tall at 390 px** (8,300 CSS px ≈ 10 screens). The user's own Tier 1 quick screen starts after ~6,300 CSS px of Tier 2 content, with no way to jump.
3. **The "information gap" label fails contrast** (slate-400 on white, 2.56:1). The label that carries the project's honesty rule is the least legible text on the page.
4. **Touch targets below 44 px** on the map (Undo/Clear 28 px tall, zoom 30 px) and on all back buttons (38 px).
5. **Error states are raw** (`Quick Screen unavailable (HTTP 429)`), and if `/fields-geo` fails the preset buttons answer "Pilot fields still loading…" forever.

## 2. Judging-criteria view (Space Apps)

| Criterion | What a judge sees now | Gap | Fix id |
| --- | --- | --- | --- |
| Impact | Farmer-facing story, rotation comparison with water deficit and 2012 drought | Value proposition not stated in the first viewport; "who is it for / what do I get" needs scrolling | F1 |
| Creativity | Two-tier design (anywhere screen + pilot deep analysis), Prithvi + CDL, MC + CVaR | Hidden behind a very long results page on mobile | F3 |
| Validity | P10–P90 everywhere, CVaR definition, 2012 backtest, sources, information gaps, no ranking | Range notation inconsistent (`95–236`, `0 to 0`, `836–1,044`), "Water use vs A" on card A shows a meaningless `0% (P10–P90 0 to 0)`; chart legend draws P50 as a box | F6 |
| Relevance | NASA POWER, USGS 3DEP, NWS, CMIP6, FAO-56 named on the first screen | Fine | — |
| Presentation | Polished photography and colour; works at 360 px | Contrast failures on honesty labels, small fonts (9–10 px, 7.5 px subscripts), 28–38 px targets, crops page hides "Run" below the fold | F2, F4, F5, F7 |

## 3. Findings by area

### 3.1 First screen in 3 seconds (`{360,390,768}-01-first-screen.jpg`)

Visible without scrolling at 390 × 844: logo + "ART FARM / Field Shift: Adapting Farms with NASA Data", a data-source chip, the slogan, a 5-line paragraph, "Scroll to explore the story". A first-time reader learns *brand + NASA data*, not *what it computes for them*. PRD §10 step 1 wants "This is a decision-support tool. It does not replace farmer judgment." on the first screen; that sentence exists but is the last clause of the paragraph.

Fix F1: one-line value proposition directly under the slogan ("Compare crop-rotation options for a Corn Belt field — crop water demand, P10–P90 ranges and 2012-drought risk from NASA POWER and open data."), a "decision aid, does not replace your judgement" line kept, and a large primary CTA "Draw your field →" inside the hero. No layout change.

### 3.2 Information hierarchy

- Map page (`390-03-map.jpg`, `390-04-map-touch-4.jpg`): order on mobile is header → back button → map → legend → presets → geometry → Next. Good. The instruction says "Click the 4 corners"; on touch it should say "Tap". There is no in-map hint of which corner comes next.
- Crops page (`390-05-crops.jpg`): three 160 px crop photos stacked; the "Run screening" button is below the fold after selecting at 390 × 844.
- Results, pilot field (`390-08-results-full.jpg`): Tier 2 header → chart → 4 strategy cards (each ~1,000 CSS px, Evidence list identical on all four) → information gaps → S7 → Tier 1. The Tier 1 card heading is the engine name ("FAO-56 engine (ported from team MATLAB prototype V8)") rather than what the card shows.
- Results, outside field: amber "Deep analysis available in 4 pilot counties" notice, then Tier 1. Good.

Fix F3: a sticky in-page jump bar on results ("Deep analysis A–D · Quick screen · Checklist"), the repeated Evidence list collapsed into `<details>` with its count visible ("Evidence (4 sources)") — still present on every card, so the five card items are not omitted — and Tier 1 heading "Quick Screen for your field" with the engine name kept as the subtitle.

### 3.3 Readability

Text nodes under 12 px (computed font size, visible elements):

| Page | 7.5 px | 9 px | 10 px | 11 px |
| --- | ---: | ---: | ---: | ---: |
| Story | – | 6 | 4 | 10 |
| Map | – | – | 4 | 4 |
| Crops | – | – | 3 | 3 |
| Results (pilot) | 4 | 2 | 38 | 16 |

The 10 px nodes on results are mostly the P10–P90 ranges and CVaR — i.e. the uncertainty information that the project wants judges to notice. The 7.5 px nodes are `<sub>` inside 10 px text (CVaR<sub>10%</sub>). Fix F7: raise `text-[10px]` → 11.5–12 px for ranges and `text-[9px]`/`[10px]` labels in results.

### 3.4 Units and sources

Units are shown on almost every number (mm, mm/yr, °C, ha, ac, km, m, cm/cm). Sources are inline on Tier 1 tiles (NASA POWER, USGS 3DEP) and listed under "Assumptions & sources"; Tier 2 cards cite NASA POWER, FAO-56, SSURGO, CDL. Issues: the Tier 2 chart axis says `mm/yr` while the 2012 backtest dot is a single-season value in mm (the card says "mm deficit"); "Winter bare days P50" has no unit word ("days" only in the label); "Field context" mixes gSSURGO soil and NASA POWER precip without naming the precip source.

### 3.5 P10–P90 visualisation

- Chart (`390-08`, y≈1,600–2,300 px): floating bar = P10–P90, line = P50, diamond = CVaR, dot = 2012. The legend renders P50 as a filled rectangle (Chart.js uses the dataset's box unless `usePointStyle`), and the P10–P90 legend swatch is green although unmatched strategies are drawn grey. Bars pass non-text contrast only because of their 1 px `#24543e` border (fill alone 1.5:1).
- Text notation varies: `P10–P90 95–236`, `(P10–P90 0 to 0)`, `P10–P90 836–1,044` wrapping over two lines. Strategy A's "Water use vs A" is by definition 0 and should read "baseline".

Fix F6: `usePointStyle` legend, one formatter `P10–P90 a – b`, "baseline (A)" for A, `white-space: nowrap` on ranges.

### 3.6 Colour contrast (WCAG AA)

Normal text needs 4.5:1, large text (≥ 18.66 px bold) and UI/graphics 3:1. Ratios computed with alpha compositing on the actual background.

| Pair | Ratio | Need | Result |
| --- | ---: | ---: | --- |
| slate-500 #64748b on white (captions, P10–P90 small text) | 4.76:1 | 4.5 | PASS |
| slate-500 on #f3f5ee results bg (Tier 1 tiles) | 4.33:1 | 4.5 | **FAIL** |
| slate-400 #94a3b8 on white ("information gap", "(assumption)", units) | 2.56:1 | 4.5 | **FAIL** |
| slate-600 #475569 on white | 7.58:1 | 4.5 | PASS |
| amber-700 #b45309 on white ("screening estimate") | 5.02:1 | 4.5 | PASS |
| #5a9e2e on white ("TIER 1 · QUICK SCREEN") | 3.30:1 | 4.5 | **FAIL** |
| #2f6b1d on #82c341@20% ("matches your crops") | 5.61:1 | 4.5 | PASS |
| amber-900 on amber-100 (SCREENING ESTIMATE pill) | 8.15:1 | 4.5 | PASS |
| #0f291e on #82c341 (primary CTA) | 7.25:1 | 3.0 | PASS |
| white on #173a2b (dark buttons, toast) | 12.53:1 | 4.5 | PASS |
| amber-300 on #173a2b | 8.69:1 | 4.5 | PASS |
| emerald-100/80 on #173a2b (Tier 2 run line) | 7.71:1 | 4.5 | PASS |
| emerald-100/60 on white/10 over #173a2b (model id, profile disclaimer) | 4.09:1 | 4.5 | **FAIL** |
| emerald-100/75 on #173a2b (preset note) | 6.95:1 | 4.5 | PASS |
| white on white/12 over #173a2b (preset buttons) | 8.64:1 | 4.5 | PASS |
| white on emerald-950/20 over #74b93d (story badge "NASA POWER 10-yr…") | 3.31:1 | 4.5 | **FAIL** |
| #102a1b on white/25 over #74b93d (story badge) | 8.03:1 | 4.5 | PASS |
| emerald-200/70 on #183829 (endpoint mono 11 px) | 5.78:1 | 4.5 | PASS |
| slate-500 on amber-50 (S7 note) | 4.59:1 | 4.5 | PASS |
| amber-800 on white (Trade-offs) | 7.09:1 | 4.5 | PASS |
| emerald-800 on white (Benefits) | 7.68:1 | 4.5 | PASS |
| slate-700 on white | 10.35:1 | 4.5 | PASS |
| graphic: P10–P90 bar fill rgba(36,84,62,.25) on white | 1.52:1 | 3.0 | fill FAIL, border PASS |
| graphic: matched bar fill rgba(130,195,65,.55) on white | 1.50:1 | 3.0 | fill FAIL, border PASS |
| graphic: bar border #24543e on white | 8.70:1 | 3.0 | PASS |
| graphic: user polygon stroke #f7f6f0 vs dark field ≈#2c3a24 | 11.16:1 | 3.0 | PASS |
| graphic: pilot outline #f2c46d vs dark field ≈#2c3a24 | 7.42:1 | 3.0 | PASS |

Hero text sits on a photo with a black→green gradient; not computed (varies per pixel). Fix F2: slate-400 text → slate-500/600, `#5a9e2e` text → `#3d7a1f`, emerald-100/60 → /80, story badge text white → dark, slate-500 on `#f3f5ee` tiles → slate-600.

### 3.7 Mobile (360 / 390 / 768 px)

| Check | 360 | 390 | 768 |
| --- | --- | --- | --- |
| Document width = viewport (no horizontal scroll) | 360 ✓ | 390 ✓ | 768 ✓ |
| Touch: 4 taps → 4 vertices, area computed | 4/4, 35.77 ha | 4/4, 42.61 ha | 4/4, 58.65 ha |
| Preset Story IA → tier | Quick + Deep ✓ | ✓ | ✓ |
| Strategy cards stacking (x, width CSS px) | 1 col, 328 | 1 col, 358 | 2 col, 344 |
| Tables needing horizontal scroll | none (no `<table>`; CDL chips wrap) | none | none |
| Page JS errors | 0 | 0 | 0 |
| Pilot results page height (CSS px) | — | 8,300 | — |

Touch targets under 44 × 44 CSS px (measured):

| Element | Size | Pages |
| --- | --- | --- |
| Map Undo / Clear | 55 × 28 | map |
| Leaflet zoom + / − | 30 × 30 | map |
| "← Story", "← Map", "← Crops", "New field" | 80–99 × 38 | map, crops, results |
| Preset buttons | 140–328 × 42 | map |
| "Launch Tool →" (768 px) | 135 × 38 | story |
| S7 checkboxes | 13 × 13 (label row is clickable, 14–46 px tall) | results |
| Evidence links in cards | ≈ 280 × 31 (inline links in a list) | results |

Fix F4: `min-height: 44px` on all `button`s in pages, Leaflet zoom 44 px on `(pointer: coarse)`, checkbox 20 px with padded label, Undo/Clear 44 px.

### 3.8 Loading, error, information-gap states

- Loading: sunflower + rotating source messages; no elapsed time, no cancel. Acceptable (a Story preset ran in a few seconds).
- Tier 1 / Tier 2 failure: red box with the raw error text, e.g. `Quick Screen unavailable (HTTP 429)`. "Information gap — no fallback values" is correct honesty-wise; missing: plain-language cause (rate limit / upstream down) and a Retry button.
- `/fields-geo` failure: one toast; preset buttons then say "Pilot fields still loading…" indefinitely. Needs a retry and an honest message.
- `/explain` failure: "Explanation unavailable: <message>". OK, could add retry.
- Information gaps: rendered as `information gap` in slate-400 italic → contrast failure (§3.6). The full-page capture showed the results footer clipped at the bottom; re-checked by scrolling a live 390 px viewport to the end — the footer renders completely, so this is a full-page-capture artefact, not a bug.
- `prefers-reduced-motion` is not honoured (Ken Burns hero, bouncing arrow, page fade, sunflower).

### 3.9 Design-token consistency

`:root` defines 6 tokens (`--green-story`, `--forest`, …) but the markup uses raw hex in ~60 places: `#173a2b`, `#24543e`, `#82c341`, `#93d450`, `#5a9e2e`, `#0f291e`, `#f2c46d`, `#f3f5ee`, `#f7f6f0`, `#12261c`, `#112a1e`, `#183829`, plus Tailwind slate/emerald/amber families. Two page backgrounds (`#f7f6f0` map/crops vs `#f3f5ee` results). Radii mix `rounded-xl/2xl/3xl` within the same card level. Font sizes include 7.5/9/10/11/11.5 px arbitrary values. Recommendation for tonight: no refactor; only add a `--forest-label` darker green and a `--muted` text token used by the contrast fixes, and keep the existing hexes.

## 4. Fixes ranked by impact / effort

| # | Fix | Impact | Effort | Phase 2 |
| --- | --- | --- | --- | --- |
| F2 | Contrast: information-gap label, Tier 1 label, model-id/disclaimer text, story badge, tile captions | High (honesty labels, AA) | XS | yes |
| F1 | Hero: one-line value proposition + primary "Draw your field →" CTA; keep "does not replace your judgement" | High (3-second test, PRD §10 step 1) | S | yes |
| F3 | Results: sticky jump bar (Deep A–D · Quick screen · Checklist), Evidence in `<details>` with count, Tier 1 heading "Quick Screen for your field" | High (mobile results 8,300 px) | S | yes |
| F4 | Touch targets ≥ 44 px (Undo/Clear, zoom, back buttons, checkboxes) | Medium | XS | yes |
| F5 | Map copy: "Tap" on touch devices + live "corner N of 4" hint; crops page: sticky Run bar on mobile | Medium | S | yes |
| F6 | P10–P90 consistency: single formatter, nowrap, "baseline" for A, chart legend point styles, backtest unit in chart caption | Medium (validity) | S | yes |
| F8 | Error states: plain-language 429 / network messages + Retry; `/fields-geo` retry | Medium | S | yes |
| F7 | Minimum 11.5–12 px for result ranges/labels | Medium | XS | yes |
| F9 | `prefers-reduced-motion`; `aria-pressed` on crop cards; focus-visible rings | Low–Medium (a11y) | XS | if time |
| F10 | Design tokens consolidation | Low tonight | M | no (documented only) |

All fixes keep the honesty labels (screening estimate, relative-index tooltip, P10–P90, possible range (scenario), S7, AI-image badges, "does not replace your judgement") and add no numbers.

## 5. Phase 2 — implemented (20:43–20:50 KST, branch `feat/ux-mobile`)

Applied to `frontend/` and mirrored into `docs/demo/` (the demo keeps its own snapshot API layer). No layout redesign; no numbers added; every honesty label kept.

| Fix | Status | Where |
| --- | --- | --- |
| F1 hero value line + "Draw your field →" CTA, "decision-support tool — does not replace your judgement. Free, no login." | done | `index.html` hero |
| F2 contrast (table below) | done | `app.js` GAP/labels, `index.html` badge/footer |
| F3 results jump nav (Strategies A–D · Quick Screen · Checklist), Evidence in `<details>` with count, Tier 1 heading "Quick Screen for your field" (engine name kept as subtitle) | done | `app.js` |
| F4 44 px targets: all page buttons, Undo/Clear, Leaflet zoom on coarse pointers, 20 px S7 checkboxes with 44 px label rows | done | `index.html` CSS |
| F5 "Tap" on touch devices, live "corner N of 4" hint on the map, sticky Selected/Run bar on phones, crop photos 112 px on phones | done | both |
| F6 one `P10–P90 a–b` notation (nowrap), A = "baseline", "days" unit, legend point styles, chart caption says backtest is one season and green = matches your crops | done | `app.js` |
| F7 result ranges/labels ≥ 12 px (`text-xs`); remaining 9–11 px nodes are photo badges, Leaflet attribution and the legend swatches | done | `app.js` |
| F8 plain-language 429 / network / upstream errors, raw detail kept, Retry button; pilot-outline load retry | done | `app.js` |
| F9 `prefers-reduced-motion`, `aria-pressed` on crop cards, `:focus-visible` ring, chart `role="img"` + label | done | both |
| New: `overflow-x: hidden` on `body` made it a scroll container, so `position: sticky` never stuck → `overflow-x: clip` (hidden kept as fallback) | done | `index.html` |
| New (static demo only): the fixed "static snapshot" banner covered "Next: choose crops" on phones (Playwright: banner intercepts pointer events) → banner flows at page top below `lg`, fixed bottom-left only on desktop | done | `docs/demo/app.js` |
| F10 design-token consolidation | not done (documented) | — |

Contrast after the fixes (`infra/web/ux/contrast.py`):

| Pair | Ratio | Result |
| --- | ---: | --- |
| slate-600 on white ("information gap", ranges) | 7.58:1 | PASS |
| slate-600 on #f3f5ee (Tier 1 tiles, footer) | 6.89:1 | PASS |
| slate-500 on white ("(assumption)", units) | 4.76:1 | PASS |
| #3d7a1f on white ("TIER 1 · QUICK SCREEN") | 5.25:1 | PASS |
| emerald-100/80 on white/10 over #173a2b (model id, disclaimer) | 5.91:1 | PASS |
| #102a1b on white/25 over #74b93d (story badge) | 8.03:1 | PASS |
| #0f291e on #82c341 (hero CTA) | 7.25:1 | PASS |

Verification before each commit (local server on this worktree, live model_api): `node --check` both `app.js`; `pytest model_api/tests/test_quick.py test_api_contract.py` → 23 passed; `mobile_check.py` at 360/390/1280 → document width = viewport, 4 touch taps → 4 vertices, Story preset → Quick + Deep, 0 page errors, no visible control under 44 px except the Leaflet attribution link (16 hits are Evidence links inside closed `<details>`, 7 are the 20 px checkboxes whose label rows are 44 px); `error_check.py` → mocked 429 shows the plain message + information gap + Retry, Retry then renders the real result; static demo (`docs/demo/?mode=static`) at 390/1280 plus `tools/test_static_demo.py` → 9/9 PASS, 0 page errors; → preset flow completes, banner does not overlap Run, 0 page errors. Sticky check at 390 px: Run bar bottom 832 px (viewport 844) on the crops page, jump nav top 0 after scrolling 3,000 px.

After screenshots: `docs/screens/mobile/after/` (`390-01-first-screen.jpg`, `390-04-map-touch-4.jpg`, `390-07-results-top.jpg`, `390-09-error-429.jpg`, `demo-390-crops.jpg`, …). The public tunnel still serves the deployed checkout; these fixes reach it only after merge and redeploy.

## 6. Reproduce

```bash
/srv/hackathon/venv/bin/python infra/web/ux/mobile_check.py "$(cat /srv/hackathon/state/status/demo_url.txt)" docs/screens/mobile 360,390,768
/srv/hackathon/venv/bin/python infra/web/ux/error_check.py <base-url> docs/screens/mobile   # mocked 429 → message + Retry
python3 infra/web/ux/contrast.py                                                              # table in §3.6
```

The mobile check hits the rate-limited API once per width (`/quick`, `/simulate`, `/field/{id}/profile`, `/validation/backtest`).
