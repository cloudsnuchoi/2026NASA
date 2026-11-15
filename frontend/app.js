/* ART FARM — Field Shift: Adapting Farms with NASA Data
 * Flow: Story → Map → Crops → Loading → Results
 * Tier 1 (anywhere): POST /api/quick  — FAO-56 engine ported from team MATLAB prototype V8 (screening estimate)
 * Tier 2 (polygon overlaps a pilot demo field): /api/simulate, /api/field/{id}/profile, /api/validation/backtest, /api/explain
 */
(() => {
  "use strict";
  const API = (window.ARTFARM_API || "/api").replace(/\/$/, "");
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmt = (v, d = 0) => (v === null || v === undefined || Number.isNaN(v) ? "—" : Number(v).toLocaleString("en-US", { maximumFractionDigits: d, minimumFractionDigits: d }));
  const GAP = '<span class="text-slate-400 italic">information gap</span>';
  const REL_TIP = "Relative index vs strategy A (current practice), not a guarantee. Range shown is P10–P90.";

  const COUNTY = { "19169": "Story County, IA", "17113": "McLean County, IL", "31109": "Lancaster County, NE", "39159": "Union County, OH" };
  const CROPS = [
    { id: "Corn", img: "assets/img10.jpg", note: "C4 cereal · FAO-56 Kc mid 1.20" },
    { id: "Soy", img: "assets/img11.jpg", note: "Legume · FAO-56 Kc mid 1.15" },
    { id: "Wheat", img: "assets/img12.jpg", note: "Small grain · FAO-56 Kc mid 1.15" },
  ];
  const COLORS = {
    user: { color: "#f7f6f0", weight: 2.5, fillColor: "#7dd3a8", fillOpacity: 0.38 },
    demo: { color: "#f2c46d", weight: 2, dashArray: "6 5", fillColor: "#f2c46d", fillOpacity: 0.14 },
    demoHit: { color: "#f2c46d", weight: 3, dashArray: null, fillColor: "#f2c46d", fillOpacity: 0.3 },
  };

  const state = { vertices: [], preset: null, crops: [], fields: [], hitField: null, quick: null, sim: null };

  // ------------------------------------------------------------------ helpers
  function toast(msg, ms = 2600) {
    $("#toast-msg").textContent = msg;
    const t = $("#toast");
    t.classList.add("show");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => t.classList.remove("show"), ms);
  }
  async function api(path, opts = {}) {
    const r = await fetch(API + path, {
      method: opts.body ? "POST" : "GET",
      headers: opts.body ? { "content-type": "application/json" } : {},
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    });
    const txt = await r.text();
    let j = null;
    try { j = JSON.parse(txt); } catch { /* not json */ }
    if (!r.ok) throw new Error((j && (j.detail || j.error?.message)) || `HTTP ${r.status}`);
    return j;
  }
  function show(id) {
    $$(".app-page").forEach((p) => p.classList.toggle("active", p.id === id));
    window.scrollTo({ top: 0 });
    if (id === "page-map") initMap();
    history.replaceState(null, "", "#" + id.replace("page-", ""));
  }
  document.addEventListener("click", (e) => {
    const g = e.target.closest("[data-goto]");
    if (g) show(g.dataset.goto);
  });
  $("#btn-skip-to-map")?.addEventListener("click", () => show("page-map"));
  $("#btn-start-location")?.addEventListener("click", () => show("page-map"));

  // story reveal
  const io = new IntersectionObserver((es) => es.forEach((x) => x.isIntersecting && x.target.classList.add("in-view")), { threshold: 0.18 });
  $$(".story-block").forEach((b) => io.observe(b));

  // ------------------------------------------------------------------ geometry (same method as V8 / model_api.quick)
  function metrics(pts) {
    if (pts.length < 3) return null;
    const a = 6378137.0, f = 1 / 298.257223563, e2 = f * (2 - f);
    const lon0 = pts.reduce((s, p) => s + p[0], 0) / pts.length;
    const lat0d = pts.reduce((s, p) => s + p[1], 0) / pts.length;
    const lat0 = (lat0d * Math.PI) / 180;
    const den = Math.sqrt(1 - e2 * Math.sin(lat0) ** 2);
    const mlat = ((a * (1 - e2)) / den ** 3) * (Math.PI / 180);
    const mlon = (a / den) * Math.cos(lat0) * (Math.PI / 180);
    const xy = pts.map(([lo, la]) => [(lo - lon0) * mlon, (la - lat0d) * mlat]);
    let A = 0, P = 0;
    for (let i = 0; i < xy.length; i++) {
      const [x0, y0] = xy[i], [x1, y1] = xy[(i + 1) % xy.length];
      A += x0 * y1 - x1 * y0;
      P += Math.hypot(x1 - x0, y1 - y0);
    }
    return { area_ha: Math.abs(A) / 2 / 1e4, perimeter_km: P / 1000 };
  }
  function pip([x, y], ring) {
    let ins = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [xi, yi] = ring[i], [xj, yj] = ring[j];
      if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) ins = !ins;
    }
    return ins;
  }
  function segX(p1, p2, p3, p4) {
    const d = (a, b, c) => (c[0] - a[0]) * (b[1] - a[1]) - (b[0] - a[0]) * (c[1] - a[1]);
    const d1 = d(p3, p4, p1), d2 = d(p3, p4, p2), d3 = d(p1, p2, p3), d4 = d(p1, p2, p4);
    return d1 * d2 < 0 && d3 * d4 < 0;
  }
  function intersects(a, b) {
    if (a.some((p) => pip(p, b)) || b.some((p) => pip(p, a))) return true;
    for (let i = 0; i < a.length; i++) for (let j = 0; j < b.length; j++) if (segX(a[i], a[(i + 1) % a.length], b[j], b[(j + 1) % b.length])) return true;
    return false;
  }
  const inCornBelt = ([lo, la]) => la >= 36 && la <= 48 && lo >= -104 && lo <= -80;

  // ------------------------------------------------------------------ map
  let map, userLayer, vertexLayer, demoLayers = {};
  function initMap() {
    if (map) { setTimeout(() => map.invalidateSize(), 50); return; }
    map = L.map("map", { zoomControl: true, worldCopyJump: false }).setView([41.0, -90.3], 6);
    window.__artfarmMap = map;
    L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
      maxZoom: 19,
      attribution: "Imagery © Esri, Maxar, Earthstar Geographics, and the GIS User Community",
    }).addTo(map);
    L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}", {
      maxZoom: 19, opacity: 0.85, attribution: "Labels © Esri",
    }).addTo(map);
    vertexLayer = L.layerGroup().addTo(map);
    map.on("click", (e) => addVertex([e.latlng.lng, e.latlng.lat]));
    loadDemoFields();
    setTimeout(() => map.invalidateSize(), 80);
  }
  async function loadDemoFields() {
    try {
      const fc = await api("/fields-geo");
      state.fields = fc.fields || [];
      for (const f of state.fields) {
        const lyr = L.polygon(f.ring.map(([lo, la]) => [la, lo]), COLORS.demo).addTo(map);
        lyr.bindTooltip(`Pilot demo field · ${COUNTY[f.county_fips] || f.county_fips} · ${fmt(f.area_ha, 1)} ha`);
        lyr.on("click", (e) => { L.DomEvent.stopPropagation(e); usePresetField(f); });
        demoLayers[f.field_id] = lyr;
      }
      for (const fips of Object.keys(COUNTY)) {
        const f = state.fields.find((x) => x.county_fips === fips);
        if (!f) continue;
        const c = f.ring.reduce((a, p) => [a[0] + p[0] / f.ring.length, a[1] + p[1] / f.ring.length], [0, 0]);
        L.circleMarker([c[1], c[0]], { radius: 8, color: "#173a2b", weight: 2, fillColor: "#f2c46d", fillOpacity: 1 })
          .bindTooltip(`Pilot · ${COUNTY[fips]}`, { permanent: true, direction: "right", className: "vtx-label" })
          .on("click", (e) => { L.DomEvent.stopPropagation(e); usePresetField(f); })
          .addTo(map);
      }
    } catch (e) {
      toast("Pilot field outlines unavailable: " + e.message);
    }
  }
  function addVertex(p) {
    if (state.preset) { state.vertices = []; state.preset = null; }
    if (state.vertices.length >= 4) { toast("4 corners placed — Undo or Clear to redraw."); return; }
    if (!inCornBelt(p)) { toast("Outside the US Corn Belt screening area (36–48°N, 80–104°W)."); return; }
    state.vertices.push(p);
    redraw();
  }
  function usePresetField(f) {
    state.vertices = f.ring.slice();
    state.preset = f;
    redraw();
    map.fitBounds(L.polygon(f.ring.map(([lo, la]) => [la, lo])).getBounds(), { padding: [60, 60], maxZoom: 16 });
  }
  function redraw() {
    vertexLayer.clearLayers();
    if (userLayer) { map.removeLayer(userLayer); userLayer = null; }
    const v = state.vertices;
    if (!state.preset) v.forEach((p, i) => L.circleMarker([p[1], p[0]], { radius: 6, color: "#173a2b", weight: 2, fillColor: "#f7f6f0", fillOpacity: 1 })
      .bindTooltip(String(i + 1), { permanent: true, direction: "top", className: "vtx-label" }).addTo(vertexLayer));
    if (v.length >= 2) userLayer = (v.length >= 3 ? L.polygon : L.polyline)(v.map(([lo, la]) => [la, lo]), COLORS.user).addTo(map);
    const m = metrics(v);
    $("#m-vertices").textContent = state.preset ? `preset (${v.length} vertices)` : `${v.length} / 4`;
    $("#m-area").textContent = m ? `${fmt(m.area_ha, 2)} ha (${fmt(m.area_ha * 2.47105, 1)} ac)` : "—";
    $("#m-perim").textContent = m ? `${fmt(m.perimeter_km, 3)} km` : "—";
    state.hitField = null;
    Object.values(demoLayers).forEach((l) => l.setStyle(COLORS.demo));
    if (v.length >= 3) {
      state.hitField = state.preset || state.fields.find((f) => intersects(v, f.ring)) || null;
      if (state.hitField && demoLayers[state.hitField.field_id]) demoLayers[state.hitField.field_id].setStyle(COLORS.demoHit);
    }
    const ready = state.preset ? true : v.length === 4;
    $("#m-tier").textContent = !ready ? "—" : state.hitField ? "Quick Screen + Deep Analysis" : "Quick Screen";
    $("#m-tier-note").textContent = !ready ? "" : state.hitField
      ? `Overlaps pilot field ${state.hitField.field_id} (${COUNTY[state.hitField.county_fips] || ""}) — engine strategies A–D will be shown.`
      : "Deep analysis available in 4 pilot counties (Story IA, McLean IL, Lancaster NE, Union OH).";
    $("#btn-to-crops").disabled = !ready;
  }
  $("#btn-undo").addEventListener("click", () => { if (state.preset) state.vertices = []; else state.vertices.pop(); state.preset = null; redraw(); });
  $("#btn-clear").addEventListener("click", () => { state.vertices = []; state.preset = null; redraw(); });
  $$("[data-preset]").forEach((b) => b.addEventListener("click", () => {
    const f = state.fields.find((x) => x.county_fips === b.dataset.preset);
    if (!f) { toast("Pilot fields still loading…"); return; }
    usePresetField(f);
  }));
  $("#btn-to-crops").addEventListener("click", () => show("page-crops"));

  // ------------------------------------------------------------------ crops
  $("#crop-grid").innerHTML = CROPS.map((c) => `
    <button data-crop="${c.id}" class="crop-card group text-left rounded-3xl overflow-hidden bg-white shadow border-2 border-transparent transition">
      <div class="h-40 overflow-hidden"><img src="${c.img}" alt="${c.id} field" class="w-full h-full object-cover group-hover:scale-105 transition" /></div>
      <div class="p-4 flex items-center justify-between"><div><div class="text-lg font-extrabold text-[#173a2b]">${c.id === "Soy" ? "Soybean" : c.id}</div>
      <div class="text-[11px] text-slate-500">${c.note}</div></div><span class="crop-check w-7 h-7 rounded-full border-2 border-slate-300 flex items-center justify-center text-white font-bold">✓</span></div>
    </button>`).join("");
  $$("[data-crop]").forEach((b) => b.addEventListener("click", () => {
    const id = b.dataset.crop, i = state.crops.indexOf(id);
    if (i >= 0) state.crops.splice(i, 1); else state.crops.push(id);
    $$("[data-crop]").forEach((x) => x.classList.toggle("selected", state.crops.includes(x.dataset.crop)));
    $("#crop-selected").textContent = state.crops.length ? state.crops.map((c) => (c === "Soy" ? "Soybean" : c)).join(" · ") : "none";
    $("#btn-run").disabled = state.crops.length < 2;
  }));

  // ------------------------------------------------------------------ loading (sunflower)
  (function initSunflower() {
    const g = $("#sunflower-petals"), seeds = $("#sunflower-seeds"), ns = "http://www.w3.org/2000/svg";
    if (!g) return;
    for (let layer = 0; layer < 2; layer++) {
      const off = layer ? 360 / 32 : 0;
      for (let i = 0; i < 16; i++) {
        const w = document.createElementNS(ns, "g");
        w.setAttribute("transform", `rotate(${(360 / 16) * i + off})`);
        const p = document.createElementNS(ns, "path");
        p.setAttribute("d", layer ? "M 0,-30 C 8,-44 7,-64 0,-78 C -7,-64 -8,-44 0,-30 Z" : "M 0,-30 C 10,-46 9,-70 0,-88 C -9,-70 -10,-46 0,-30 Z");
        p.setAttribute("fill", layer ? "#f59e0b" : "#facc15");
        p.setAttribute("stroke", layer ? "#d97706" : "#eab308");
        p.setAttribute("class", "sunflower-petal");
        p.style.animationDelay = `${(((i + layer * 0.5) / 16) * 1.6).toFixed(2)}s`;
        w.appendChild(p); g.appendChild(w);
      }
    }
    for (let i = 0; i < 60; i++) {
      const r = 2.6 * Math.sqrt(i), t = i * 2.39996;
      const c = document.createElementNS(ns, "circle");
      c.setAttribute("cx", (r * Math.cos(t)).toFixed(2)); c.setAttribute("cy", (r * Math.sin(t)).toFixed(2));
      c.setAttribute("r", "1.3"); c.setAttribute("fill", "#d9a441"); seeds.appendChild(c);
    }
  })();

  // ------------------------------------------------------------------ run
  $("#btn-run").addEventListener("click", run);
  async function run() {
    show("page-loading");
    const status = $("#loading-status");
    const msgs = ["Querying USGS 3DEP elevation…", "Downloading NASA POWER 10-year daily weather…", "Reading NWS forecast and Open-Meteo climate ranges…", "Running FAO-56 water balance per crop…"];
    let k = 0; status.textContent = msgs[0];
    const tick = setInterval(() => { k = (k + 1) % msgs.length; status.textContent = msgs[k]; }, 1500);
    const poly = state.vertices.length > 60 ? simplify(state.vertices, 60) : state.vertices;
    const pQuick = api("/quick", { body: { polygon: poly, crops: state.crops } }).catch((e) => ({ __error: e.message }));
    const fid = state.hitField?.field_id;
    const pDeep = fid ? Promise.all([
      api("/simulate", { body: { field_id: fid, n: 500, seed: 42 } }),
      api(`/field/${fid}/profile`),
      api(`/validation/backtest?field_id=${fid}&year=2012`).catch(() => null),
    ]).catch((e) => ({ __error: e.message })) : Promise.resolve(null);
    const [q, d] = await Promise.all([pQuick, pDeep]);
    clearInterval(tick);
    state.quick = q;
    renderTier2(d, fid);
    renderTier1(q);
    show("page-results");
  }
  function simplify(pts, n) { const s = Math.ceil(pts.length / n); return pts.filter((_, i) => i % s === 0); }

  // ------------------------------------------------------------------ Tier 2 (engine)
  const PCT = (o) => (!o || o.p50 === null || o.p50 === undefined ? GAP
    : `<span title="${REL_TIP}" class="underline decoration-dotted cursor-help">${o.p50 > 0 ? "+" : ""}${fmt(o.p50, 0)}%</span> <span class="text-[10px] text-slate-500">(P10–P90 ${fmt(o.p10, 0)} to ${fmt(o.p90, 0)})</span>`);
  function matches(code) {
    const c = new Set(state.crops);
    if (code === "D") return false;
    if (code === "A" || code === "B") return c.has("Corn") && c.has("Soy");
    if (code === "C") return c.has("Wheat");
    return false;
  }
  let chart;
  function renderTier2(d, fid) {
    const el = $("#tier2");
    if (!fid) {
      el.innerHTML = `<div class="rounded-2xl bg-white border border-amber-300 p-4 text-sm text-slate-700">🔎 <strong>Deep analysis available in 4 pilot counties</strong> — Story IA, McLean IL, Lancaster NE, Union OH. Your field is outside the 20 demo fields, so only the Quick Screen below is shown. Use a preset on the map to see strategies A–D.</div>`;
      return;
    }
    if (!d || d.__error) { el.innerHTML = `<div class="rounded-2xl bg-white border border-red-300 p-4 text-sm">Deep analysis engine unavailable (${esc(d?.__error)}). Information gap.</div>`; return; }
    const [sim, prof, bt] = d;
    state.sim = sim;
    const strat = [...sim.strategies].sort((a, b) => a.strategy_code.localeCompare(b.strategy_code));
    const btBy = Object.fromEntries((bt?.results || []).map((r) => [r.strategy_code, r]));
    const cdl = (prof.cdl_history || []).slice().sort((a, b) => b.year - a.year).slice(0, 8);
    const v = prof.vision || {};
    const cards = strat.map((s) => {
      const hl = matches(s.strategy_code), ref = s.strategy_code === "D";
      const m = s.metrics || {};
      const wd = m.season_water_deficit_mm || {};
      const b12 = btBy[s.strategy_code]?.metrics;
      return `<article class="rounded-3xl bg-white shadow p-5 border-2 ${hl ? "border-[#82c341] ring-4 ring-[#82c341]/20" : "border-slate-200"} flex flex-col">
        <div class="flex items-start justify-between gap-2 mb-2">
          <div><div class="text-xs font-bold text-slate-500">Strategy ${esc(s.strategy_code)} · ${esc(s.sequence)}</div>
          <h3 class="text-lg font-extrabold text-[#173a2b] leading-tight">${esc(s.label)}</h3>
          <div class="text-[11px] text-slate-500">${esc(s.goal_label || "")}</div></div>
          ${hl ? '<span class="shrink-0 px-2 py-0.5 rounded-full bg-[#82c341]/20 text-[#2f6b1d] text-[10px] font-extrabold">matches your crops</span>' : ""}
          ${ref ? '<span class="shrink-0 px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 text-[10px] font-extrabold">reference</span>' : ""}
        </div>
        <p class="text-xs text-slate-600 mb-3"><strong>Why:</strong> ${esc(s.why)}</p>
        <div class="grid grid-cols-2 gap-2 text-xs mb-3">
          <div class="rounded-xl bg-slate-50 p-2"><div class="text-slate-500">Season water deficit P50</div><strong>${fmt(wd.p50)} mm/yr</strong><div class="text-[10px] text-slate-500">P10–P90 ${fmt(wd.p10)}–${fmt(wd.p90)} · CVaR<sub>10%</sub> ${fmt(wd.cvar)}</div></div>
          <div class="rounded-xl bg-slate-50 p-2"><div class="text-slate-500">2012 drought backtest</div><strong>${b12 ? fmt(b12.season_water_deficit_mm) + " mm deficit" : GAP}</strong><div class="text-[10px] text-slate-500">${b12 ? fmt(b12.stress_days) + " stress days" : ""}</div></div>
          <div class="rounded-xl bg-slate-50 p-2"><div class="text-slate-500">Winter bare days P50</div><strong>${fmt(m.winter_bare_days?.p50)}</strong></div>
          <div class="rounded-xl bg-slate-50 p-2"><div class="text-slate-500">Water use vs A</div>${PCT(s.display?.water_use_pct)}</div>
        </div>
        <div class="text-xs space-y-2 flex-1">
          <div><div class="font-bold text-emerald-800">Benefits</div><ul class="list-disc ml-4 text-slate-700">${(s.benefits || []).map((x) => `<li>${esc(x)}</li>`).join("") || `<li>${GAP}</li>`}</ul></div>
          <div><div class="font-bold text-amber-800">Trade-offs</div><ul class="list-disc ml-4 text-slate-700">${(s.cons || []).map((x) => `<li>${esc(x)}</li>`).join("") || "<li>none listed</li>"}</ul></div>
          <div><div class="font-bold text-slate-700">Evidence</div><ul class="ml-1 text-slate-600">${(s.evidence || []).map((x) => `<li>• ${x.url ? `<a class="underline" target="_blank" rel="noopener" href="${esc(x.url)}">${esc(x.quote || x.url)}</a>` : esc(x.quote || "")}${x.doi ? ` (doi:${esc(x.doi)})` : ""}</li>`).join("")}</ul></div>
          <div><div class="font-bold text-slate-700">Information gaps</div><ul class="list-disc ml-4 text-slate-500">${(s.info_gaps || []).map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>
          <div><div class="font-bold text-red-800">Check locally</div><ul class="list-disc ml-4 text-slate-700">${(s.local_review_risks || []).map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>
        </div>
        <button data-explain="${esc(s.strategy_code)}" class="mt-3 px-3 py-2 rounded-xl bg-[#173a2b] text-white text-xs font-bold hover:bg-[#24543e]">Explain this strategy (AI, numbers from engine only)</button>
        <div class="explain-out mt-2 text-xs text-slate-700 whitespace-pre-wrap"></div>
      </article>`;
    }).join("");
    const risks = [...new Set(strat.flatMap((s) => s.local_review_risks || []))];
    el.innerHTML = `
      <div class="rounded-3xl bg-[#173a2b] text-white p-6 shadow-xl mb-5">
        <div class="text-xs font-bold uppercase tracking-widest text-amber-300">Tier 2 · Deep Analysis · pilot field ${esc(fid)}</div>
        <h2 class="text-2xl font-extrabold mt-1">${esc(prof.region_label || COUNTY[prof.county_fips] || "")} · ${fmt(prof.area_ha, 1)} ha · current rotation ${esc(prof.current_rotation || "—")}</h2>
        <p class="text-xs text-emerald-100/80 mt-1">Monte Carlo water balance, n=${esc(sim.n)}, seed=${esc(sim.seed)}, run ${esc(sim.run_id)} · ${esc(sim.cvar_definition)} · Strategies are not ranked; highlighted cards match your selected crops (D = reference).</p>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3 mt-4 text-xs">
          <div class="rounded-2xl bg-white/10 p-3"><div class="text-amber-200 font-bold">Prithvi-EO crop map (vision)</div>
            <div>Predicted: <strong>${esc(v.crop_pred || "—")}</strong> · bare fraction ${fmt(v.bare_fraction, 2)}</div>
            <div>Agreement with USDA CDL: <strong>${v.agreement_with_cdl != null ? fmt(v.agreement_with_cdl * 100, 0) + "%" : "—"}</strong></div>
            <div class="text-[10px] text-emerald-100/60 break-all">${esc(v.model_id || "")}</div></div>
          <div class="rounded-2xl bg-white/10 p-3"><div class="text-amber-200 font-bold">USDA CDL history</div>
            <div class="flex flex-wrap gap-1 mt-1">${cdl.map((c) => `<span class="px-1.5 py-0.5 rounded bg-white/15">${c.year}: ${esc(c.crop)}</span>`).join("")}</div></div>
          <div class="rounded-2xl bg-white/10 p-3"><div class="text-amber-200 font-bold">Field context</div>
            <div>Soil OM ${fmt(prof.soil?.om_pct, 1)}% · AWC ${fmt(prof.soil?.awc_cm_cm, 2)} cm/cm · ${esc(prof.soil?.drainagecl || "")}</div>
            <div>Precip ${fmt(prof.precip_mm_yr)} mm/yr · NDVI peak ${fmt(prof.ndvi_peak, 2)}</div>
            <div class="text-[10px] text-emerald-100/60">${esc(prof.disclaimer || "")}</div></div>
        </div>
      </div>
      <div class="rounded-3xl bg-white shadow p-5 mb-5">
        <div class="flex flex-wrap justify-between items-baseline gap-2"><h3 class="font-extrabold text-[#173a2b]">Season water deficit — possible range (P10–P90) and CVaR<sub>10%</sub></h3>
        <span class="text-[11px] text-slate-500">mm/yr · bar = P10–P90, line = P50, ◆ = CVaR (mean of worst 10%), ● = 2012 backtest</span></div>
        <div class="h-64"><canvas id="dist-chart"></canvas></div>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-5">${cards}</div>
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div class="rounded-3xl bg-white shadow p-5"><h3 class="font-extrabold text-[#173a2b] mb-2">Information gaps</h3>
          <ul class="list-disc ml-5 text-xs text-slate-600">${[...(prof.info_gaps || []), ...(sim.info_gaps || [])].map((x) => `<li>${esc(typeof x === "string" ? x : x.message || x.item || JSON.stringify(x))}</li>`).join("")}</ul></div>
        <div class="rounded-3xl bg-amber-50 border border-amber-300 shadow p-5"><h3 class="font-extrabold text-[#173a2b] mb-1">S7 · Human judgement checklist</h3>
          <p class="text-[11px] text-slate-600 mb-2">ART FARM does not replace your judgement. Before acting, check these with your agronomist or extension office:</p>
          <ul class="text-xs space-y-1">${risks.map((r) => `<li><label class="flex gap-2"><input type="checkbox" class="mt-0.5"> <span>${esc(r)}</span></label></li>`).join("")}
          <li><label class="flex gap-2"><input type="checkbox" class="mt-0.5"> <span>In-field soil test (not provided by this tool)</span></label></li></ul>
          <p class="text-[10px] text-slate-500 mt-2">${esc(sim.disclaimer || "")}</p></div>
      </div>`;
    drawChart(strat, btBy);
    $$("[data-explain]").forEach((b) => b.addEventListener("click", () => explain(b, fid)));
  }
  function drawChart(strat, btBy) {
    if (chart) chart.destroy();
    const labels = strat.map((s) => `${s.strategy_code} · ${s.sequence}`);
    const wd = strat.map((s) => s.metrics?.season_water_deficit_mm || {});
    chart = new Chart($("#dist-chart"), {
      data: {
        labels,
        datasets: [
          { type: "bar", label: "P10–P90", data: wd.map((w) => [w.p10, w.p90]), backgroundColor: strat.map((s) => (matches(s.strategy_code) ? "rgba(130,195,65,.55)" : "rgba(36,84,62,.25)")), borderColor: "#24543e", borderWidth: 1, borderSkipped: false, barPercentage: 0.5 },
          { type: "scatter", label: "P50", data: wd.map((w, i) => ({ x: labels[i], y: w.p50 })), pointStyle: "line", pointRadius: 18, borderWidth: 3, borderColor: "#173a2b" },
          { type: "scatter", label: "CVaR 10%", data: wd.map((w, i) => ({ x: labels[i], y: w.cvar })), pointStyle: "rectRot", pointRadius: 6, backgroundColor: "#d97706" },
          { type: "scatter", label: "2012 backtest", data: strat.map((s, i) => ({ x: labels[i], y: btBy[s.strategy_code]?.metrics?.season_water_deficit_mm ?? null })), pointRadius: 6, backgroundColor: "#b91c1c" },
        ],
      },
      options: { maintainAspectRatio: false, scales: { y: { title: { display: true, text: "mm/yr" }, beginAtZero: true } }, plugins: { legend: { position: "bottom" } } },
    });
  }
  async function explain(btn, fid) {
    const out = btn.nextElementSibling, code = btn.dataset.explain;
    btn.disabled = true; out.textContent = "Asking the explainer (numbers come only from engine tool calls)…";
    try {
      const r = await api("/explain", { body: { field_id: fid, strategy_code: code, lang: "en", question: `Why might strategy ${code} fit or not fit this field, and what should I check locally?` } });
      out.textContent = (r.answer || "").replace(/\*\*/g, "") + (r.insufficient_evidence ? "\n[insufficient evidence in the library]" : "") + "\n— AI-generated explanation (SI); verify locally.";
    } catch (e) { out.textContent = "Explanation unavailable: " + e.message; }
    btn.disabled = false;
  }

  // ------------------------------------------------------------------ Tier 1 (quick screen)
  const dist = (o, u = "") => (!o ? GAP : `<strong>${fmt(o.p50)}</strong>${u} <span class="text-[10px] text-slate-500">P10–P90 ${fmt(o.p10)}–${fmt(o.p90)}</span>`);
  function renderTier1(q) {
    const el = $("#tier1");
    if (!q || q.__error) {
      el.innerHTML = `<div class="rounded-2xl bg-white border border-red-300 p-4 text-sm">Quick Screen unavailable (${esc(q?.__error)}). Information gap — no fallback values are shown.</div>`;
      return;
    }
    const g = q.geometry || {}, ch = q.climate_history, fc = q.forecast_anomaly, pj = q.climate_projection;
    const name = (c) => (c === "Soy" ? "Soybean" : c);
    el.innerHTML = `
      <div class="rounded-3xl bg-white shadow p-6 mb-5 border-l-8 border-[#82c341]">
        <div class="flex flex-wrap items-baseline justify-between gap-2">
          <div><div class="text-xs font-bold uppercase tracking-widest text-[#5a9e2e]">Tier 1 · Quick Screen</div>
          <h2 class="text-2xl font-extrabold text-[#173a2b]">${esc(q.engine)}</h2></div>
          <span class="px-3 py-1 rounded-full bg-amber-100 text-amber-900 text-xs font-extrabold uppercase">${esc(q.label)}</span>
        </div>
        <div class="grid grid-cols-2 md:grid-cols-5 gap-3 mt-4 text-sm">
          <div class="rounded-xl bg-[#f3f5ee] p-3"><div class="text-[11px] text-slate-500">Area (WGS84)</div><strong>${fmt(g.area_ha, 2)} ha</strong></div>
          <div class="rounded-xl bg-[#f3f5ee] p-3"><div class="text-[11px] text-slate-500">Perimeter</div><strong>${fmt(g.perimeter_km, 3)} km</strong></div>
          <div class="rounded-xl bg-[#f3f5ee] p-3"><div class="text-[11px] text-slate-500">Elevation (USGS 3DEP, centroid)</div><strong>${q.elevation ? fmt(q.elevation.value_m, 1) + " m" : GAP}</strong></div>
          <div class="rounded-xl bg-[#f3f5ee] p-3"><div class="text-[11px] text-slate-500">Mean temp ${ch ? esc(ch.period) : ""} (NASA POWER)</div>${ch ? dist(ch.mean?.t2m_c, " °C") : GAP}</div>
          <div class="rounded-xl bg-[#f3f5ee] p-3"><div class="text-[11px] text-slate-500">Annual precip / ET₀ (NASA POWER)</div>${ch ? `${dist(ch.mean?.precip_mm, " mm")}<br>${dist(ch.mean?.et0_mm, " mm")}` : GAP}</div>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3 text-xs">
          <div class="rounded-xl border border-slate-200 p-3"><div class="font-bold text-[#173a2b]">NWS 7-day forecast anomaly</div>${fc && fc.anomaly_c != null ? `<strong>${fc.anomaly_c > 0 ? "+" : ""}${fmt(fc.anomaly_c, 1)} °C</strong> vs ${esc(fc.baseline)}<div class="text-[10px] text-slate-500">${esc(fc.note)}</div>` : GAP}</div>
          <div class="rounded-xl border border-slate-200 p-3"><div class="font-bold text-[#173a2b]">Possible range (scenario) · climate model</div>${pj ? Object.entries(pj.periods || {}).map(([k, p]) => `<div>${esc(k)}: ${fmt(p.t2m_mean_c, 1)} °C · precip ${dist(p.precip_mm_per_year, " mm/yr")}</div>`).join("") + `<div class="text-[10px] text-slate-500">${esc(pj.source)} — ${esc(pj.note)}</div>` : GAP}</div>
        </div>
      </div>
      <h3 class="font-extrabold text-[#173a2b] mb-2">Crop water balance (FAO-56) — ${esc(q.label)}</h3>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">${(q.crop_cards || []).map((c) => `
        <div class="rounded-3xl bg-white shadow overflow-hidden">
          <div class="h-24 overflow-hidden"><img src="${(CROPS.find((x) => x.id === c.crop) || {}).img || ""}" class="w-full h-full object-cover" alt=""></div>
          <div class="p-4 text-xs space-y-1.5">
            <div class="flex justify-between items-baseline"><h4 class="text-lg font-extrabold text-[#173a2b]">${name(c.crop)}</h4><span class="text-[10px] text-amber-700 font-bold">${esc(c.label)}</span></div>
            <div title="${esc(c.kc?.source)} ${esc(c.kc?.note || "")}" class="cursor-help">K<sub>c</sub> ini/mid/end: <strong>${c.kc?.ini} / ${c.kc?.mid} / ${c.kc?.end}</strong> <span class="text-slate-400">(FAO-56 Table 12)</span></div>
            <div>Season ${esc(c.season_window?.start)} → ${esc(c.season_window?.end)} <span class="text-slate-400">(assumption)</span></div>
            <div>Crop water demand ETc: ${dist(c.history?.etc_mm, " mm")}</div>
            <div>Effective rain: ${dist(c.history?.effective_precip_mm, " mm")}</div>
            <div>Irrigation deficit: ${dist(c.history?.irrigation_deficit_mm, " mm")}</div>
            <div>Years with deficit: <strong>${c.history?.water_stress?.share_of_years_with_deficit != null ? fmt(c.history.water_stress.share_of_years_with_deficit * 100) + "%" : GAP}</strong></div>
            <div class="pt-1 border-t border-slate-100">Scenario range deficit: ${dist(c.projection?.irrigation_deficit_mm, " mm")}</div>
          </div></div>`).join("")}</div>
      <h3 class="font-extrabold text-[#173a2b] mb-1">Rotation candidates (not ranked)</h3>
      <p class="text-[11px] text-slate-500 mb-2">No crop repeats back-to-back. Order is arbitrary — compare trade-offs yourself. Sequences with the same crops in a different order share the same seasonal averages in this screening model (order effects such as N credit are not modelled).</p>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">${(q.rotation_candidates || []).map((r) => `
        <div class="rounded-2xl bg-white shadow p-4 text-xs">
          <div class="text-[11px] text-slate-500">Candidate ${r.candidate}</div>
          <div class="text-base font-extrabold text-[#173a2b] mb-2">${r.sequence.map(name).join(" → ")}</div>
          <div>Mean season ETc: <strong>${fmt(r.mean_season_etc_mm)} mm</strong></div>
          <div>Mean irrigation deficit: <strong>${fmt(r.mean_season_irrigation_deficit_mm)} mm</strong></div>
          <div>Water-use index: ${r.relative_water_use_index ? `<strong title="${esc(r.relative_water_use_index.tooltip)}" class="underline decoration-dotted cursor-help">${fmt(r.relative_water_use_index.value, 1)}</strong> <span class="text-slate-400">${esc(r.relative_water_use_index.unit)}</span>` : GAP}</div>
        </div>`).join("")}</div>
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div class="rounded-2xl bg-white shadow p-4 text-xs"><h4 class="font-extrabold text-[#173a2b] mb-1">Information gaps</h4><ul class="list-disc ml-5 text-slate-600">${(q.info_gaps || []).map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>
        <div class="rounded-2xl bg-white shadow p-4 text-xs"><h4 class="font-extrabold text-[#173a2b] mb-1">Assumptions & sources</h4>
          <ul class="list-disc ml-5 text-slate-600">${(q.economic_assumptions || []).map((a) => `<li>${esc(a.name || a.item || "")}: ${esc(a.value)} ${esc(a.unit || "")} — ${esc(a.source)} ${esc(a.year || "")} <em>(assumption)</em></li>`).join("")}
          ${(q.sources || []).map((s) => `<li>${esc(s)}</li>`).join("")}</ul>
          <p class="text-[10px] text-slate-500 mt-2">${esc(q.disclaimer)}</p></div>
      </div>`;
  }

  // deep link
  const h = location.hash.replace("#", "");
  if (h && $("#page-" + h) && h !== "loading" && h !== "results") show("page-" + h);
})();
