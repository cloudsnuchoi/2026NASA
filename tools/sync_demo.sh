#!/usr/bin/env bash
# Regenerate the static GitHub Pages copy (docs/demo) from frontend/ (RESTORE lane, 2026-11-15).
# Same app.js/index.html; docs/demo sets window.ARTFARM_STATIC=true → snapshot JSON only (no cross-origin API call).
# Snapshot data itself: python3 tools/make_demo_snapshot.py (unchanged).
set -euo pipefail
cd "$(dirname "$0")/.."
cp frontend/app.js frontend/data-sources.js docs/demo/
cp -r frontend/assets/. docs/demo/assets/
sed 's#<script src="app.js"></script>#<script>window.ARTFARM_STATIC = true;</script>\n<script src="app.js"></script>#' frontend/index.html > docs/demo/index.html
grep -q 'ARTFARM_STATIC = true' docs/demo/index.html
echo "docs/demo synced"
