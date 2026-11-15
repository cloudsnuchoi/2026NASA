/* Field Shift status dashboard — plain JS, no build. */
(function () {
  "use strict";

  const OWNER = "cloudsnuchoi";
  const REPO = "2026NASA";
  const API = "https://api.github.com";
  const CACHE_KEY = "fieldshift-dash-v1";
  const REFRESH_MS = 2 * 60 * 1000;
  const DEADLINE = new Date("2026-11-15T23:59:00+09:00");
  const ARCH_URLS = [
    "../ARCHITECTURE.md",
    "https://raw.githubusercontent.com/cloudsnuchoi/2026NASA/main/docs/ARCHITECTURE.md",
  ];

  const TIME_BLOCKS = [
    { id: "freeze", label: "08:00–10:00 동결", start: "2026-11-15T08:00:00+09:00", end: "2026-11-15T10:00:00+09:00" },
    { id: "data", label: "08:00–11:00 데이터·EDA", start: "2026-11-15T08:00:00+09:00", end: "2026-11-15T11:00:00+09:00" },
    { id: "build", label: "11:00–18:00 병렬 구축", start: "2026-11-15T11:00:00+09:00", end: "2026-11-15T18:00:00+09:00" },
    { id: "e2e", label: "18:00–20:00 기능 동결·E2E", start: "2026-11-15T18:00:00+09:00", end: "2026-11-15T20:00:00+09:00" },
    { id: "submit", label: "20:00–23:30 제출물", start: "2026-11-15T20:00:00+09:00", end: "2026-11-15T23:30:00+09:00" },
    { id: "upload", label: "23:30–23:55 업로드", start: "2026-11-15T23:30:00+09:00", end: "2026-11-15T23:55:00+09:00" },
    { id: "deadline", label: "23:59 마감", start: "2026-11-15T23:55:00+09:00", end: "2026-11-15T23:59:00+09:00" },
  ];

  const AREAS = [
    { key: "area: data", label: "data" },
    { key: "area: model", label: "model" },
    { key: "area: frontend", label: "frontend" },
    { key: "area: matlab", label: "matlab" },
    { key: "area: rag", label: "rag" },
    { key: "area: sim", label: "sim" },
    { key: "area: infra", label: "infra" },
    { key: "area: docs", label: "docs" },
    { key: "area: pitch", label: "pitch" },
  ];

  const MEMBERS = [
    { id: "hyle", name: "Hylē", patterns: [/hyl[eē]/i, /하일리/] },
    { id: "yoonsung", name: "김윤성", patterns: [/김윤성/, /윤성/] },
    { id: "woochan", name: "김우찬", patterns: [/김우찬/, /우찬/] },
    { id: "jieun", name: "고지은", patterns: [/고지은/, /지은/] },
    { id: "jimin", name: "하지민", patterns: [/하지민/, /지민/] },
    { id: "daeun", name: "강다은", patterns: [/강다은/, /다은/] },
  ];

  const $ = (id) => document.getElementById(id);
  const banner = $("banner");

  function setBanner(msg, kind) {
    banner.textContent = msg || "";
    banner.className = "banner" + (kind ? " " + kind : "");
    banner.hidden = !msg;
  }

  function pad(n) { return String(n).padStart(2, "0"); }

  function fmtKST(d) {
    const parts = new Intl.DateTimeFormat("sv-SE", {
      timeZone: "Asia/Seoul",
      year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", second: "2-digit",
      hour12: false,
    }).format(d);
    return parts.replace(" ", " ") + " Asia/Seoul (KST)";
  }

  function tickCountdown() {
    const now = new Date();
    const ms = DEADLINE - now;
    const el = $("countdown-time");
    const box = $("countdown");
    $("now-kst").textContent = fmtKST(now);
    if (ms <= 0) {
      el.textContent = "마감";
      box.classList.add("over");
    } else {
      const h = Math.floor(ms / 3600000);
      const m = Math.floor((ms % 3600000) / 60000);
      const s = Math.floor((ms % 60000) / 1000);
      el.textContent = h + ":" + pad(m) + ":" + pad(s);
      box.classList.toggle("over", h < 2);
    }
    renderBlocks(now);
  }

  function renderBlocks(now) {
    const root = $("time-blocks");
    root.innerHTML = "";
    let currentId = null;
    TIME_BLOCKS.forEach(function (b) {
      const start = new Date(b.start);
      const end = new Date(b.end);
      const div = document.createElement("div");
      div.className = "block";
      if (now >= start && now < end) {
        div.classList.add("current");
        currentId = b.id;
      } else if (now >= end) {
        div.classList.add("past");
      }
      div.textContent = b.label;
      root.appendChild(div);
    });
    const cur = TIME_BLOCKS.find(function (b) { return b.id === currentId; });
    $("current-block").textContent = cur
      ? ("현재 체크리스트 구간: " + cur.label)
      : (now < new Date(TIME_BLOCKS[0].start)
        ? "현재 체크리스트 구간: 아직 동결 창 전"
        : "현재 체크리스트 구간: 마감 이후");
  }

  function loadCache() {
    try {
      const raw = localStorage.getItem(CACHE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  function saveCache(data) {
    try {
      localStorage.setItem(CACHE_KEY, JSON.stringify(data));
    } catch (e) { /* quota */ }
  }

  function parseLinkNext(header) {
    if (!header) return null;
    const parts = header.split(",");
    for (let i = 0; i < parts.length; i++) {
      const m = parts[i].match(/<([^>]+)>;\s*rel="next"/);
      if (m) return m[1];
    }
    return null;
  }

  function rateFrom(res) {
    return {
      remaining: res.headers.get("X-RateLimit-Remaining"),
      limit: res.headers.get("X-RateLimit-Limit"),
      reset: res.headers.get("X-RateLimit-Reset"),
    };
  }

  async function fetchJson(url) {
    const res = await fetch(url, {
      headers: { Accept: "application/vnd.github+json" },
    });
    const rate = rateFrom(res);
    if (res.status === 403 || res.status === 429) {
      const err = new Error("rate_limited");
      err.rate = rate;
      err.status = res.status;
      throw err;
    }
    if (!res.ok) {
      const err = new Error("http_" + res.status);
      err.status = res.status;
      err.rate = rate;
      throw err;
    }
    const data = await res.json();
    return { data: data, rate: rate, link: res.headers.get("Link") };
  }

  async function fetchAll(url) {
    let acc = [];
    let next = url;
    let rate = null;
    let guard = 0;
    while (next && guard < 8) {
      const page = await fetchJson(next);
      acc = acc.concat(page.data);
      rate = page.rate;
      next = parseLinkNext(page.link);
      guard += 1;
    }
    return { data: acc, rate: rate };
  }

  async function loadGithub() {
    const issuesUrl = API + "/repos/" + OWNER + "/" + REPO + "/issues?state=all&per_page=100";
    const pullsUrl = API + "/repos/" + OWNER + "/" + REPO + "/pulls?state=all&per_page=100";
    const commitsUrl = API + "/repos/" + OWNER + "/" + REPO + "/commits?per_page=15";
    const [issues, pulls, commits] = await Promise.all([
      fetchAll(issuesUrl),
      fetchAll(pullsUrl),
      fetchJson(commitsUrl),
    ]);
    return {
      fetchedAt: Date.now(),
      issues: issues.data,
      pulls: pulls.data,
      commits: commits.data,
      rate: commits.rate || pulls.rate || issues.rate,
    };
  }

  function isIssue(item) {
    return !item.pull_request;
  }

  function labelsOf(item) {
    return (item.labels || []).map(function (l) { return l.name; });
  }

  function ownerSection(body) {
    if (!body) return "";
    const m = body.match(/##\s*제안 담당\s*\n([\s\S]*?)(?=\n##\s|$)/);
    return m ? m[1].trim() : "";
  }

  function ownersOf(item) {
    const text = ownerSection(item.body);
    if (!text) return [];
    const found = [];
    MEMBERS.forEach(function (mem) {
      if (mem.patterns.some(function (re) { return re.test(text); })) {
        found.push(mem);
      }
    });
    return found;
  }

  function pct(n, d) {
    if (!d) return 0;
    return Math.round((100 * n) / d);
  }

  function renderStats(data) {
    const issues = (data.issues || []).filter(isIssue);
    const openI = issues.filter(function (i) { return i.state === "open"; });
    const closedI = issues.filter(function (i) { return i.state === "closed"; });
    const pulls = data.pulls || [];
    const openP = pulls.filter(function (p) { return p.state === "open"; });
    const merged = pulls.filter(function (p) { return p.merged_at; });
    $("stats").innerHTML =
      stat("열린 이슈", openI.length) +
      stat("닫힌 이슈", closedI.length) +
      stat("전체 진행", pct(closedI.length, issues.length) + "%") +
      stat("열린 PR", openP.length) +
      stat("머지된 PR", merged.length) +
      stat("최근 커밋", (data.commits || []).length + "건 표시");
  }

  function stat(label, value) {
    return '<div class="stat"><div class="n">' + escapeHtml(String(value)) + '</div><div class="l">' + escapeHtml(label) + "</div></div>";
  }

  function renderAreas(data) {
    const issues = (data.issues || []).filter(isIssue);
    $("areas").innerHTML = AREAS.map(function (area) {
      const mine = issues.filter(function (i) { return labelsOf(i).indexOf(area.key) !== -1; });
      const closed = mine.filter(function (i) { return i.state === "closed"; }).length;
      const p0open = mine.filter(function (i) {
        return i.state === "open" && labelsOf(i).indexOf("priority: P0") !== -1;
      }).length;
      const p = pct(closed, mine.length);
      return (
        '<div class="area"><header><strong>' +
        escapeHtml(area.label) +
        "</strong><span class=\"muted\">" +
        closed + "/" + mine.length + " · " + p + "%" +
        (p0open ? " · P0 열림 " + p0open : "") +
        "</span></header><div class=\"bar\"><span style=\"width:" + p + '%"></span></div></div>'
      );
    }).join("");
  }

  function renderMembers(data) {
    const issues = (data.issues || []).filter(isIssue);
    $("members").innerHTML = MEMBERS.map(function (mem) {
      const mine = issues.filter(function (i) {
        return ownersOf(i).some(function (o) { return o.id === mem.id; });
      });
      const open = mine.filter(function (i) { return i.state === "open"; });
      const closed = mine.length - open.length;
      const p = pct(closed, mine.length);
      const titles = open.slice(0, 3).map(function (i) {
        return '<div class="muted">#' + i.number + " " + escapeHtml(i.title) + "</div>";
      }).join("");
      return (
        '<div class="member"><header><strong>' +
        escapeHtml(mem.name) +
        "</strong><span class=\"muted\">" +
        closed + "/" + mine.length + " · " + p + "%</span></header>" +
        '<div class="bar"><span style="width:' + p + '%"></span></div>' +
        (titles || '<div class="muted">열린 이슈 없음</div>') +
        "</div>"
      );
    }).join("");
  }

  function priClass(item) {
    const ls = labelsOf(item);
    if (ls.indexOf("priority: P0") !== -1) return "p0";
    if (ls.indexOf("priority: P1") !== -1) return "p1";
    return "";
  }

  function areaTags(item) {
    return labelsOf(item)
      .filter(function (n) { return n.indexOf("area:") === 0 || n.indexOf("priority:") === 0; })
      .map(function (n) {
        const cls = n === "priority: P0" ? "p0" : n === "priority: P1" ? "p1" : "";
        return '<span class="tag ' + cls + '">' + escapeHtml(n) + "</span>";
      })
      .join(" ");
  }

  function renderIssues(data) {
    const issues = (data.issues || []).filter(isIssue).slice().sort(function (a, b) {
      const ao = a.state === "open" ? 0 : 1;
      const bo = b.state === "open" ? 0 : 1;
      if (ao !== bo) return ao - bo;
      const ap = priClass(a) === "p0" ? 0 : priClass(a) === "p1" ? 1 : 2;
      const bp = priClass(b) === "p0" ? 0 : priClass(b) === "p1" ? 1 : 2;
      if (ap !== bp) return ap - bp;
      return b.number - a.number;
    });
    const rows = issues.map(function (i) {
      const owners = ownersOf(i).map(function (o) { return o.name; }).join(" · ") || "미지정";
      const st = i.state === "open" ? '<span class="tag open">open</span>' : '<span class="tag closed">closed</span>';
      return (
        "<tr><td><a href=\"" + escapeHtml(i.html_url) + "\" target=\"_blank\" rel=\"noopener\">#" +
        i.number + "</a></td><td>" + escapeHtml(i.title) + "</td><td>" + st + " " +
        areaTags(i) + "</td><td>" + escapeHtml(owners) + "</td></tr>"
      );
    }).join("");
    $("issues").innerHTML = rows || "<tr><td colspan='4' class='muted'>이슈 없음</td></tr>";
  }

  function renderPulls(data) {
    const pulls = (data.pulls || []).slice();
    const rows = pulls.map(function (p) {
      const st = p.merged_at
        ? '<span class="tag open">merged</span>'
        : (p.state === "open" ? '<span class="tag open">open</span>' : '<span class="tag closed">closed</span>');
      return (
        "<tr><td><a href=\"" + escapeHtml(p.html_url) + "\" target=\"_blank\" rel=\"noopener\">#" +
        p.number + "</a></td><td>" + escapeHtml(p.title) + "</td><td>" + st +
        "</td><td>" + escapeHtml(p.user && p.user.login ? p.user.login : "") + "</td></tr>"
      );
    }).join("");
    $("pulls").innerHTML = rows || "<tr><td colspan='4' class='muted'>PR 없음</td></tr>";
  }

  function renderCommits(data) {
    const commits = data.commits || [];
    const rows = commits.map(function (c) {
      const sha = c.sha.slice(0, 7);
      const msg = (c.commit && c.commit.message ? c.commit.message : "").split("\n")[0];
      const author = (c.commit && c.commit.author && c.commit.author.name) || "";
      const date = c.commit && c.commit.author && c.commit.author.date
        ? fmtKST(new Date(c.commit.author.date))
        : "";
      return (
        "<tr><td><a href=\"" + escapeHtml(c.html_url) + "\" target=\"_blank\" rel=\"noopener\">" +
        sha + "</a></td><td>" + escapeHtml(msg) + "</td><td>" + escapeHtml(author) +
        "</td><td>" + escapeHtml(date) + "</td></tr>"
      );
    }).join("");
    $("commits").innerHTML = rows || "<tr><td colspan='4' class='muted'>커밋 없음</td></tr>";
  }

  function rateMessage(rate, fetchedAt, usedCache, err) {
    const when = fetchedAt ? fmtKST(new Date(fetchedAt)) : "";
    const bits = [];
    if (usedCache) bits.push("로컬 캐시 표시" + (when ? " (수집 " + when + ")" : ""));
    else if (when) bits.push("GitHub API 갱신 " + when);
    if (rate && rate.remaining != null) {
      bits.push("잔여 요청 " + rate.remaining + "/" + (rate.limit || "?") + " (비인증 한도 60/시간)");
      if (rate.reset) {
        bits.push("한도 리셋 " + fmtKST(new Date(Number(rate.reset) * 1000)));
      }
    }
    bits.push("2분마다 갱신, 결과는 localStorage에 저장");
    let kind = "";
    if (err === "rate_limited") {
      bits.unshift("API 한도에 걸렸습니다. 캐시로 표시합니다.");
      kind = "warn";
    } else if (err) {
      bits.unshift("API 요청 실패(" + err + "). 캐시가 있으면 캐시를 씁니다.");
      kind = usedCache ? "warn" : "bad";
    }
    return { msg: bits.join(" · "), kind: kind };
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderAll(data) {
    renderStats(data);
    renderAreas(data);
    renderMembers(data);
    renderIssues(data);
    renderPulls(data);
    renderCommits(data);
  }

  async function refresh(reason) {
    const cache = loadCache();
    try {
      const data = await loadGithub();
      saveCache(data);
      renderAll(data);
      const b = rateMessage(data.rate, data.fetchedAt, false, null);
      setBanner(b.msg, b.kind);
    } catch (err) {
      const code = err && err.message ? err.message : String(err);
      if (cache && cache.issues) {
        renderAll(cache);
        const b = rateMessage(err.rate || cache.rate, cache.fetchedAt, true, code);
        setBanner(b.msg, b.kind || "warn");
      } else {
        setBanner("GitHub API를 불러오지 못했습니다 (" + code + "). 비인증 한도는 시간당 60회입니다. 잠시 뒤 새로고침하세요.", "bad");
      }
    }
  }

  /* ---- mermaid from ARCHITECTURE.md ---- */
  function extractMermaid(md) {
    const blocks = [];
    const re = /^##\s+(.+)\n([\s\S]*?)(?=^##\s|\s*$)/gm;
    const parts = md.split(/(?=^## )/m);
    parts.forEach(function (part) {
      const titleMatch = part.match(/^##\s+(.+)$/m);
      const title = titleMatch ? titleMatch[1].trim() : "다이어그램";
      const fence = /```mermaid\s*([\s\S]*?)```/g;
      let m;
      while ((m = fence.exec(part))) {
        blocks.push({ title: title, code: m[1].trim() });
      }
    });
    return blocks;
  }

  let mermaidReady = false;
  let mermaidBlocks = [];

  async function loadArchitecture() {
    let lastErr = null;
    for (let i = 0; i < ARCH_URLS.length; i++) {
      try {
        const res = await fetch(ARCH_URLS[i], { cache: "no-store" });
        if (!res.ok) throw new Error("http_" + res.status);
        const md = await res.text();
        mermaidBlocks = extractMermaid(md);
        if (!mermaidBlocks.length) throw new Error("no_mermaid");
        setupTabs(mermaidBlocks);
        return;
      } catch (e) {
        lastErr = e;
      }
    }
    $("mermaid-box").innerHTML = '<div class="empty">ARCHITECTURE.md를 불러오지 못했습니다. <a href="https://github.com/cloudsnuchoi/2026NASA/blob/main/docs/ARCHITECTURE.md">GitHub에서 보기</a>' +
      (lastErr ? " (" + escapeHtml(String(lastErr.message || lastErr)) + ")" : "") + "</div>";
  }

  function setupTabs(blocks) {
    const tabs = $("diagram-tabs");
    tabs.innerHTML = "";
    blocks.forEach(function (b, idx) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = b.title.replace(/^\d+\.\s*/, "");
      btn.addEventListener("click", function () { showDiagram(idx); });
      tabs.appendChild(btn);
    });
    showDiagram(0);
  }

  async function showDiagram(idx) {
    const tabs = $("diagram-tabs").querySelectorAll("button");
    tabs.forEach(function (btn, i) { btn.classList.toggle("active", i === idx); });
    const box = $("mermaid-box");
    const block = mermaidBlocks[idx];
    if (!block) return;
    if (!window.mermaid) {
      box.innerHTML = '<div class="empty">mermaid CDN을 아직 불러오지 못했습니다. 아래 원본을 표시합니다.<pre>' +
        escapeHtml(block.code) + "</pre></div>";
      return;
    }
    if (!mermaidReady) {
      window.mermaid.initialize({
        startOnLoad: false,
        theme: "dark",
        securityLevel: "strict",
        fontFamily: "Pretendard, Noto Sans KR, system-ui, sans-serif",
      });
      mermaidReady = true;
    }
    const id = "mmd-" + idx + "-" + Date.now();
    try {
      const out = await window.mermaid.render(id, block.code);
      box.innerHTML = out.svg;
    } catch (e) {
      box.innerHTML = '<div class="empty">다이어그램 렌더 실패: ' + escapeHtml(String(e)) +
        "</div><pre>" + escapeHtml(block.code) + "</pre>";
    }
  }

  function boot() {
    tickCountdown();
    setInterval(tickCountdown, 1000);
    const cache = loadCache();
    if (cache && cache.issues) {
      renderAll(cache);
      const b = rateMessage(cache.rate, cache.fetchedAt, true, null);
      setBanner(b.msg + " · 최신 데이터 요청 중", "");
    }
    refresh("boot");
    setInterval(function () { refresh("interval"); }, REFRESH_MS);
    loadArchitecture();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
