# ART FARM — 30-second demo recording sequence

Owner: 강다은 (demo video). Voice-over text is in [video-script.md](video-script.md); this file is the click-by-click recording plan. Every screen below exists in the build. The UX lane's screenshots in `docs/screens/mobile/after/` show the same screens (2026-11-15).

## Setup (before pressing record)

- URL: live server `https://watts-astrology-asus-blessed.trycloudflare.com` (Tier 2 cards need the model API). Fallback if the tunnel is down: static snapshot `https://cloudsnuchoi.github.io/2026NASA/demo/`.
- Browser window 1280 × 720 (desktop) **or** device emulation 390 × 844 (phone). Pick one and keep it for the whole take.
- Hard-refresh once, then load the flow one time without recording so NASA POWER responses are cached. Results then appear without a long wait.
- Hide bookmarks, other tabs and notifications. Do not show the team chat, keys or terminal.

## Sequence (≈30 s)

| Time | Action | What must be visible |
| --- | --- | --- |
| 0–3 s | First screen, hold still | "ART FARM — Field Shift: Adapting Farms with NASA Data", data-source strip (NASA POWER · USGS 3DEP · …), "does not replace your judgement" |
| 3–5 s | Click **Draw your field →** | Step 1 map with Esri attribution |
| 5–10 s | Click preset **Story, IA**, or tap 4 corners on a Story County field | 4 numbered corners, "4 corners placed — Next: choose crops" |
| 10–13 s | Step 2: tick **Corn** and **Soybean**, click **Run screening →** | "unranked — the choice stays yours"; the "AI-generated image" marks on the crop photos |
| 13–15 s | Loading screen (do not cut) | Progress state |
| 15–21 s | Results top: Tier 2 Deep Analysis header | "screening estimate", "FAO-56 engine (ported from team MATLAB prototype V8)", Monte Carlo n = 500 / seed, CVaR definition |
| 21–26 s | Open **Strategies A–D**, scroll slowly through one card | P10–P90 bar, "2012 drought backtest", information-gap and local-review lines |
| 26–30 s | Scroll to the checklist or footer, hold 2 s | "does not replace your judgement" text; end on the ART FARM title or the slides URL |

## Do not show

- The word "Recommended" or any ranking. If a screen shows one, stop and report it to Hylē; do not record around it.
- Numbers that are not on screen in the build: do not add on-video captions with extra figures.
- NASA logos, flags or mission insignia; any terminal, `.env` or key file.
- The 3D field simulation (planned, not built).

## After recording

- Length ≤ 30 s; export MP4 1080p or 720p.
- Upload where the form asks, then paste the link into `submission-form.md` (TODO(Hylē) line at the top).
- Record in `docs/si-log.md` only if an SI tool was used to edit the video (none planned).
