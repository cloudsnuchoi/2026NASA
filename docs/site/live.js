/* Live status panel (docs/status/live.json) for dashboard + roadmap. No build step.
 * Usage: <section id="live-status"></section> + FieldShiftLive.mount("live-status").
 * Data comes from FieldShiftSite.onLive (fetched no-store every 60 s by site.js). */
(function (global) {
  "use strict";

  const esc = function (s) { return global.FieldShiftSite.escapeHtml(s == null ? "" : s); };
  const ICON = { done: "✅", progress: "🟡", blocked: "🔴" };
  const arr = function (v) { return Array.isArray(v) ? v : []; };

  function fmtKST(iso) {
    const d = new Date(iso);
    if (!iso || isNaN(d)) return "미확인";
    return new Intl.DateTimeFormat("ko-KR", {
      timeZone: "Asia/Seoul", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", hour12: false,
    }).format(d) + " KST";
  }

  function remainingText(data) {
    let min = null;
    const dl = new Date(data.deadline);
    if (data.deadline && !isNaN(dl)) min = Math.floor((dl - Date.now()) / 60000);
    else if (typeof data.remaining_min === "number") min = data.remaining_min;
    if (min == null) return "미확인";
    if (min <= 0) return "마감 지남";
    return Math.floor(min / 60) + "시간 " + (min % 60) + "분";
  }

  function pctOf(v) {
    const n = Number(v);
    return isFinite(n) ? Math.max(0, Math.min(100, Math.round(n))) : 0;
  }

  function list(items, fn, emptyText) {
    items = arr(items);
    if (!items.length) return '<p class="empty">' + (emptyText || "없음") + "</p>";
    return "<ul class=\"live-list\">" + items.map(function (x) { return "<li>" + fn(x) + "</li>"; }).join("") + "</ul>";
  }

  function laneHtml(lane, prevOpen) {
    const items = arr(lane.items);
    const p = pctOf(lane.pct);
    const counts = { done: 0, progress: 0, blocked: 0 };
    items.forEach(function (it) { if (counts[it.status] != null) counts[it.status]++; });
    const rows = items.map(function (it) {
      return '<li class="live-item s-' + esc(it.status) + '"><span class="ico" aria-hidden="true">' +
        (ICON[it.status] || "⚪") + "</span><span><strong>" + esc(it.label) + "</strong>" +
        (it.detail ? ' <span class="muted">' + esc(it.detail) + "</span>" : "") + "</span></li>";
    }).join("");
    const key = String(lane.id || lane.name || "");
    const open = key in prevOpen ? prevOpen[key] : counts.blocked > 0;
    return '<details class="live-lane" data-lane="' + esc(key) + '"' + (open ? " open" : "") + ">" +
      "<summary><span class=\"lane-name\">" + esc(lane.name || lane.id) + "</span>" +
      '<span class="bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="' + p + '"><span style="width:' + p + '%"></span></span>' +
      '<span class="pct">' + p + "%</span>" +
      '<span class="lane-counts muted">✅' + counts.done + " 🟡" + counts.progress + " 🔴" + counts.blocked + "</span></summary>" +
      (rows ? '<ul class="live-items">' + rows + "</ul>" : '<p class="empty">항목 없음</p>') +
      "</details>";
  }

  function render(host, data, err) {
    if (!data) {
      host.innerHTML = '<div class="card live-card"><h2>라이브 현황 (live.json)</h2>' +
        '<p class="empty live-missing">현황 파일 없음</p>' +
        '<p class="muted">docs/status/live.json을 읽지 못했습니다' + (err ? " (" + esc(err) + ")" : "") + ". 60초마다 다시 시도합니다.</p></div>";
      return;
    }
    /* keep expand/collapse state across 60 s re-renders */
    const prevOpen = {};
    host.querySelectorAll("details.live-lane").forEach(function (d) { prevOpen[d.dataset.lane] = d.open; });
    const stale = data.generated_at && (Date.now() - new Date(data.generated_at)) > 15 * 60000;
    host.innerHTML =
      '<div class="card live-card">' +
        '<div class="live-head"><h2>라이브 현황 (live.json)</h2>' +
          '<div class="stat-row">' +
            '<div class="stat"><div class="n live-remaining">' + esc(remainingText(data)) + '</div><div class="l">마감까지 · ' + esc(fmtKST(data.deadline)) + "</div></div>" +
            '<div class="stat"><div class="n live-gen">' + esc(fmtKST(data.generated_at)) + '</div><div class="l">생성 시각' + (stale ? ' · <span class="stale-flag warn">15분 넘게 갱신 없음</span>' : "") + "</div></div>" +
          "</div></div>" +
        '<h3>레인별 진행률</h3><div class="live-lanes">' + (arr(data.lanes).map(function (l) { return laneHtml(l, prevOpen); }).join("") || '<p class="empty">레인 정보 없음</p>') + "</div>" +
        '<div class="live-grid">' +
          '<section><h3>🔴 막힌 점</h3>' + list(data.blockers, esc, "막힌 점 없음") + "</section>" +
          '<section><h3>다음 3가지</h3>' + list(arr(data.next).slice(0, 3), esc, "미정") + "</section>" +
          '<section><h3>최근 머지된 PR</h3>' + list(data.merged_prs, function (pr) {
            return '<a href="https://github.com/cloudsnuchoi/2026NASA/pull/' + esc(pr.number) + '" target="_blank" rel="noopener">#' +
              esc(pr.number) + "</a> " + esc(pr.title) + (pr.merged_at ? ' <span class="muted">' + esc(fmtKST(pr.merged_at)) + "</span>" : "");
          }, "없음") + "</section>" +
          '<section><h3>AI 모델 상태</h3>' + list(data.ai_models, function (m) {
            return "<strong>" + esc(m.name) + '</strong> <span class="tag">' + esc(m.status || "미확인") + "</span>" +
              (m.detail ? ' <span class="muted">' + esc(m.detail) + "</span>" : "");
          }, "정보 없음") + "</section>" +
        "</div>" +
        '<div class="live-grid">' +
          '<section><h3>tmux 에이전트 레인</h3><div class="table-wrap"><table><thead><tr><th>이름</th><th>모델</th><th>작업</th><th>마지막 활동</th></tr></thead><tbody>' +
            (arr(data.tmux).map(function (t) {
              return "<tr><td><code>" + esc(t.name) + "</code></td><td>" + esc(t.model) + "</td><td>" + esc(t.task) + "</td><td>" + esc(t.last_activity || "—") + "</td></tr>";
            }).join("") || '<tr><td colspan="4" class="empty">없음</td></tr>') + "</tbody></table></div></section>" +
          '<section><h3>팀원 마지막 활동</h3><div class="table-wrap"><table><thead><tr><th>이름</th><th>Mattermost</th><th>저장소</th></tr></thead><tbody>' +
            (arr(data.people).map(function (p) {
              return "<tr><td>" + esc(p.name) + (p.user ? ' <span class="muted">@' + esc(p.user) + "</span>" : "") + "</td><td>" +
                esc(p.mattermost_last || "—") + "</td><td>" + esc(p.repo_last || "—") + "</td></tr>";
            }).join("") || '<tr><td colspan="3" class="empty">없음</td></tr>') + "</tbody></table></div></section>" +
        "</div>" +
      "</div>";
  }

  function mount(id) {
    const host = document.getElementById(id);
    if (!host) return;
    host.classList.add("live-status");
    host.innerHTML = '<div class="card live-card"><p class="empty">라이브 현황 불러오는 중…</p></div>';
    let last = null;
    global.FieldShiftSite.onLive(function (data, err) { last = data; render(host, data, err); });
    /* keep the countdown text fresh between fetches */
    setInterval(function () {
      const el = host.querySelector(".live-remaining");
      if (el && last) el.textContent = remainingText(last);
    }, 30000);
  }

  global.FieldShiftLive = { mount: mount, render: render };
})(window);
