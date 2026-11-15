"""Chunked ranged download (server returns empty body for plain GET on NASS CDL zips, but Range works)."""

import requests
import os
from concurrent.futures import ThreadPoolExecutor


def rangedl(url, out, chunk=64 << 20, workers=4):
    if os.path.exists(out):
        return out
    n = int(requests.head(url, allow_redirects=True, timeout=60).headers["content-length"])

    def get(i):
        s = i * chunk
        e = min(n - 1, s + chunk - 1)
        for a in range(6):
            try:
                r = requests.get(url, headers={"Range": f"bytes={s}-{e}"}, timeout=180)
                if r.status_code == 206 and len(r.content) == e - s + 1:
                    return i, r.content
            except Exception:
                pass
        raise RuntimeError(f"chunk {i} failed")

    with open(out + ".part", "wb") as f:
        f.truncate(n)
        with ThreadPoolExecutor(workers) as ex:
            for i, b in ex.map(get, range((n + chunk - 1) // chunk)):
                f.seek(i * chunk)
                f.write(b)
    os.rename(out + ".part", out)
    return out
