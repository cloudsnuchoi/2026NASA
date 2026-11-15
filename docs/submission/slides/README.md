# ART FARM slides

`index.html` is a self-contained 7-slide deck (no external fonts, scripts or images; 1280×720 px per slide). Open it in any browser to present (scroll between slides).

## Export to PDF

**Browser (any machine):** open `index.html` in Chrome or Edge → Print (Ctrl/Cmd+P) → Destination "Save as PDF" → Margins "None" → enable "Background graphics" → Save. The page size comes from the CSS `@page { size: 1280px 720px }`, one slide per page.

**Headless (VPS, Playwright already installed in `/srv/hackathon/venv`):**

```bash
cd docs/submission/slides
/srv/hackathon/venv/bin/python - <<'PY'
from playwright.sync_api import sync_playwright
import pathlib
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    pg.goto(pathlib.Path("index.html").resolve().as_uri())
    pg.pdf(path="artfarm-slides.pdf", width="1280px", height="720px", print_background=True)
    b.close()
PY
```

Tested 2026-11-15: 7 pages, no slide overflow. Do not commit the PDF if the submission form takes an upload; attach it directly.

## Notes

- All numbers on slide 5 come from the live model API; sources are in the comment block at the end of `../submission.md`.
- MATLAB figures: `/srv/hackathon/data/processed/v1/matlab/outputs/jieun/*.png` did not exist at 20:00 KST, so no MATLAB figures are included. If they appear, add them to slide 4 or 5 as base64 `<img>` so the file stays self-contained.
- Team slide: the role of 강다은 is marked "to confirm" in AGENTS.md; check before final export.
- No NASA logos, flags or mission insignia.
