"""Stage MAT2 scripts while preserving any teammate edits (no network)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from data_pipeline.matlab_export import ROOT

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = {
    "yoonsung": ("yoonsung_nldas_2012.m", "yoonsung_season_anomaly.m", "yoonsung_s2s_box.m"),
    "jimin": ("jimin_growing_season.m", "jimin_ndvi_anomaly.m", "jimin_bare_vs_rye.m"),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stage(root=ROOT, repo=REPO):
    # Preflight the complete batch before placing anything. Unknown differing
    # files are human-owned; a checksum ledger never authorizes overwriting them.
    batches = []
    for user, names in SCRIPTS.items():
        folder = root / "work" / user
        ledger = folder / ".agent_sha.json"
        hashes = json.loads(ledger.read_text()) if ledger.exists() else {}
        for name in names:
            source, target = repo / "matlab" / name, folder / name
            digest = sha(source)
            if target.exists() and sha(target) not in (digest, hashes.get(name)):
                raise FileExistsError(f"Teammate modification preserved: {target}")
        batches.append((folder, ledger, hashes, names))
    for folder, ledger, hashes, names in batches:
        folder.mkdir(parents=True, exist_ok=True)
        for name in names:
            source, target = repo / "matlab" / name, folder / name
            target.write_bytes(source.read_bytes())
            target.chmod(0o644)
            hashes[name] = sha(target)
        temporary = ledger.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(hashes, indent=2) + "\n")
        temporary.replace(ledger)
        print(f"Staged {len(names)} scripts in {folder}; checksum ledger updated")


if __name__ == "__main__":
    stage()
