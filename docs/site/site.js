/* Shared Field Shift Pages chrome — no build step. */
(function (global) {
  "use strict";

  const THEME_KEY = "fieldshift-theme";
  const DRIVE_URL = "https://drive.google.com/drive/folders/1pUlXbE_VNiMGHVYSkHHT4Mr-nzo--Yqd";
  const DEFAULT_CHAT_URL = "https://process-investigators-dean-unified.trycloudflare.com/";
  const LIVE_POLL_MS = 60000;
  const RAW_DOCS = "https://raw.githubusercontent.com/cloudsnuchoi/2026NASA/main/docs/";
  const PAGES = [
    { id: "dashboard", label: "현황판", href: "dashboard/" },
    { id: "roadmap", label: "로드맵·체크리스트", href: "roadmap.html" },
    { id: "data", label: "데이터셋", href: "data.html" },
    { id: "architecture", label: "아키텍처·파이프라인", href: "architecture.html" },
    { id: "models", label: "AI 모델", href: "models.html" },
    { id: "overview", label: "개요/PRD", href: "overview.html" },
    { id: "team", label: "팀", href: "team.html" },
  ];

  function inDashboard() {
    const p = location.pathname.replace(/\/+$/, "") || "/";
    return /\/dashboard(?:\/index\.html)?$/.test(p);
  }

  function rootPrefix() {
    return inDashboard() ? "../" : "./";
  }

  function currentTheme() {
    return document.documentElement.getAttribute("data-theme") || "dark";
  }

  function applyTheme(theme) {
    const t = theme === "light" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", t);
    try { localStorage.setItem(THEME_KEY, t); } catch (e) { /* */ }
    const btn = document.getElementById("site-theme-toggle");
    if (btn) btn.textContent = t === "dark" ? "밝은 테마" : "어두운 테마";
    window.dispatchEvent(new CustomEvent("fieldshift:theme", { detail: t }));
  }

  function initTheme() {
    let t = null;
    try { t = localStorage.getItem(THEME_KEY); } catch (e) { t = null; }
    applyTheme(t || "dark");
  }

  function injectNav(activeId) {
    let nav = document.getElementById("site-nav");
    if (!nav) {
      nav = document.createElement("nav");
      nav.id = "site-nav";
      nav.setAttribute("aria-label", "주요 메뉴");
      document.body.insertBefore(nav, document.body.firstChild);
    }
    nav.classList.add("site-nav");
    const root = rootPrefix();
    const links = PAGES.map(function (p) {
      const href = root + p.href;
      const cls = p.id === activeId ? " active" : "";
      const aria = p.id === activeId ? ' aria-current="page"' : "";
      return '<a class="' + cls.trim() + '"' + aria + ' href="' + href + '">' + p.label + "</a>";
    }).join("") +
      '<a class="drive-link" href="' + DRIVE_URL + '" target="_blank" rel="noopener">팀 드라이브 (아몰라)</a>' +
      chatLink("drive-link") + demoLink("drive-link");

    nav.innerHTML =
      '<div class="nav-inner">' +
        '<a class="site-brand" href="' + root + 'overview.html">' +
          "<strong>팀 아몰라</strong><span>Field Shift · 2026NASA</span>" +
        "</a>" +
        '<button type="button" class="icon-btn nav-toggle" id="nav-toggle" aria-expanded="false" aria-controls="site-links">메뉴</button>' +
        '<div class="site-links" id="site-links">' + links + "</div>" +
        exportMenuHtml() +
        '<button type="button" class="icon-btn" id="site-theme-toggle" aria-label="밝은/어두운 테마 전환">테마</button>' +
      "</div>";

    const toggle = document.getElementById("nav-toggle");
    if (toggle) {
      toggle.addEventListener("click", function () {
        const open = nav.classList.toggle("open");
        toggle.setAttribute("aria-expanded", open ? "true" : "false");
      });
    }
    bindExportMenu();
    const themeBtn = document.getElementById("site-theme-toggle");
    if (themeBtn) {
      themeBtn.addEventListener("click", function () {
        applyTheme(currentTheme() === "dark" ? "light" : "dark");
      });
      themeBtn.textContent = currentTheme() === "dark" ? "밝은 테마" : "어두운 테마";
    }
  }

  function injectFooter() {
    let el = document.getElementById("site-footer");
    if (!el) {
      el = document.createElement("footer");
      el.id = "site-footer";
      el.className = "site-footer";
      document.body.appendChild(el);
    } else {
      el.classList.add("site-footer");
    }
    const root = rootPrefix();
    const pageLinks = PAGES.map(function (p) {
      return '<a href="' + root + p.href + '">' + p.label + "</a>";
    }).join("");
    el.innerHTML =
      '<div class="footer-links">' +
        pageLinks +
        '<a href="' + DRIVE_URL + '" target="_blank" rel="noopener">팀 드라이브 (아몰라)</a>' +
        chatLink("") +
        '<a href="https://github.com/cloudsnuchoi/2026NASA" target="_blank" rel="noopener">GitHub</a>' +
      "</div>" +
      "<p>코드는 항상 GitHub에 둡니다. 슬라이드·이미지·작은 CSV는 " +
      '<a href="' + DRIVE_URL + '" target="_blank" rel="noopener">팀 드라이브 (아몰라)</a>' +
      "의 PRD·DESIGN·FRONT·BACK·DATA 폴더에 올립니다. 질문은 " + chatLink("") + "에 남깁니다. 대용량 데이터는 VPS에 둡니다. " +
      "원문은 <code>docs/PRD.md</code>, <code>SOT.md</code>, <code>ARCHITECTURE.md</code>, <code>TEAM_SPEC.md</code>, <code>DECISIONS.md</code>이며, 충돌하면 가장 최근 DECISIONS 항목을 따릅니다. 시각은 Asia/Seoul (KST)입니다.</p>";
  }

  async function fetchFirst(urls) {
    let lastErr = null;
    for (let i = 0; i < urls.length; i++) {
      try {
        const res = await fetch(urls[i], { cache: "no-store" });
        if (!res.ok) throw new Error("http_" + res.status);
        return await res.text();
      } catch (e) { lastErr = e; }
    }
    throw lastErr || new Error("fetch_failed");
  }

  function docsUrls(name) {
    return [rootPrefix() + name, RAW_DOCS + name];
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
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
        blocks.push({ title: title, code: m[1].trim(), section: part });
      }
    });
    return blocks;
  }

  function sectionBetween(md, startRe, endRe) {
    const start = md.search(startRe);
    if (start < 0) return "";
    const rest = md.slice(start);
    if (!endRe) return rest;
    const m = rest.slice(1).search(endRe);
    return m < 0 ? rest : rest.slice(0, m + 1);
  }

  let mermaidReady = false;
  let mermaidTheme = null;

  async function ensureMermaid() {
    if (!window.mermaid) return false;
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
    return true;
  }

  async function renderMermaidInto(box, code, key) {
    if (!box) return;
    if (!(await ensureMermaid())) {
      box.innerHTML = '<div class="empty">mermaid CDN을 아직 불러오지 못했습니다.</div><pre>' + escapeHtml(code) + "</pre>";
      return;
    }
    const id = "mmd-" + (key || "x") + "-" + Date.now() + "-" + Math.floor(Math.random() * 1e6);
    try {
      const out = await window.mermaid.render(id, code);
      box.innerHTML = out.svg;
    } catch (e) {
      box.innerHTML = '<div class="empty">다이어그램 렌더 실패: ' + escapeHtml(String(e)) +
        "</div><pre>" + escapeHtml(code) + "</pre>";
    }
  }

  function markedParse(md) {
    if (!window.marked || !window.marked.parse) {
      return "<pre>" + escapeHtml(md) + "</pre>";
    }
    const renderer = {
      code: function (code, info) {
        /* marked v9+ passes a token object; older passes (code, lang). */
        let text = code;
        let lang = info || "";
        if (code && typeof code === "object") {
          text = code.text || "";
          lang = code.lang || "";
        }
        if (String(lang).trim() === "mermaid") {
          return '<div class="mermaid-box"><div class="mermaid">' + escapeHtml(text) + "</div></div>";
        }
        return "<pre><code>" + escapeHtml(text) + "</code></pre>";
      },
    };
    try {
      if (window.marked.use) {
        /* clone-like: parse with renderer option */
        return window.marked.parse(md, { gfm: true, breaks: false, renderer: Object.assign(new window.marked.Renderer(), renderer) });
      }
      return window.marked.parse(md, { gfm: true, renderer: renderer });
    } catch (e) {
      return window.marked.parse(md);
    }
  }

  function rewriteDocLinks(container) {
    if (!container) return;
    container.querySelectorAll("a[href]").forEach(function (a) {
      const href = a.getAttribute("href") || "";
      const map = {
        "./PRD.md": "prd.html",
        "PRD.md": "prd.html",
        "./SOT.md": "data.html",
        "SOT.md": "data.html",
        "./ARCHITECTURE.md": "architecture.html",
        "ARCHITECTURE.md": "architecture.html",
        "./TEAM_SPEC.md": "team.html",
        "TEAM_SPEC.md": "team.html",
        "./DECISIONS.md": "https://github.com/cloudsnuchoi/2026NASA/blob/main/docs/DECISIONS.md",
        "DECISIONS.md": "https://github.com/cloudsnuchoi/2026NASA/blob/main/docs/DECISIONS.md",
        "./dashboard/index.html": "dashboard/",
        "./PROMPTS.md": "https://github.com/cloudsnuchoi/2026NASA/blob/main/docs/PROMPTS.md",
        "PROMPTS.md": "https://github.com/cloudsnuchoi/2026NASA/blob/main/docs/PROMPTS.md",
        "./ONBOARDING.md": "https://github.com/cloudsnuchoi/2026NASA/blob/main/docs/ONBOARDING.md",
        "ONBOARDING.md": "https://github.com/cloudsnuchoi/2026NASA/blob/main/docs/ONBOARDING.md",
        "./CHECKLIST.md": "https://github.com/cloudsnuchoi/2026NASA/blob/main/docs/CHECKLIST.md",
        "CHECKLIST.md": "https://github.com/cloudsnuchoi/2026NASA/blob/main/docs/CHECKLIST.md",
      };
      if (map[href]) a.setAttribute("href", map[href]);
    });
  }

  function renderMath(root) {
    if (!window.renderMathInElement || !root) return;
    try {
      window.renderMathInElement(root, {
        delimiters: [
          { left: "$$", right: "$$", display: true },
          { left: "\\[", right: "\\]", display: true },
          { left: "\\(", right: "\\)", display: false },
        ],
        throwOnError: false,
      });
    } catch (e) { /* */ }
  }

  async function renderMarkdownInto(el, md, opts) {
    if (!el) return;
    el.innerHTML = markedParse(md);
    el.classList.add("prose");
    rewriteDocLinks(el);
    const mermaidNodes = el.querySelectorAll(".mermaid");
    if (mermaidNodes.length && window.mermaid) {
      await ensureMermaid();
      try { await window.mermaid.run({ querySelector: "#" + (el.id || "missing") + " .mermaid" }); }
      catch (e) { /* individual boxes may still show source */ }
    }
    if (!opts || opts.math !== false) renderMath(el);
  }

  function tocFrom(el, tocEl) {
    if (!el || !tocEl) return;
    const heads = el.querySelectorAll("h2");
    if (!heads.length) { tocEl.hidden = true; return; }
    const items = [];
    heads.forEach(function (h, i) {
      if (!h.id) h.id = "sec-" + (i + 1);
      items.push('<li><a href="#' + h.id + '">' + escapeHtml(h.textContent) + "</a></li>");
    });
    tocEl.innerHTML = "<h2>목차</h2><ol>" + items.join("") + "</ol>";
    tocEl.hidden = false;
  }


  /* ---------- team chat link (default URL, replaced by live.json chat_url) ---------- */
  let chatUrl = DEFAULT_CHAT_URL;

  function chatLink(cls) {
    return '<a class="chat-link ' + cls + '" href="' + escapeHtml(chatUrl) + '" target="_blank" rel="noopener">팀 채팅</a>';
  }

  /* ---------- live demo link (hidden until live.json has demo_url) ---------- */
  function demoLink(cls) {
    return '<a class="demo-link ' + cls + '" href="#" target="_blank" rel="noopener" style="display:none">라이브 데모</a>';
  }

  function setDemoUrl(url) {
    if (!/^https?:\/\//i.test(String(url || ""))) return;
    document.querySelectorAll("a.demo-link").forEach(function (a) { a.setAttribute("href", url); a.style.display = ""; });
  }

  function setChatUrl(url) {
    if (!/^https?:\/\//i.test(String(url || ""))) return;
    chatUrl = url;
    document.querySelectorAll("a.chat-link").forEach(function (a) { a.setAttribute("href", url); });
  }

  /* ---------- live.json polling (shared by all pages) ---------- */
  const liveSubs = [];
  let liveState = null; /* { data, err } once the first fetch has finished */
  let liveTimer = null;

  function liveUrl() { return rootPrefix() + "status/live.json"; }

  async function pollLive() {
    let data = null, err = null;
    try {
      const res = await fetch(liveUrl() + "?t=" + Date.now(), { cache: "no-store" });
      if (!res.ok) throw new Error("http_" + res.status);
      data = await res.json();
      if (!data || typeof data !== "object") throw new Error("invalid_json");
    } catch (e) { data = null; err = String(e.message || e); }
    liveState = { data: data, err: err };
    if (data && data.chat_url) setChatUrl(data.chat_url);
    if (data && data.demo_url) setDemoUrl(data.demo_url);
    liveSubs.forEach(function (cb) { try { cb(data, err); } catch (e) { console.error(e); } });
    return liveState;
  }

  function startLive() {
    if (liveTimer) return;
    pollLive();
    liveTimer = setInterval(pollLive, LIVE_POLL_MS);
  }

  function onLive(cb) {
    liveSubs.push(cb);
    if (liveState) cb(liveState.data, liveState.err);
  }

  /* ---------- 내보내기: Markdown / PDF 인쇄 / JSON ---------- */
  function exportMenuHtml() {
    return '<details class="export-menu" id="site-export">' +
      '<summary class="icon-btn">내보내기</summary>' +
      '<div class="export-pop" role="menu">' +
        '<button type="button" role="menuitem" data-export="md">Markdown</button>' +
        '<button type="button" role="menuitem" data-export="print">PDF 인쇄</button>' +
        (inDashboard() ? '<button type="button" role="menuitem" data-export="json">JSON</button>' : "") +
      "</div></details>";
  }

  function bindExportMenu() {
    const menu = document.getElementById("site-export");
    if (!menu) return;
    menu.addEventListener("click", function (ev) {
      const btn = ev.target.closest("button[data-export]");
      if (!btn) return;
      menu.open = false;
      const kind = btn.getAttribute("data-export");
      if (kind === "md") downloadBlob(pageSlug() + ".md", pageToMarkdown(), "text/markdown;charset=utf-8");
      else if (kind === "print") window.print();
      else if (kind === "json") exportLiveJson();
    });
    document.addEventListener("click", function (ev) {
      if (menu.open && !menu.contains(ev.target)) menu.open = false;
    });
  }

  function pageSlug() {
    if (inDashboard()) return "dashboard";
    const m = location.pathname.match(/([^\/]+)\.html$/);
    return m ? m[1] : "page";
  }

  function downloadBlob(name, text, type) {
    const url = URL.createObjectURL(new Blob([text], { type: type }));
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }

  async function exportLiveJson() {
    try {
      const res = await fetch(liveUrl() + "?t=" + Date.now(), { cache: "no-store" });
      if (!res.ok) throw new Error("http_" + res.status);
      downloadBlob("live.json", await res.text(), "application/json");
    } catch (e) {
      alert("현황 파일 없음 (status/live.json): " + (e.message || e));
    }
  }

  /* Minimal DOM → Markdown: headings, paragraphs, lists, tables, links, code, quotes. */
  const MD_SKIP = /^(SCRIPT|STYLE|NOSCRIPT|SVG|BUTTON|INPUT|SELECT|TEXTAREA|FORM|TEMPLATE|IFRAME|CANVAS)$/;

  function mdInline(node) {
    let out = "";
    node.childNodes.forEach(function (n) {
      if (n.nodeType === 3) { out += n.nodeValue.replace(/\s+/g, " "); return; }
      if (n.nodeType !== 1 || MD_SKIP.test(n.tagName) || n.hidden) return;
      const t = n.tagName;
      const inner = mdInline(n);
      if (t === "A") {
        const href = n.href || "";
        out += href && inner.trim() ? "[" + inner.trim() + "](" + href + ")" : inner;
      } else if (t === "STRONG" || t === "B") out += inner.trim() ? "**" + inner.trim() + "**" : "";
      else if (t === "EM" || t === "I") out += inner.trim() ? "*" + inner.trim() + "*" : "";
      else if (t === "CODE") out += "`" + n.textContent + "`";
      else if (t === "BR") out += "  \n";
      else if (t === "IMG") out += n.alt ? "![" + n.alt + "](" + n.src + ")" : "";
      else if (/^(UL|OL|TABLE|PRE|DETAILS|H[1-6])$/.test(t)) out += " " + n.textContent.replace(/\s+/g, " ") + " ";
      else out += inner;
    });
    return out;
  }

  function mdTable(table) {
    const rows = Array.prototype.slice.call(table.querySelectorAll("tr")).map(function (tr) {
      return Array.prototype.slice.call(tr.children).map(function (c) {
        return mdInline(c).trim().replace(/\|/g, "\\|").replace(/ *\n/g, "<br>") || " ";
      });
    }).filter(function (r) { return r.length; });
    if (!rows.length) return "";
    const w = Math.max.apply(null, rows.map(function (r) { return r.length; }));
    const line = function (r) { while (r.length < w) r.push(" "); return "| " + r.join(" | ") + " |"; };
    const sep = "| " + new Array(w).fill("---").join(" | ") + " |";
    return [line(rows[0]), sep].concat(rows.slice(1).map(line)).join("\n") + "\n\n";
  }

  function mdList(list, depth) {
    let out = "";
    let i = 1;
    const ordered = list.tagName === "OL";
    Array.prototype.forEach.call(list.children, function (li) {
      if (li.tagName !== "LI" || li.hidden) return;
      const clone = li.cloneNode(true);
      clone.querySelectorAll("ul,ol").forEach(function (x) { x.remove(); });
      out += "  ".repeat(depth) + (ordered ? (i++) + ". " : "- ") + mdBlocks(clone).replace(/\n+/g, " ").trim() + "\n";
      Array.prototype.forEach.call(li.children, function (c) {
        if (c.tagName === "UL" || c.tagName === "OL") out += mdList(c, depth + 1);
      });
    });
    return depth ? out : out + "\n";
  }

  function mdBlocks(node) {
    let out = "";
    let buf = "";
    const flush = function () { if (buf.trim()) out += buf.trim() + "\n\n"; buf = ""; };
    node.childNodes.forEach(function (n) {
      if (n.nodeType === 3) { buf += n.nodeValue.replace(/\s+/g, " "); return; }
      if (n.nodeType !== 1 || MD_SKIP.test(n.tagName) || n.hidden) return;
      const t = n.tagName;
      const h = t.match(/^H([1-6])$/);
      if (h) { flush(); out += "#".repeat(+h[1]) + " " + mdInline(n).trim() + "\n\n"; }
      else if (t === "UL" || t === "OL") { flush(); out += mdList(n, 0); }
      else if (t === "TABLE") { flush(); out += mdTable(n); }
      else if (t === "PRE") { flush(); out += "```\n" + n.textContent.replace(/\n$/, "") + "\n```\n\n"; }
      else if (t === "BLOCKQUOTE") { flush(); out += mdBlocks(n).trim().split("\n").map(function (l) { return "> " + l; }).join("\n") + "\n\n"; }
      else if (t === "HR") { flush(); out += "---\n\n"; }
      else if (t === "SUMMARY") { flush(); out += "**" + mdInline(n).trim() + "**\n\n"; }
      else if (/^(P|DIV|SECTION|ARTICLE|HEADER|FOOTER|MAIN|DETAILS|ASIDE|NAV|FIGURE|LI|DL|DD|DT)$/.test(t)) { flush(); out += mdBlocks(n); }
      else buf += mdInline({ childNodes: [n] });
    });
    flush();
    return out;
  }

  function pageToMarkdown() {
    const parts = [];
    const head = document.querySelector("body > header");
    if (head) parts.push(mdBlocks(head));
    const main = document.querySelector("main") || document.body;
    parts.push(mdBlocks(main));
    const meta = "<!-- " + location.href + " · 내보낸 시각 " +
      new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul", dateStyle: "short", timeStyle: "short" }).format(new Date()) +
      " KST -->\n\n";
    return meta + parts.join("").replace(/\n{3,}/g, "\n\n").trim() + "\n";
  }

  function mount(opts) {
    opts = opts || {};
    initTheme();
    injectNav(opts.active || "");
    injectFooter();
    startLive();
  }

  global.FieldShiftSite = {
    DRIVE_URL: DRIVE_URL,
    onLive: onLive,
    pollLive: pollLive,
    pageToMarkdown: pageToMarkdown,
    PAGES: PAGES,
    mount: mount,
    rootPrefix: rootPrefix,
    currentTheme: currentTheme,
    applyTheme: applyTheme,
    fetchFirst: fetchFirst,
    docsUrls: docsUrls,
    escapeHtml: escapeHtml,
    extractMermaid: extractMermaid,
    sectionBetween: sectionBetween,
    renderMermaidInto: renderMermaidInto,
    markedParse: markedParse,
    renderMarkdownInto: renderMarkdownInto,
    rewriteDocLinks: rewriteDocLinks,
    renderMath: renderMath,
    tocFrom: tocFrom,
    ensureMermaid: ensureMermaid,
  };
})(window);
