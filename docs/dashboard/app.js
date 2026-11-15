/* Field Shift live team board — plain JS, no build. dash-v2 */
(function () {
  "use strict";

  const OWNER = "cloudsnuchoi";
  const REPO = "2026NASA";
  const API = "https://api.github.com";
  const CACHE_KEY = "fieldshift-dash-v2";
  const TOKEN_KEY = "fieldshift-gh-token";
  const THEME_KEY = "fieldshift-theme";
  const COMMENT_REFRESH_MS = 2 * 60 * 1000;
  const FULL_SYNC_MS = 10 * 60 * 1000;
  const DEADLINE = new Date("2026-11-15T23:59:00+09:00");
  const COMMENTS_SINCE = "2026-11-14T15:00:00Z"; /* 2026-11-15 00:00 KST */
  const STALE_30 = 30 * 60 * 1000;
  const STALE_60 = 60 * 60 * 1000;
  const ARCH_URLS = [
    "../ARCHITECTURE.md",
    "https://raw.githubusercontent.com/cloudsnuchoi/2026NASA/main/docs/ARCHITECTURE.md",
  ];

  /* 팀원 GitHub 로그인 매핑 — 여기만 고치면 됩니다. */
  const LOGIN_MAP = {
    cloudsnuchoi: "Hylē",
    ssbb215356: "김윤성",
    "flyingbear-code": "김우찬",
    "jieun-Ribby": "고지은",
    hahah383: "하지민",
    kangdaeun2005: "강다은",
  };

  const TEAM = [
    { id: "hyle", name: "Hylē", role: "풀스택·인프라", login: "cloudsnuchoi" },
    { id: "yoonsung", name: "김윤성", role: "MATLAB A", login: "ssbb215356" },
    { id: "woochan", name: "김우찬", role: "MATLAB B", login: "flyingbear-code" },
    { id: "jieun", name: "고지은", role: "UI/UX A", login: "jieun-Ribby" },
    { id: "jimin", name: "하지민", role: "UI/UX B", login: "hahah383" },
    { id: "daeun", name: "강다은", role: "복셀 시뮬", login: "kangdaeun2005" },
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

  const STATE_META = {
    progress: { key: "progress", label: "🟢 진행 중", badge: "progress", card: "state-progress" },
    blocked: { key: "blocked", label: "🔴 막힘", badge: "blocked", card: "state-blocked" },
    review: { key: "review", label: "🟡 리뷰 대기", badge: "review", card: "state-review" },
    done: { key: "done", label: "✅ 완료", badge: "done", card: "state-done" },
  };

  const $ = (id) => document.getElementById(id);
  const banner = $("banner");

  function getToken() {
    try { return (localStorage.getItem(TOKEN_KEY) || "").trim(); } catch (e) { return ""; }
  }

  function setToken(value) {
    try {
      if (value) localStorage.setItem(TOKEN_KEY, value);
      else localStorage.removeItem(TOKEN_KEY);
    } catch (e) { /* private mode */ }
  }

  function hasToken() { return !!getToken(); }

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
    return parts + " Asia/Seoul (KST)";
  }

  function fmtKSTShort(d) {
    return new Intl.DateTimeFormat("sv-SE", {
      timeZone: "Asia/Seoul",
      hour: "2-digit", minute: "2-digit", second: "2-digit",
      hour12: false,
    }).format(d);
  }

  function relativeKo(then, now) {
    const ms = now - then;
    if (ms < 0) return "방금";
    const s = Math.floor(ms / 1000);
    if (s < 20) return "방금";
    if (s < 60) return s + "초 전";
    const m = Math.floor(s / 60);
    if (m < 60) return m + "분 전";
    const h = Math.floor(m / 60);
    if (h < 24) return h + "시간 " + (m % 60) + "분 전";
    return fmtKST(then);
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
      ? cur.label
      : (now < new Date(TIME_BLOCKS[0].start)
        ? "아직 동결 창 전"
        : "마감 이후");
  }

  function loadCache() {
    try {
      const raw = localStorage.getItem(CACHE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) { return null; }
  }

  function saveCache(data) {
    try { localStorage.setItem(CACHE_KEY, JSON.stringify(data)); } catch (e) { /* quota */ }
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

  function authHeaders() {
    const headers = { Accept: "application/vnd.github+json" };
    const token = getToken();
    if (token) headers.Authorization = "Bearer " + token;
    return headers;
  }

  async function fetchJson(url) {
    const res = await fetch(url, { headers: authHeaders() });
    const rate = rateFrom(res);
    if (res.status === 403 || res.status === 429) {
      const err = new Error("rate_limited");
      err.rate = rate;
      err.status = res.status;
      throw err;
    }
    if (res.status === 401) {
      const err = new Error("bad_token");
      err.rate = rate;
      err.status = 401;
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

  async function fetchAll(url, maxPages) {
    let acc = [];
    let next = url;
    let rate = null;
    let guard = 0;
    const cap = maxPages || 2;
    while (next && guard < cap) {
      const page = await fetchJson(next);
      acc = acc.concat(page.data);
      rate = page.rate;
      next = parseLinkNext(page.link);
      guard += 1;
    }
    return { data: acc, rate: rate };
  }

  function issueNumberFromComment(c) {
    const url = c.issue_url || "";
    const m = url.match(/\/issues\/(\d+)$/);
    return m ? Number(m[1]) : null;
  }

  function parseStatus(body) {
    if (!body) return null;
    const lines = body.replace(/\r\n/g, "\n").split("\n");
    const first = (lines[0] || "").trim();
    const head = first.match(/^STATUS:\s*(?:(🟢|🔴|🟡|✅)\s*)?(진행\s*중|막힘|리뷰\s*대기|완료)/);
    if (!head) return null;
    const label = head[2].replace(/\s+/g, " ").trim();
    let key = "progress";
    if (label === "막힘") key = "blocked";
    else if (label === "리뷰 대기") key = "review";
    else if (label === "완료") key = "done";
    const field = function (name) {
      const re = new RegExp("^" + name + "\\s*:\\s*(.*)$");
      for (let i = 1; i < lines.length; i++) {
        const m = lines[i].trim().match(re);
        if (m) return m[1].trim();
      }
      return "";
    };
    const progRaw = field("진행률");
    const progM = progRaw.match(/(\d+)/);
    return {
      key: key,
      task: field("작업"),
      progress: progM ? Math.min(100, Number(progM[1])) : null,
      blocked: field("막힌\\s*점") || field("막힌 점"),
      next: field("다음"),
    };
  }

  function nameOfLogin(login) {
    return LOGIN_MAP[login] || login;
  }

  function memberByLogin(login) {
    return TEAM.find(function (m) { return m.login === login; }) || null;
  }

  function isIssue(item) { return !item.pull_request; }

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
    return TEAM.filter(function (mem) {
      const re = new RegExp(mem.name.replace(/[ē]/g, "e?") + "|Hylē|하일리", mem.name === "Hylē" ? "i" : undefined);
      if (mem.name === "Hylē") return /hyl[eē]|하일리/i.test(text);
      if (mem.name === "김윤성") return /김윤성|윤성/.test(text);
      if (mem.name === "김우찬") return /김우찬|우찬/.test(text);
      if (mem.name === "고지은") return /고지은|지은/.test(text);
      if (mem.name === "하지민") return /하지민|지민/.test(text);
      if (mem.name === "강다은") return /강다은|다은/.test(text);
      return re.test(text);
    });
  }

  function pct(n, d) {
    if (!d) return 0;
    return Math.round((100 * n) / d);
  }

  function mergeComments(prev, incoming) {
    const map = {};
    (prev || []).concat(incoming || []).forEach(function (c) { map[c.id] = c; });
    return Object.keys(map).map(function (k) { return map[k]; });
  }

  function latestStatusByLogin(comments) {
    const by = {};
    (comments || []).forEach(function (c) {
      const parsed = parseStatus(c.body);
      if (!parsed) return;
      const login = c.user && c.user.login;
      if (!login) return;
      const t = new Date(c.updated_at || c.created_at).getTime();
      if (!by[login] || t > by[login].time) {
        by[login] = { comment: c, parsed: parsed, time: t, issue: issueNumberFromComment(c) };
      }
    });
    return by;
  }

  function issueByNumber(data, n) {
    return (data.issues || []).find(function (i) { return i.number === n; }) || null;
  }

  function renderMemberCards(data) {
    const now = Date.now();
    const latest = latestStatusByLogin(data.comments || []);
    const pulls = (data.pulls || []).filter(function (p) { return p.state === "open"; });
    const html = TEAM.map(function (mem) {
      const st = latest[mem.login];
      const meta = st ? STATE_META[st.parsed.key] : null;
      const age = st ? now - st.time : null;
      let staleClass = "";
      let staleHtml = "";
      if (st && st.parsed.key !== "done") {
        if (age > STALE_60) {
          staleClass = "stale-60";
          staleHtml = '<span class="stale-flag bad">60분 초과</span>';
        } else if (age > STALE_30) {
          staleClass = "stale-30";
          staleHtml = '<span class="stale-flag warn">30분 초과</span>';
        }
      }
      const cardClass = "member-card " + (meta ? meta.card : "") + (staleClass ? " " + staleClass : "");
      const badge = meta
        ? '<span class="badge ' + meta.badge + '">' + escapeHtml(meta.label) + "</span>"
        : '<span class="badge">보고 없음</span>';
      const task = st && st.parsed.task
        ? '<p class="task-text">' + escapeHtml(st.parsed.task) + "</p>"
        : '<p class="task-text empty">아직 STATUS 댓글이 없습니다.</p>';
      const prog = st && st.parsed.progress != null ? st.parsed.progress : null;
      const bar = prog != null
        ? '<div class="progress-row"><div class="bar" role="progressbar" aria-valuenow="' + prog +
          '" aria-valuemin="0" aria-valuemax="100"><span style="width:' + prog + '%"></span></div>' +
          '<div class="pct">' + prog + "%</div></div>"
        : '<div class="progress-row"><div class="bar"><span style="width:0%"></span></div><div class="pct muted">—</div></div>';
      let issueHtml = "";
      if (st && st.issue) {
        const iss = issueByNumber(data, st.issue);
        const title = iss ? iss.title : "이슈 #" + st.issue;
        const href = iss && iss.html_url
          ? iss.html_url
          : "https://github.com/" + OWNER + "/" + REPO + "/issues/" + st.issue;
        issueHtml = '<a class="issue-link" href="' + escapeHtml(href) + '" target="_blank" rel="noopener">#' +
          st.issue + " " + escapeHtml(title) + "</a>";
      } else {
        const assigned = (data.issues || []).filter(isIssue).filter(function (i) {
          return i.state === "open" && ownersOf(i).some(function (o) { return o.id === mem.id; });
        }).slice(0, 2);
        issueHtml = assigned.length
          ? assigned.map(function (i) {
              return '<a class="issue-link" href="' + escapeHtml(i.html_url) + '" target="_blank" rel="noopener">#' +
                i.number + " " + escapeHtml(i.title) + "</a>";
            }).join("<br>")
          : '<span class="muted">연결된 이슈 없음</span>';
      }
      const ago = st
        ? '<div class="ago">마지막 보고 ' + escapeHtml(relativeKo(st.time, now)) +
          " (" + escapeHtml(fmtKSTShort(new Date(st.time))) + " KST)</div>"
        : '<div class="ago">보고 시각 없음</div>';
      const minePr = pulls.filter(function (p) { return p.user && p.user.login === mem.login; });
      const prHtml = minePr.length
        ? '<div class="pr-line">열린 PR: ' + minePr.map(function (p) {
            return '<a href="' + escapeHtml(p.html_url) + '" target="_blank" rel="noopener">#' + p.number +
              " " + escapeHtml(p.title) + "</a>";
          }).join(", ") + "</div>"
        : '<div class="pr-line muted">열린 PR 없음</div>';
      const blocked = st && st.parsed.blocked
        ? '<p class="blocked-note">막힌 점: ' + escapeHtml(st.parsed.blocked) + "</p>"
        : "";
      const next = st && st.parsed.next
        ? '<p class="next-note">다음: ' + escapeHtml(st.parsed.next) + "</p>"
        : "";
      return (
        '<article class="' + cardClass + '" data-login="' + escapeHtml(mem.login) + '">' +
          '<div class="member-top">' + badge + staleHtml + "</div>" +
          "<h3 class=\"member-name\">" + escapeHtml(mem.name) + "</h3>" +
          '<p class="member-meta">' + escapeHtml(mem.role) + " · @" + escapeHtml(mem.login) + "</p>" +
          '<div class="task-label">현재 작업</div>' + task + bar + issueHtml + blocked + next + ago + prHtml +
        "</article>"
      );
    }).join("");
    $("member-cards").innerHTML = html;
  }

  function renderStats(data) {
    const issues = (data.issues || []).filter(isIssue);
    const openI = issues.filter(function (i) { return i.state === "open"; });
    const closedI = issues.filter(function (i) { return i.state === "closed"; });
    const pulls = data.pulls || [];
    const openP = pulls.filter(function (p) { return p.state === "open"; });
    const merged = pulls.filter(function (p) { return p.merged_at; });
    const latest = latestStatusByLogin(data.comments || []);
    let blocked = 0, active = 0;
    Object.keys(latest).forEach(function (login) {
      if (latest[login].parsed.key === "blocked") blocked += 1;
      if (latest[login].parsed.key === "progress") active += 1;
    });
    $("stats").innerHTML =
      stat("열린 이슈", openI.length) +
      stat("닫힌 이슈", closedI.length) +
      stat("전체 진행", pct(closedI.length, issues.length) + "%") +
      stat("열린 PR", openP.length) +
      stat("머지된 PR", merged.length) +
      stat("진행 중 / 막힘", active + " / " + blocked);
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

  function ciTag(sha, statuses) {
    const st = (statuses || {})[sha];
    if (!st || !st.state || st.state === "pending" && !st.total_count) {
      return '<span class="tag">CI 미확인</span>';
    }
    if (st.state === "success") return '<span class="tag ci-success">CI 통과</span>';
    if (st.state === "pending") return '<span class="tag ci-pending">CI 진행</span>';
    if (st.state === "failure" || st.state === "error") return '<span class="tag ci-failure">CI 실패</span>';
    return '<span class="tag">CI ' + escapeHtml(st.state) + "</span>";
  }

  function renderPrQueue(data) {
    const open = (data.pulls || []).filter(function (p) { return p.state === "open"; });
    if (!open.length) {
      $("pr-queue").innerHTML = '<div class="empty">열린 PR이 없습니다.</div>';
      return;
    }
    $("pr-queue").innerHTML = open.map(function (p) {
      const sha = p.head && p.head.sha;
      const draft = p.draft ? '<span class="tag draft">초안</span>' : "";
      const review = p.draft
        ? '<span class="tag">초안</span>'
        : '<span class="tag p1">리뷰 필요</span>';
      const author = p.user && p.user.login ? p.user.login : "";
      const who = nameOfLogin(author);
      return (
        '<div class="pr-item"><div class="pr-title"><a href="' + escapeHtml(p.html_url) +
        '" target="_blank" rel="noopener">#' + p.number + " " + escapeHtml(p.title) +
        "</a></div><div>" + draft + review + ciTag(sha, data.statuses) +
        ' <span class="muted">@' + escapeHtml(author) + (who !== author ? " · " + escapeHtml(who) : "") +
        "</span></div></div>"
      );
    }).join("");
  }

  function renderFeed(data) {
    const items = [];
    (data.comments || []).forEach(function (c) {
      const login = c.user && c.user.login;
      const parsed = parseStatus(c.body);
      const n = issueNumberFromComment(c);
      const snippet = parsed
        ? (STATE_META[parsed.key].label + (parsed.task ? " · " + parsed.task : ""))
        : (c.body || "").split("\n")[0].slice(0, 120);
      items.push({
        t: new Date(c.created_at).getTime(),
        kind: parsed ? "STATUS" : "댓글",
        html: '<a href="' + escapeHtml(c.html_url) + '" target="_blank" rel="noopener">#' +
          (n || "?") + "</a> @" + escapeHtml(login) + " (" + escapeHtml(nameOfLogin(login)) + ") " +
          escapeHtml(snippet),
      });
    });
    (data.commits || []).forEach(function (c) {
      const sha = c.sha.slice(0, 7);
      const msg = (c.commit && c.commit.message ? c.commit.message : "").split("\n")[0];
      const author = (c.author && c.author.login) || (c.commit && c.commit.author && c.commit.author.name) || "";
      const date = c.commit && c.commit.author && c.commit.author.date;
      items.push({
        t: date ? new Date(date).getTime() : 0,
        kind: "커밋",
        html: '<a href="' + escapeHtml(c.html_url) + '" target="_blank" rel="noopener">' + sha +
          "</a> " + escapeHtml(msg) + ' <span class="muted">' + escapeHtml(author) + "</span>",
      });
    });
    (data.pulls || []).forEach(function (p) {
      const author = p.user && p.user.login ? p.user.login : "";
      items.push({
        t: new Date(p.created_at).getTime(),
        kind: "PR",
        html: '<a href="' + escapeHtml(p.html_url) + '" target="_blank" rel="noopener">#' +
          p.number + " " + escapeHtml(p.title) + "</a> @" + escapeHtml(author),
      });
      if (p.merged_at) {
        items.push({
          t: new Date(p.merged_at).getTime(),
          kind: "머지",
          html: '<a href="' + escapeHtml(p.html_url) + '" target="_blank" rel="noopener">#' +
            p.number + "</a> 머지됨",
        });
      }
    });
    items.sort(function (a, b) { return b.t - a.t; });
    const top = items.slice(0, 25);
    $("activity-feed").innerHTML = top.map(function (it) {
      return '<li class="feed-item"><span class="feed-time">' + escapeHtml(fmtKSTShort(new Date(it.t))) +
        " KST</span><span class=\"feed-kind\">" + escapeHtml(it.kind) + "</span><span>" + it.html + "</span></li>";
    }).join("") || '<li class="empty">활동이 아직 없습니다.</li>';
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

  function rateMessage(rate, fetchedAt, usedCache, err) {
    const when = fetchedAt ? fmtKSTShort(new Date(fetchedAt)) + " KST" : "";
    const bits = [];
    if (usedCache) bits.push("캐시" + (when ? " " + when : ""));
    else if (when) bits.push("갱신 " + when);
    if (rate && rate.remaining != null) {
      bits.push("잔여 " + rate.remaining + "/" + (rate.limit || "?") + (hasToken() ? " (토큰)" : ""));
    }
    bits.push(hasToken() ? "2분마다 갱신" : "댓글 2분 · 이슈/PR 10분");
    let kind = "";
    if (err === "rate_limited") {
      bits.unshift("API 한도에 걸렸습니다. 캐시로 표시합니다.");
      kind = "warn";
    } else if (err === "bad_token") {
      bits.unshift("토큰이 거부되었습니다. 토큰을 지우고 비인증으로 다시 시도하세요.");
      kind = "bad";
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
    renderMemberCards(data);
    renderStats(data);
    renderAreas(data);
    renderPrQueue(data);
    renderFeed(data);
    renderIssues(data);
  }

  async function loadComments(since) {
    const q = "sort=updated&direction=desc&per_page=100&since=" + encodeURIComponent(since || COMMENTS_SINCE);
    return fetchJson(API + "/repos/" + OWNER + "/" + REPO + "/issues/comments?" + q);
  }

  async function loadFull() {
    const issuesUrl = API + "/repos/" + OWNER + "/" + REPO + "/issues?state=all&per_page=100";
    const pullsUrl = API + "/repos/" + OWNER + "/" + REPO + "/pulls?state=all&per_page=100";
    const commitsUrl = API + "/repos/" + OWNER + "/" + REPO + "/commits?per_page=20";
    const [issues, pulls, commits, comments] = await Promise.all([
      fetchAll(issuesUrl, 2),
      fetchAll(pullsUrl, 2),
      fetchJson(commitsUrl),
      loadComments(COMMENTS_SINCE),
    ]);
    const data = {
      fetchedAt: Date.now(),
      fullSyncAt: Date.now(),
      issues: issues.data,
      pulls: pulls.data,
      commits: commits.data,
      comments: comments.data,
      statuses: {},
      rate: comments.rate || commits.rate || pulls.rate || issues.rate,
    };
    await maybeLoadStatuses(data);
    return data;
  }

  async function maybeLoadStatuses(data) {
    const open = (data.pulls || []).filter(function (p) { return p.state === "open" && p.head && p.head.sha; });
    if (!open.length) return;
    const remaining = data.rate && data.rate.remaining != null ? Number(data.rate.remaining) : 0;
    const allow = hasToken() || remaining > 20;
    if (!allow || open.length > 5) return;
    const statuses = data.statuses || {};
    for (let i = 0; i < open.length; i++) {
      try {
        const r = await fetchJson(API + "/repos/" + OWNER + "/" + REPO + "/commits/" + open[i].head.sha + "/status");
        statuses[open[i].head.sha] = { state: r.data.state, total_count: r.data.total_count };
        data.rate = r.rate || data.rate;
      } catch (e) { /* skip CI */ }
    }
    data.statuses = statuses;
  }

  async function loadCommentsOnly(cache) {
    const since = cache && cache.fetchedAt
      ? new Date(cache.fetchedAt - 60 * 1000).toISOString()
      : COMMENTS_SINCE;
    const comments = await loadComments(since);
    const merged = mergeComments(cache && cache.comments, comments.data);
    return {
      fetchedAt: Date.now(),
      fullSyncAt: cache && cache.fullSyncAt,
      issues: (cache && cache.issues) || [],
      pulls: (cache && cache.pulls) || [],
      commits: (cache && cache.commits) || [],
      comments: merged,
      statuses: (cache && cache.statuses) || {},
      rate: comments.rate,
    };
  }

  async function refresh(reason) {
    const cache = loadCache();
    const now = Date.now();
    const fullAge = cache && cache.fullSyncAt ? now - cache.fullSyncAt : Infinity;
    const wantFull = reason === "boot" || reason === "manual" || hasToken() || fullAge >= FULL_SYNC_MS || !cache || !cache.issues;
    try {
      const data = wantFull ? await loadFull() : await loadCommentsOnly(cache);
      if (!wantFull && cache && cache.issues) {
        /* keep previous full payload */
      }
      saveCache(data);
      renderAll(data);
      const b = rateMessage(data.rate, data.fetchedAt, false, null);
      setBanner(b.msg, b.kind);
    } catch (err) {
      const code = err && err.message ? err.message : String(err);
      if (code === "bad_token") setToken("");
      if (cache && (cache.issues || cache.comments)) {
        renderAll(cache);
        const b = rateMessage(err.rate || cache.rate, cache.fetchedAt, true, code);
        setBanner(b.msg, b.kind || "warn");
      } else {
        setBanner("GitHub API를 불러오지 못했습니다 (" + code + "). 비인증 한도는 시간당 60회입니다. 잠시 뒤 새로고침하세요.", "bad");
        $("member-cards").innerHTML = TEAM.map(function (mem) {
          return '<article class="member-card"><h3 class="member-name">' + escapeHtml(mem.name) +
            '</h3><p class="member-meta">' + escapeHtml(mem.role) + " · @" + escapeHtml(mem.login) +
            '</p><p class="task-text empty">데이터를 아직 불러오지 못했습니다.</p></article>';
        }).join("");
      }
    }
  }

  /* ---- mermaid from ARCHITECTURE.md ---- */
  let mermaidReady = false;
  let mermaidBlocks = [];
  let mermaidTheme = "dark";
  let mermaidIdx = 0;

  function currentTheme() {
    return document.documentElement.getAttribute("data-theme") || "dark";
  }

  function applyTheme(theme) {
    const t = theme === "light" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", t);
    try { localStorage.setItem(THEME_KEY, t); } catch (e) { /* */ }
    if (mermaidBlocks.length) {
      mermaidReady = false;
      mermaidTheme = t;
      showDiagram(0);
    }
  }

  function initTheme() {
    let t = null;
    try { t = localStorage.getItem(THEME_KEY); } catch (e) { t = null; }
    if (!t && window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches) t = "light";
    applyTheme(t || "dark");
  }

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
      } catch (e) { lastErr = e; }
    }
    $("mermaid-box").innerHTML = '<div class="empty">ARCHITECTURE.md를 불러오지 못했습니다. <a href="https://github.com/cloudsnuchoi/2026NASA/blob/main/docs/ARCHITECTURE.md">GitHub에서 보기</a>' +
      (lastErr ? " (" + escapeHtml(String(lastErr.message || lastErr)) + ")" : "") + "</div>";
  }

  function extractMermaid(md) {
    const blocks = [];
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
    mermaidIdx = idx;
    if (!block) return;
    if (!window.mermaid) {
      box.innerHTML = '<div class="empty">mermaid CDN을 아직 불러오지 못했습니다. 아래 원본을 표시합니다.<pre>' +
        escapeHtml(block.code) + "</pre></div>";
      return;
    }
    const theme = currentTheme() === "light" ? "neutral" : "dark";
    if (!mermaidReady || mermaidTheme !== currentTheme()) {
      window.mermaid.initialize({
        startOnLoad: false,
        theme: theme,
        securityLevel: "strict",
        fontFamily: "Pretendard, Noto Sans KR, system-ui, sans-serif",
      });
      mermaidReady = true;
      mermaidTheme = currentTheme();
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

  function bindChrome() {
    const themeBtn = $("theme-toggle");
    if (themeBtn) {
      themeBtn.addEventListener("click", function () {
        applyTheme(currentTheme() === "dark" ? "light" : "dark");
      });
    }
    window.addEventListener("fieldshift:theme", function () {
      if (mermaidBlocks.length) {
        mermaidReady = false;
        showDiagram(typeof mermaidIdx === "number" ? mermaidIdx : 0);
      }
    });
    $("refresh-btn").addEventListener("click", function () { refresh("manual"); });
    $("token-save").addEventListener("click", function () {
      const v = ($("token-input").value || "").trim();
      if (!v) return;
      setToken(v);
      $("token-input").value = "";
      updateTokenState();
      refresh("manual");
    });
    $("token-clear").addEventListener("click", function () {
      setToken("");
      $("token-input").value = "";
      updateTokenState();
      refresh("manual");
    });
    updateTokenState();
  }

  function updateTokenState() {
    $("token-state").textContent = hasToken()
      ? "이 브라우저에 토큰이 저장되어 있습니다. 한도가 올라갑니다. 광범위 토큰은 사용하지 마세요."
      : "토큰 없음 · 비인증 한도 60회/시간";
  }

  function boot() {
    initTheme();
    bindChrome();
    tickCountdown();
    setInterval(tickCountdown, 1000);
    const cache = loadCache();
    if (cache && (cache.issues || cache.comments)) {
      renderAll(cache);
      const b = rateMessage(cache.rate, cache.fetchedAt, true, null);
      setBanner(b.msg + " · 최신 데이터 요청 중", "");
    } else {
      $("member-cards").innerHTML = TEAM.map(function (mem) {
        return '<article class="member-card"><h3 class="member-name">' + escapeHtml(mem.name) +
          '</h3><p class="member-meta">' + escapeHtml(mem.role) + " · @" + escapeHtml(mem.login) +
          '</p><p class="task-text empty">불러오는 중…</p></article>';
      }).join("");
    }
    refresh("boot");
    setInterval(function () { refresh("interval"); }, COMMENT_REFRESH_MS);
    loadArchitecture();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
