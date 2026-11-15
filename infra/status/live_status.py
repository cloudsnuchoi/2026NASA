#!/usr/bin/env python3
"""Live team status for 아몰라 (NASA Space Apps 2026). Writes live.json + LIVE.md.

Every number comes from an automatic check (DB rows, files, API responses, GitHub issue/PR state,
tmux, Mattermost). Lane % = done items / all items. No guesses, no secrets.

Run on the VPS (user hackathon):  python3 -I live_status.py --out /srv/hackathon/state/status
Env: PG* for the fieldshift DB, MM_BOT_TOKEN_FILE (orchestrator .env path) for Mattermost reads,
API_URL (model_api, default http://127.0.0.1:8099).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

KST = dt.timezone(dt.timedelta(hours=9))
DEADLINE = dt.datetime(2026, 11, 15, 22, 0, tzinfo=KST)
REPO = "cloudsnuchoi/2026NASA"
API = os.environ.get("API_URL", "http://127.0.0.1:8090")
MM = os.environ.get("MM_URL", "http://127.0.0.1:8065")
ENV_FILE = os.environ.get("MM_BOT_TOKEN_FILE", "/srv/hackathon/projects/2026NASA/infra/orchestrator/.env")
MATLAB_DIR = Path(os.environ.get("FS_MATLAB_DIR", "/srv/hackathon/data/processed/v1/matlab"))
CACHE = Path(os.environ.get("STATUS_CACHE", "/srv/hackathon/state/status/cache.json"))
TUNNEL_LOG = Path("/srv/hackathon/db/mattermost/tunnel.log")
PEOPLE = [("김우찬", "woochan", "flyingbear-code"), ("김윤성", "yoonsung", "ssbb215356"), ("고지은", "jieun", "jieun-Ribby"),
          ("하지민", "jimin", "hahah383"), ("강다은", "daeun", "kangdaeun2005"), ("Hylē", "hyle", "cloudsnuchoi")]
TMUX_INFO = {  # what each lane is; model names are the ones the lanes were started with
    "imerg": ("claude-sonnet-5-5", "IMERG·NLDAS-2 카운티 적재"), "fields2": ("claude-opus-5-5", "대비 데모 필지 추가"),
    "site": ("claude-opus-5-5", "사이트 live 현황·내보내기·채팅 버튼"), "prithvi": ("claude-opus-5-5", "Prithvi 작물 분류 추론"),
    "bot": ("DeepSeek Flash + Codex sol/terra + Claude", "Mattermost 오케스트레이터 봇"), "api": ("—", "model_api 상시 실행 (:8090)"),
    "live": ("—", "이 현황 생성기 (5분)"), "nudge": ("DeepSeek Flash", "타임라인 독촉 봇"), "runner": ("—", "GitHub Actions 러너"),
    "mm-tunnel": ("—", "Mattermost Cloudflare 터널"), "keywatch": ("—", "SSH 공개키 자동 등록 (root)"),
    "qa": ("claude-opus-5-5", "QA·E2E"), "fix": ("claude-opus-5-5", "엔진 P1 수정"),
    "l1": ("claude-opus-5-5", "L1 프론트·/quick·배포"), "l2": ("codex gpt-6.1-sol", "L2 MATLAB 사전계산·검증"),
    "prd": ("claude-opus-5-5", "PRD 확정 문서"), "l4": ("claude-opus-5-5", "L4 제출물"), "l5": ("codex gpt-6.1-terra", "L5 공개 URL QA"),
    "web": ("—", "프론트+API 프록시 (:8095)"), "web-tunnel": ("—", "공개 데모 터널"),
}


def now() -> dt.datetime:
    return dt.datetime.now(KST)


def hm(ts: float | None) -> str | None:
    return dt.datetime.fromtimestamp(ts, KST).strftime("%H:%M") if ts else None


def sh(cmd: list[str], timeout: int = 20) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except Exception:
        return ""


def http_json(url: str, method: str = "GET", body: dict | None = None, headers: dict | None = None, timeout: int = 30):
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", "User-Agent": "amolla-status", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def sql(q: str) -> list[list[str]]:
    out = sh(["psql", "-At", "-F", "\t", "-c", q], timeout=60)
    return [line.split("\t") for line in out.splitlines() if line]


def scalar(q: str) -> int:
    try:
        return int(float(sql(q)[0][0] or 0))
    except Exception:
        return 0


def load_cache() -> dict:
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def cached(cache: dict, key: str, ttl: int, fn):
    hit = cache.get(key)
    if hit and time.time() - hit["t"] < ttl:
        return hit["v"]
    try:
        v = fn()
    except Exception as exc:
        v = {"error": type(exc).__name__}
    cache[key] = {"t": time.time(), "v": v}
    return v


def item(label: str, ok: bool, detail: str = "", blocked: bool = False) -> dict:
    return {"label": label, "status": "done" if ok else ("blocked" if blocked else "progress"), "detail": detail}


# --------------------------------------------------------------------------- checks
def gh(cache: dict) -> dict:
    def fetch():
        issues = http_json(f"https://api.github.com/repos/{REPO}/issues?state=all&per_page=100")
        prs = http_json(f"https://api.github.com/repos/{REPO}/pulls?state=closed&per_page=15&sort=updated&direction=desc")
        commits = http_json(f"https://api.github.com/repos/{REPO}/commits?per_page=60")
        runs = http_json(f"https://api.github.com/repos/{REPO}/actions/runs?branch=main&per_page=5")
        tree = http_json(f"https://api.github.com/repos/{REPO}/git/trees/main?recursive=1")
        return {
            "issues": {str(i["number"]): i["state"] for i in issues if "pull_request" not in i},
            "merged": [{"number": p["number"], "title": p["title"], "merged_at": p["merged_at"]} for p in prs if p.get("merged_at")][:8],
            "pr_auth": [{"user": p["user"]["login"], "at": p["updated_at"]} for p in prs],
            "commits": [{"login": (c.get("author") or {}).get("login"), "at": c["commit"]["author"]["date"]} for c in commits],
            "ci": [{"name": r["name"], "conclusion": r["conclusion"], "status": r["status"]} for r in runs.get("workflow_runs", [])],
            "paths": [t["path"] for t in tree.get("tree", [])],
        }
    return cached(cache, "github", 900, fetch)  # 60 req/h unauthenticated -> refresh every 15 min


def api_checks(cache: dict) -> dict:
    out: dict = {}
    try:
        out["health"] = http_json(f"{API}/health", timeout=10).get("status") == "ok"
        fields = http_json(f"{API}/fields", timeout=20)
        out["fields"] = fields.get("fields", [])
    except Exception as exc:
        out["health"], out["fields"], out["error"] = False, [], type(exc).__name__
        return out
    fid = out["fields"][0]["field_id"] if out["fields"] else None

    def heavy():
        r: dict = {}
        if not fid:
            return r
        prof = http_json(f"{API}/field/{fid}/profile")
        r["vision"] = prof.get("vision") or {}
        cmp_ = http_json(f"{API}/strategies/compare", "POST", {"field_id": fid}, timeout=60)
        strat = cmp_.get("strategies", [])
        r["mc_ok"] = bool(strat) and all(all(k in s for k in ("p10", "p50", "p90", "cvar")) for s in strat)
        r["p50"] = {s.get("strategy_code") or s.get("candidate_id"): s.get("p50") for s in strat}
        out_ = http_json(f"{API}/field/{fid}/climate/outlook")
        ns = out_.get("next_season") or {}
        r["s2s_members"] = ns.get("n_members")
        mc = out_.get("mid_century") or []
        r["nex_models"] = max([m.get("n_models") or 0 for m in mc] or [0])
        bt = http_json(f"{API}/validation/backtest?field_id={fid}&year=2012")
        defs = [((x.get("metrics") or {}).get("season_water_deficit_mm")) for x in bt.get("results", [])]
        r["backtest_distinct"] = len({d for d in defs if d is not None})
        spread = []
        for f in out["fields"][:24]:
            try:
                c = http_json(f"{API}/strategies/compare", "POST", {"field_id": f["field_id"]}, timeout=60)
                a = [s for s in c.get("strategies", []) if s.get("strategy_code") == "A"]
                if a:
                    spread.append(a[0].get("p50"))
            except Exception:
                pass
        r["a_p50_range"] = [min(spread), max(spread)] if spread else None
        return r
    out.update(cached(cache, "api_heavy", 600, heavy))

    def explain():
        t0 = time.time()
        e = http_json(f"{API}/explain", "POST", {"field_id": fid, "question": "What is the main water risk for this field?"}, timeout=90)
        return {"ok": bool(e.get("answer")), "secs": round(time.time() - t0, 1), "model": e.get("model")}
    out["explain"] = cached(cache, "explain", 3600, explain) if fid else {"ok": False}
    return out


def mm_activity(cache: dict) -> dict:
    def fetch():
        tok = [ln.split("=", 1)[1].strip() for ln in open(ENV_FILE) if ln.startswith("MM_BOT_TOKEN=")][-1]
        hdr = {"Authorization": "Bearer " + tok}
        me = http_json(f"{MM}/api/v4/users/me", headers=hdr)
        team = http_json(f"{MM}/api/v4/teams/name/amolla", headers=hdr)
        users = {u["id"]: u["username"] for u in http_json(f"{MM}/api/v4/users?per_page=200", headers=hdr)}
        since = int((time.time() - 24 * 3600) * 1000)
        last: dict = {}
        for ch in http_json(f"{MM}/api/v4/users/me/teams/{team['id']}/channels", headers=hdr):
            if ch.get("last_post_at", 0) < since:
                continue
            for p in http_json(f"{MM}/api/v4/channels/{ch['id']}/posts?since={since}", headers=hdr).get("posts", {}).values():
                if p.get("type") or p["user_id"] == me["id"]:
                    continue
                u = users.get(p["user_id"], "")
                last[u] = max(last.get(u, 0), p["create_at"] / 1000)
        return last
    return cached(cache, "mm", 240, fetch)


def tmux_sessions() -> list[dict]:
    out = []
    for line in sh(["tmux", "list-sessions", "-F", "#{session_name}\t#{session_activity}"]).splitlines():
        name, act = (line.split("\t") + ["0"])[:2]
        model, task = TMUX_INFO.get(name, ("?", "?"))
        out.append({"name": name, "model": model, "task": task, "last_activity": hm(float(act or 0))})
    return out


def public_checks(base: str) -> dict:
    """Hit the public demo through the tunnel/proxy (same path a judge uses)."""
    def code(path, body=None):
        try:
            req = urllib.request.Request(base + path, method="POST" if body is not None else "GET",
                                         data=json.dumps(body).encode() if body is not None else None,
                                         headers={"Content-Type": "application/json", "User-Agent": "amolla-status"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code
        except Exception:
            return None
    out = {"home": code("/"), "fields": code("/api/fields")}
    poly = [[-93.6375, 42.0308], [-93.6319, 42.0353], [-93.6263, 42.0308], [-93.6319, 42.0263]]
    out["quick"] = code("/api/quick", {"polygon": poly, "crops": ["corn", "soybean"]})
    try:
        f = json.loads(urllib.request.urlopen(urllib.request.Request(base + "/api/fields", headers={"User-Agent": "amolla-status"}),
                                              timeout=30).read())["fields"][0]["field_id"]
        out["compare"] = code("/api/strategies/compare", {"field_id": f})
    except Exception:
        out["compare"] = None
    return out


MATLAB_PEOPLE = [
    ("woochan", "matlab-hyle", ("v8_cards_20fields.csv", "coefficients_sources.csv")),
    ("yoonsung", "matlab-2", ("drought_compare_2012.png", "drought_compare_2012_summary.csv")),
    ("jimin", "matlab-3", ("baresoil_days_20fields.csv",)),
    ("jieun", "matlab-4", ("fig_p10p90.png", "fig_backtest2012.png")),
]


def matlab_connected(user: str, container: str) -> bool:
    """Connected = an SSH tunnel session for the user now, or a MATLAB process running in their container
    (MATLAB only starts after the person's own MathWorks sign-in). No secrets read."""
    if any(line.split()[0] == user for line in sh(["ps", "-eo", "user,cmd"]).splitlines()[1:] if "sshd" in line and line.split()):
        return True
    return bool(sh(["docker", "exec", container, "pgrep", "-f", "MATLAB"], timeout=10).strip())


def demo_url() -> str | None:
    p = Path("/srv/hackathon/state/status/demo_url.txt")
    try:
        u = p.read_text(encoding="utf-8").strip()
        return u if u.startswith("https://") else None
    except OSError:
        return None


def lane_done(name: str) -> bool:
    p = Path(f"/srv/hackathon/logs/{name}-lane.jsonl")
    return p.exists() and f"{name.upper()}-LANE-DONE" in p.read_text(errors="replace")[-20000:]


# --------------------------------------------------------------------------- build
def build() -> dict:
    cache = load_cache()
    g = gh(cache)
    demo = demo_url()
    pub = cached(cache, "public", 300, lambda: public_checks(demo)) if demo else {}
    a = api_checks(cache)
    issues = g.get("issues", {}) if isinstance(g, dict) else {}
    paths = set(g.get("paths", [])) if isinstance(g, dict) else set()
    closed = lambda n: issues.get(str(n)) == "closed"  # noqa: E731

    imerg_years = scalar("select count(distinct extract(year from date)) from county_imerg_daily")
    counties = len({f.get("county_fips") for f in a.get("fields", [])})
    data = [
        item("POWER 일별 12주 1995–2025", scalar("select count(*) from county_weather_daily") > 10_000_000),
        item("CDL 카운티 작물 비율", scalar("select count(*) from county_crop_share") > 0),
        item("CSB 필지 경계", scalar("select count(*) from fields") > 0),
        item("SSURGO 필지 토양", scalar("select count(*) from field_soil") > 0),
        item("HLS NDVI 데모 필지", scalar("select count(*) from field_ndvi_hls") > 0),
        item("SMAP L3 (맥락)", scalar("select count(*) from county_smap") > 0),
        item("NLDAS-2 월별", scalar("select count(*) from county_nldas_monthly") > 0),
        item("IMERG 일별 2010–2025 (16개 연도)", imerg_years >= 16, f"{imerg_years}개 연도 적재"),
        item("NEX-GDDP 2개 모델 이상 (API)", (a.get("nex_models") or 0) >= 2, f"{a.get('nex_models')}개 모델"),
        item("GEOS-S2S 다음 시즌 (API)", bool(a.get("s2s_members")), f"멤버 {a.get('s2s_members')}"),
        item("대비 데모 필지 (3개 카운티 이상)", counties >= 3, f"데모 필지 {len(a.get('fields', []))}개, {counties}개 카운티"),
    ]
    vision = a.get("vision") or {}
    engine = [
        item("model_api 상시 실행", bool(a.get("health")), a.get("error", "")),
        item("Story 데모 필지 목록 /fields", bool(a.get("fields"))),
        item("전략 비교 MC·CVaR", bool(a.get("mc_ok"))),
        item("2012 백테스트 전략별 차이", (a.get("backtest_distinct") or 0) >= 3, f"서로 다른 물 부족 값 {a.get('backtest_distinct')}개"),
        item("필지별 결과 차이 (A P50 범위 > 0.02)",
             bool(a.get("a_p50_range")) and (a["a_p50_range"][1] - a["a_p50_range"][0]) > 0.02, f"A P50 범위 {a.get('a_p50_range')}"),
        item("공개 데모 배포", pub.get("home") == 200, f"{demo or '데모 URL 없음'}"),
    ]
    ex = a.get("explain") or {}
    ai = [
        {"name": "Prithvi 작물 분류", "status": "done" if vision.get("crop_pred") else "progress",
         "detail": f"crop_pred={vision.get('crop_pred')}, agreement_with_cdl={vision.get('agreement_with_cdl')}"},
        {"name": "GEOS-S2S 다음 시즌 분포", "status": "done" if a.get("s2s_members") else "progress", "detail": f"앙상블 멤버 {a.get('s2s_members')}"},
        {"name": "NEX-GDDP 2030년대", "status": "done" if (a.get("nex_models") or 0) >= 2 else "progress", "detail": f"모델 {a.get('nex_models')}개"},
        {"name": "Monte Carlo·CVaR", "status": "done" if a.get("mc_ok") else "progress", "detail": f"전략별 P50 {a.get('p50')}"},
        {"name": "/explain (DeepSeek)", "status": "done" if ex.get("ok") else "progress", "detail": f"{ex.get('secs')} s, {ex.get('model')}"},
    ]
    ai_items = [item(x["name"], x["status"] == "done", x["detail"]) for x in ai]
    mfiles = {p.name for p in MATLAB_DIR.glob("*.csv")} if MATLAB_DIR.exists() else set()
    matlab = [item(f"윤성 1차 CSV: {f}", f in mfiles) for f in ("drought_2012_county.csv", "climate_annual.csv", "calibration_params.csv")]
    for who, cont, outs in MATLAB_PEOPLE:
        have = all((MATLAB_DIR / "outputs" / who / o).exists() for o in outs)
        if have:
            stage, ok = "✅ 결과 파일 있음", True
        elif matlab_connected(who, cont):
            stage, ok = "🟡 접속함·작업 중", False
        else:
            stage, ok = "🔑 접속 전", False
        matlab.append(item(f"{who}: " + " + ".join(outs), ok, stage))
    ui = [
        item("frontend/ 코드 (main)", "frontend/index.html" in paths),
        item("공개 데모 접속 200 (로그인 없음)", pub.get("home") == 200, f"{demo or '데모 URL 없음'}"),
        item("공개 API /fields (20필지)", pub.get("fields") == 200),
        item("1층 /quick (screening estimate)", pub.get("quick") == 200, f"HTTP {pub.get('quick')}"),
        item("2층 전략 비교 /strategies/compare", pub.get("compare") == 200, f"HTTP {pub.get('compare')}"),
        item("화면 캡처 docs/screens", any(p_.startswith("docs/screens/") for p_ in paths)),
        item("공개 URL QA (docs/QA-FINAL.md)", "docs/QA-FINAL.md" in paths),
    ]
    sim = [item("sim/ 코드", any(p.startswith("sim/") and not p.endswith(".gitkeep") for p in paths)), item("복셀 시뮬 (#30)", closed(30))]
    tmux = tmux_sessions()
    names = {t["name"] for t in tmux}
    mm_ok = False
    try:
        mm_ok = http_json(f"{MM}/api/v4/system/ping", timeout=5).get("status") == "OK"
    except Exception:
        pass
    ci = g.get("ci", []) if isinstance(g, dict) else []
    infra = [
        item("Mattermost", mm_ok), item("봇 (tmux bot)", "bot" in names), item("러너 (tmux runner)", "runner" in names),
        item("SSH 공개키 자동 등록 (keywatch)", bool(sh(["pgrep", "-f", "hackathon-keywatch.py"]).strip()), "root 프로세스로 확인"),
        item("main CI 최근 성공", bool(ci) and ci[0].get("conclusion") == "success", ci[0]["conclusion"] if ci else "기록 없음"),
        item("live 현황 (tmux live)", "live" in names),
    ]
    lanes = [("data", "데이터", data), ("engine", "엔진·API", engine), ("ai", "AI 모델", ai_items), ("matlab", "MATLAB", matlab),
             ("ui", "UI", ui), ("infra", "인프라·봇", infra)]  # 시뮬 = Stretch (19:30 링크 없음), 진행률 계산에서 제외
    lanes_out = [{"id": i, "name": n, "pct": round(100 * sum(x["status"] == "done" for x in its) / len(its)), "items": its} for i, n, its in lanes]

    mm = mm_activity(cache)
    commits = g.get("commits", []) if isinstance(g, dict) else []
    people = []
    for name, user, login in PEOPLE:
        rl = max([c["at"] for c in commits if c.get("login") == login] + [p["at"] for p in g.get("pr_auth", []) if p["user"] == login] or [None],
                 key=lambda x: x or "")
        people.append({"name": name, "user": user, "mattermost_last": hm(mm.get(user)) if isinstance(mm, dict) else None,
                       "repo_last": dt.datetime.fromisoformat(rl.replace("Z", "+00:00")).astimezone(KST).strftime("%H:%M") if rl else None})
    blockers = [f"{ln['name']}: {x['label']}" + (f" ({x['detail']})" if x["detail"] else "")
                for ln in lanes_out for x in ln["items"] if x["status"] == "blocked"]
    extra = Path("/srv/hackathon/state/status/blockers.txt")
    if extra.exists():
        blockers += [b.strip() for b in extra.read_text(encoding="utf-8").splitlines() if b.strip()]
    order = ["matlab", "ui", "engine", "ai", "data", "sim", "infra"]
    nxt = [f"{ln['name']}: {x['label']}" for o in order for ln in lanes_out if ln["id"] == o for x in ln["items"] if x["status"] != "done"][:3]
    chat = None
    try:
        import re
        urls = re.findall(r"https://[a-z0-9-]+\.trycloudflare\.com", TUNNEL_LOG.read_text(errors="replace"))
        chat = urls[-1] + "/" if urls else None
    except Exception:
        pass
    t = now()
    data_out = {
        "generated_at": t.isoformat(timespec="seconds"), "deadline": DEADLINE.isoformat(), "remaining_min": max(0, int((DEADLINE - t).total_seconds() // 60)),
        "chat_url": chat, "demo_url": demo_url(), "lanes": lanes_out, "tmux": tmux, "people": people, "blockers": blockers, "next": nxt,
        "merged_prs": g.get("merged", []) if isinstance(g, dict) else [], "ai_models": ai,
        "stretch": [{"name": "복셀 시뮬 (다은)", "status": "stretch",
                     "detail": "19:30까지 공개 링크 없음 → Stretch, 진행률 계산 제외" if not sim[0]["status"] == "done" else "sim/ 코드 있음"}],
        "lane_agents_done": {n: lane_done(n) for n in ("l1", "l2", "prd", "l4", "l5")},
    }
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache), encoding="utf-8")
    return data_out


def to_md(d: dict) -> str:
    icon = {"done": "✅", "progress": "🟡", "blocked": "🔴"}
    L = [f"# 아몰라 실시간 현황 · {d['generated_at'][11:16]} KST", "",
         f"제출 목표 22:00 KST까지 **{d['remaining_min'] // 60}시간 {d['remaining_min'] % 60}분** 남음. 팀 채팅: {d.get('chat_url') or '—'}", "",
         "| 레인 | 진행 | 완료/전체 |", "| --- | --- | --- |"]
    for ln in d["lanes"]:
        done = sum(x["status"] == "done" for x in ln["items"])
        L.append(f"| {ln['name']} | {ln['pct']}% | {done}/{len(ln['items'])} |")
    for ln in d["lanes"]:
        L += ["", f"## {ln['name']} {ln['pct']}%"] + [f"- {icon[x['status']]} {x['label']}" + (f" — {x['detail']}" if x["detail"] else "") for x in ln["items"]]
    L += ["", "## 막힌 점"] + ([f"- {b}" for b in d["blockers"]] or ["- 없음"])
    L += ["", "## 다음 할 일"] + [f"{i}. {n}" for i, n in enumerate(d["next"], 1)]
    L += ["", "## AI 모델"] + [f"- {icon.get(m['status'], '🟡')} {m['name']} — {m['detail']}" for m in d["ai_models"]]
    L += ["", "## 에이전트 레인 (tmux)", "| 세션 | 모델 | 하는 일 | 마지막 활동 |", "| --- | --- | --- | --- |"]
    L += [f"| {t['name']} | {t['model']} | {t['task']} | {t['last_activity']} |" for t in d["tmux"]]
    L += ["", "## 사람 (마지막 활동, KST)", "| 이름 | Mattermost | 레포 |", "| --- | --- | --- |"]
    L += [f"| {p['name']} | {p['mattermost_last'] or '—'} | {p['repo_last'] or '—'} |" for p in d["people"]]
    L += ["", "## 최근 머지된 PR"] + [f"- #{p['number']} {p['title']}" for p in d["merged_prs"]]
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/srv/hackathon/state/status")
    a = ap.parse_args()
    d = build()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "live.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "LIVE.md").write_text(to_md(d), encoding="utf-8")
    print(f"live {d['generated_at']} " + " ".join(f"{ln['id']}={ln['pct']}" for ln in d["lanes"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
