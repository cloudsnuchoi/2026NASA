/* ART FARM — Field Shift: Adapting Farms with NASA Data
 * Flow: Story → Map → Crops → Loading → Results
 * Tier 1 (anywhere): POST /api/quick  — FAO-56 engine ported from team MATLAB prototype V8 (screening estimate)
 * Tier 2 (polygon overlaps a pilot demo field): /api/simulate, /api/field/{id}/profile, /api/validation/backtest, /api/explain
 * Layout = UI/UX team final mockup v8 (analysis pages restored by the RESTORE lane, 2026-11-15).
 * Static copy (docs/demo/index.html sets window.ARTFARM_STATIC = true): JSON snapshots only, never a cross-origin
 * API call (no CORS errors on github.io); snapshots come from tools/make_demo_snapshot.py.
 */
(() => {
  "use strict";
  const API = (window.ARTFARM_API || "/api").replace(/\/$/, "");
  const STATIC = !!window.ARTFARM_STATIC;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmt = (v, d = 0) => (v === null || v === undefined || Number.isNaN(v) ? "—" : Number(v).toLocaleString("en-US", { maximumFractionDigits: d, minimumFractionDigits: d }));
  const GAP = '<span class="text-slate-500 italic">information gap</span>';
  const rng = (lo, hi, d = 0) => `<span class="rng text-[11px] text-slate-500">P10–P90 ${fmt(lo, d)}–${fmt(hi, d)}</span>`;
  function friendly(msg) {
    const m = String(msg || "");
    if (/429|rate limit/i.test(m)) return "Too many requests from this network in the last minute (public demo limit). Wait about a minute, then retry.";
    if (/Failed to fetch|NetworkError|Load failed/i.test(m)) return "Network connection to the ART FARM server failed. Check your connection, then retry.";
    if (/50[234]|upstream|unavailable/i.test(m)) return "A data service did not answer in time (server or upstream open-data API). Retry in a moment.";
    return "The request could not be completed.";
  }
  const errBox = (title, msg) => `<div class="rounded-2xl bg-white border border-red-300 p-4 text-sm text-slate-700" role="alert"><strong class="text-red-800">${title}</strong> — ${esc(friendly(msg))} <span class="text-slate-600">Information gap: no fallback values are shown.</span>
    <div class="mt-2 flex flex-wrap items-center gap-3"><button data-retry class="min-h-[44px] px-4 rounded-xl bg-[#173a2b] text-white text-xs font-bold">Retry</button><span class="text-xs text-slate-600">Detail: ${esc(msg)}</span></div></div>`;
  const REL_TIP = "Relative index vs strategy A (current practice), not a guarantee. Range shown is P10–P90.";

  const COUNTY = { "19169": "Story County, IA", "17113": "McLean County, IL", "31109": "Lancaster County, NE", "39159": "Union County, OH" };
  const CROP_DB = {
    Corn: { id: "Corn", name: "Corn", icon: "🌽", img: "assets/img10.jpg", color: "#e2b93b", kc: "0.30 / 1.20 / 0.60", desc: "C4 cereal, highest mid-season water demand of the three. Season window May–Sep (team assumption)." },
    Soy: { id: "Soy", name: "Soybean", icon: "🫘", img: "assets/img11.jpg", color: "#7fae4e", kc: "0.40 / 1.15 / 0.50", desc: "Legume; biological N fixation (not modelled in this screen). Season window May–Sep (team assumption)." },
    Wheat: { id: "Wheat", name: "Wheat", icon: "🌾", img: "assets/img12.jpg", color: "#c9a26b", kc: "0.40 / 1.15 / 0.25", desc: "Small grain; different season window from corn/soy. Window per engine assumption." },
  };
  const cname = (c) => CROP_DB[c]?.name || c;
  const COLORS = {
    user: { color: "#f7f6f0", weight: 2.5, fillColor: "#7dd3a8", fillOpacity: 0.38 },
    demo: { color: "#f2c46d", weight: 2, dashArray: "6 5", fillColor: "#f2c46d", fillOpacity: 0.14 },
    demoHit: { color: "#f2c46d", weight: 3, dashArray: null, fillColor: "#f2c46d", fillOpacity: 0.3 },
  };
  const BELT = { s: 36, n: 48, w: -104, e: -80 };
  const state = { vertices: [], preset: null, crops: [], fields: [], hitField: null, quick: null, sim: null, base: null, active: 0 };

  // ------------------------------------------------------------------ helpers
  function toast(msg, ms = 2600) {
    $("#toast-msg").textContent = msg;
    const t = $("#toast");
    t.classList.add("show");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => t.classList.remove("show"), ms);
  }

  // ---- static-demo API layer: snapshots only (no live API call from github.io → no CORS error)
  const SNAP = "snapshot/";
  const CROP_ORDER = { Corn: 0, Soy: 1, Wheat: 2 };
  const LIVE = { url: null };
  function fnv1a(str) {
    const bytes = new TextEncoder().encode(str);
    let h = 0x811c9dc5;
    for (const b of bytes) { h ^= b; h = Math.imul(h, 0x01000193) >>> 0; }
    return h.toString(16).padStart(8, "0");
  }
  function snapKey(method, path, body) {
    let k = method + "_" + path.replace(/^\/+|\/+$/g, "").replace(/[^A-Za-z0-9_.=-]/g, "_");
    if (body) {
      const b = { ...body };
      if (Array.isArray(b.crops)) b.crops = [...b.crops].sort((x, y) => (CROP_ORDER[x] ?? 9) - (CROP_ORDER[y] ?? 9));
      k += "_" + fnv1a(JSON.stringify(b));
    }
    return k + ".json";
  }
  function needsLive(msg) { const e = new Error(msg); e.needsLive = true; return e; }
  let snapIndex;
  async function snapshot(path, opts) {
    const method = opts.body ? "POST" : "GET";
    const k = snapKey(method, path, opts.body);
    snapIndex ??= fetch(SNAP + "index.json").then((r) => (r.ok ? r.json() : null)).then((j) => j?.files || null).catch(() => null);
    const idx = await snapIndex;
    const r = idx && !(k in idx) ? { ok: false } : await fetch(SNAP + k);
    if (r.ok) return r.json();
    if (path === "/quick") throw needsLive("Quick Screen for custom fields needs the live server");
    if (path === "/explain") throw needsLive("AI explanation is available on the live server");
    throw needsLive("Not in the static snapshot — available on the live server");
  }
  const liveLink = () => (LIVE.url ? ` <a class="underline font-bold" href="${esc(LIVE.url)}" target="_blank" rel="noopener">Open the live server →</a>` : "");
  function modeBadge() {
    const html = STATIC
      ? `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-100 text-amber-900 border border-amber-300 text-[10px] font-bold normal-case tracking-normal" title="Static snapshot generated 2026-11-15: results are pre-computed for the 4 pilot presets (screening estimates, not a guarantee)">📦 static snapshot${LIVE.url ? ` · <a class="underline" href="${esc(LIVE.url)}" target="_blank" rel="noopener">live server</a>` : ""}</span>`
      : "";
    $$(".mode-badge-slot").forEach((s) => (s.innerHTML = html));
  }
  if (STATIC) {
    // Same-origin file only (status/live.json on github.io); used for the "live server" link, never called as an API.
    fetch("../status/live.json", { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)).then((st) => {
      if (st?.demo_url) LIVE.url = String(st.demo_url).replace(/\/$/, "");
    }).catch(() => {}).finally(modeBadge);
    modeBadge();
    // "Live version →" header link: URL read at runtime from live_url.json ({"url","updated"}, tools/update_live_url.py).
    // The quick-tunnel URL changes on restart; missing/invalid file → no link.
    fetch("live_url.json", { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)).then((j) => {
      const u = typeof j?.url === "string" ? j.url.trim().replace(/\/$/, "") : "";
      const a = document.getElementById("live-version-link");
      if (!a || !/^https:\/\/[^\s"'<>]+$/.test(u)) return;
      a.href = u;
      if (j.updated) a.title += ` · URL updated ${String(j.updated).slice(0, 16)}`;
      a.hidden = false;
      if (!LIVE.url) { LIVE.url = u; modeBadge(); }
    }).catch(() => {});
  }

  async function api(path, opts = {}) {
    if (STATIC) return snapshot(path, opts);
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
  $("#btn-hero-start")?.addEventListener("click", () => show("page-map"));
  const COARSE = window.matchMedia?.("(pointer: coarse)").matches;
  if (COARSE) $$(".pointer-word").forEach((e) => (e.textContent = "Tap"));
  document.addEventListener("click", (e) => { if (e.target.closest("[data-retry]")) run(); });

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

  // ------------------------------------------------------------------ map (mockup layout: clear zone + translucent blue outside mask)
  let map, userLayer, vertexLayer, demoLayers = {};
  function initMap() {
    if (map) { setTimeout(() => map.invalidateSize(), 50); return; }
    map = L.map("map", { zoomControl: true, worldCopyJump: false }).setView([41.5, -91.5], 5);
    window.__artfarmMap = map;
    L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
      maxZoom: 19,
      attribution: "Imagery © Esri, Maxar, Earthstar Geographics, and the GIS User Community",
    }).addTo(map);
    L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}", {
      maxZoom: 19, opacity: 0.85, attribution: "Labels © Esri",
    }).addTo(map);
    const zone = [[BELT.s, BELT.w], [BELT.n, BELT.w], [BELT.n, BELT.e], [BELT.s, BELT.e]];
    L.polygon([[[85, -179], [85, 179], [-85, 179], [-85, -179]], zone], { stroke: false, fillColor: "#2563eb", fillOpacity: 0.38, interactive: false }).addTo(map);
    L.polygon(zone, { color: "#f59e0b", weight: 3, fill: false, interactive: false }).addTo(map);
    vertexLayer = L.layerGroup().addTo(map);
    map.on("click", (e) => addVertex([e.latlng.lng, e.latlng.lat]));
    loadDemoFields();
    setTimeout(() => map.invalidateSize(), 80);
  }
  async function loadDemoFields() {
    try {
      Object.values(demoLayers).forEach((l) => map.removeLayer(l)); demoLayers = {};
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
      state.fieldsError = e.message;
      toast("Pilot field outlines unavailable — " + friendly(e.message), 5000);
    }
  }
  function addVertex(p) {
    if (state.preset) { state.vertices = []; state.preset = null; }
    if (state.vertices.length >= 4) { toast("4 corners placed — Clear Points to redraw."); return; }
    if (!inCornBelt(p)) { toast("Not a designated area — outside the US Corn Belt screening zone (36–48°N, 80–104°W)."); return; }
    state.vertices.push(p);
    redraw();
  }
  function usePresetField(f) {
    state.vertices = f.ring.slice();
    state.preset = f;
    redraw();
    map.fitBounds(L.polygon(f.ring.map(([lo, la]) => [la, lo])).getBounds(), { padding: [60, 60], maxZoom: 16 });
  }
  const setT = (sel, t) => { const el = $(sel); if (el) el.textContent = t; };
  function centroid(v) { return v.reduce((a, p) => [a[0] + p[0] / v.length, a[1] + p[1] / v.length], [0, 0]); }
  function redraw() {
    vertexLayer.clearLayers();
    if (userLayer) { map.removeLayer(userLayer); userLayer = null; }
    const v = state.vertices;
    if (!state.preset) v.forEach((p, i) => L.circleMarker([p[1], p[0]], { radius: 6, color: "#173a2b", weight: 2, fillColor: "#f7f6f0", fillOpacity: 1 })
      .bindTooltip(String(i + 1), { permanent: true, direction: "top", className: "vtx-label" }).addTo(vertexLayer));
    if (v.length >= 2) userLayer = (v.length >= 3 ? L.polygon : L.polyline)(v.map(([lo, la]) => [la, lo]), COLORS.user).addTo(map);
    const m = metrics(v);
    setT("#meas-verts", state.preset ? `preset (${v.length} vertices)` : `${v.length} / 4`);
    const c = v.length ? centroid(v) : null;
    setT("#meas-coords", c ? `${c[1].toFixed(4)}, ${c[0].toFixed(4)}` : "—");
    setT("#meas-area", m ? `${fmt(m.area_ha * 1e4)} m² (${fmt(m.area_ha, 2)} ha / ${fmt(m.area_ha * 2.47105, 1)} ac)` : "—");
    setT("#meas-perim", m ? `${fmt(m.perimeter_km * 1000, 1)} m` : "—");
    state.hitField = null;
    Object.values(demoLayers).forEach((l) => l.setStyle(COLORS.demo));
    if (v.length >= 3) {
      state.hitField = state.preset || state.fields.find((f) => intersects(v, f.ring)) || null;
      if (state.hitField && demoLayers[state.hitField.field_id]) demoLayers[state.hitField.field_id].setStyle(COLORS.demoHit);
    }
    const ready = state.preset ? true : v.length === 4;
    setT("#meas-tier", !ready ? "—" : state.hitField ? "Quick Screen + Deep Analysis" : "Quick Screen");
    setT("#zone-badge", !v.length ? "No field yet" : state.hitField ? "Pilot field ✓" : "Corn Belt ✓");
    setT("#preset-region-label", c ? (state.hitField ? `${COUNTY[state.hitField.county_fips] || ""} · ` : "") + `${c[1].toFixed(4)}°N, ${Math.abs(c[0]).toFixed(4)}°W (centroid)` : "Draw a field or pick a preset — values load for its centroid");
    $("#btn-to-crops").disabled = !ready;
    const hint = $("#map-hint");
    if (hint) {
      const verb = COARSE ? "Tap" : "Click";
      hint.textContent = state.preset ? "Pilot field selected — Select Crops →"
        : v.length < 4 ? `${verb} corner ${v.length + 1} of 4` : "4 corners placed — Select Crops →";
    }
    if (ready) loadBaseline(); else clearBaseline();
  }
  function clearBaseline() {
    state.base = null;
    ["#env-temp", "#env-precip", "#env-et", "#env-ndvi", "#meas-elev"].forEach((s) => setT(s, "—"));
  }
  // Regional baseline: the same /quick call the results use (Corn+Soy), so every number shown here comes from the engine.
  let baseSeq = 0;
  async function loadBaseline() {
    const seq = ++baseSeq;
    clearBaseline();
    ["#env-temp", "#env-precip", "#env-et", "#env-ndvi"].forEach((s) => setT(s, "…"));
    const poly = state.vertices.length > 60 ? simplify(state.vertices, 60) : state.vertices;
    const body = { polygon: poly, crops: ["Corn", "Soy"] };
    try {
      const q = await api("/quick", { body });
      if (seq !== baseSeq) return;
      state.base = { key: JSON.stringify(poly), q };
      fillBaseline(q);
    } catch (e) {
      if (seq !== baseSeq) return;
      ["#env-temp", "#env-precip", "#env-et", "#env-ndvi"].forEach((s) => setT(s, "gap"));
      setT("#preset-region-label", e.needsLive ? "Static snapshot covers the 4 pilot presets only — custom fields need the live server" : "Baseline unavailable — " + friendly(e.message));
    }
  }
  function fillBaseline(q) {
    const ch = q.climate_history, mean = ch?.mean || {};
    setT("#env-temp", mean.t2m_c ? `${fmt(mean.t2m_c.mean, 1)} °C` : "gap");
    setT("#env-precip", mean.precip_mm ? `${fmt(mean.precip_mm.mean)} mm` : "gap");
    setT("#env-et", mean.et0_mm ? `${fmt(mean.et0_mm.mean)} mm` : "gap");
    const w = (ch?.per_year || []).map((y) => y.root_zone_wetness_mean).filter((x) => x != null);
    setT("#env-ndvi", w.length ? fmt(w.reduce((a, b) => a + b, 0) / w.length, 2) : "gap");
    setT("#meas-elev", q.elevation ? `${fmt(q.elevation.value_m, 1)} m (centroid)` : "gap");
    setT("#api-terrain-badge", q.elevation ? "WGS84 + USGS 3DEP ✓" : "WGS84 geodesic");
  }
  $("#btn-clear-poly").addEventListener("click", () => { state.vertices = []; state.preset = null; redraw(); });
  $("#btn-zoom-circle").addEventListener("click", () => {
    if (!map) return;
    if (userLayer && state.vertices.length >= 3) map.fitBounds(userLayer.getBounds(), { padding: [60, 60], maxZoom: 16 });
    else map.fitBounds([[BELT.s, BELT.w], [BELT.n, BELT.e]]);
  });
  $("#btn-sample-outside").addEventListener("click", () => {
    if (map) map.flyTo([33.5, -112.0], 6, { duration: 0.9 });
    toast("Not a designated area — outside the US Corn Belt screening zone (translucent blue).");
  });
  $$("[data-preset]").forEach((b) => b.addEventListener("click", () => {
    const f = state.fields.find((x) => x.county_fips === b.dataset.preset);
    if (!f) {
      if (state.fieldsError) { state.fieldsError = null; toast("Retrying pilot field outlines…"); loadDemoFields(); }
      else toast("Pilot fields still loading…");
      return;
    }
    usePresetField(f);
  }));
  $("#btn-to-crops").addEventListener("click", () => show("page-crops"));

  // ------------------------------------------------------------------ crops (mockup cards + compact slots)
  function renderCrops() {
    $("#crop-cards-grid").innerHTML = Object.values(CROP_DB).map((crop) => {
      const sel = state.crops.includes(crop.id);
      return `<button type="button" data-crop="${crop.id}" aria-pressed="${sel}" class="${sel
        ? "text-center rounded-2xl p-6 bg-[#173a2b] text-white border-2 border-[#173a2b] shadow-lg transition transform -translate-y-0.5 flex flex-col items-center"
        : "text-center rounded-2xl p-6 bg-white text-[#173a2b] border-2 border-slate-200 hover:border-emerald-600/50 shadow-sm transition flex flex-col items-center"}">
        <div class="text-5xl mb-3">${crop.icon}</div>
        <div class="text-lg font-extrabold mb-1">${crop.name}</div>
        <div class="text-[11px] font-bold mb-3 ${sel ? "text-amber-300" : "text-emerald-700"}">Kc ${crop.kc} · FAO-56</div>
        <p class="text-xs leading-relaxed mb-5 ${sel ? "text-emerald-100/85" : "text-slate-600"}">${crop.desc}</p>
        <span class="mt-auto px-4 py-1.5 rounded-full text-xs font-bold ${sel ? "bg-amber-300 text-[#173a2b]" : "bg-slate-100 text-slate-600"}">${sel ? "✓ Selected" : "Select"}</span>
      </button>`;
    }).join("");
    $("#selected-slots").innerHTML = state.crops.length
      ? state.crops.map((id) => `<button type="button" data-crop="${id}" title="Remove ${cname(id)}" class="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-[#2c4e38] hover:bg-red-700 text-white text-xs font-bold transition shadow-sm"><span>${CROP_DB[id].icon} ${cname(id)}</span><span class="opacity-75 text-[11px]">✕</span></button>`).join("")
      : '<span class="text-xs text-slate-400 italic">Select at least 2 crops</span>';
    $("#btn-confirm-crops").disabled = state.crops.length < 2;
  }
  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-crop]"); if (!b) return;
    const id = b.dataset.crop, i = state.crops.indexOf(id);
    if (i >= 0) state.crops.splice(i, 1);
    else if (state.crops.length < 3) state.crops.push(id);
    renderCrops();
  });
  $("#btn-reset-crops").addEventListener("click", () => { state.crops = []; renderCrops(); });
  renderCrops();

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
  $("#btn-confirm-crops").addEventListener("click", () => {
    if (state.crops.length < 2) { toast("Select at least 2 crops for a rotation."); return; }
    run();
  });
  async function run() {
    show("page-loading");
    const status = $("#loading-status");
    const msgs = ["Querying USGS 3DEP elevation…", "Downloading NASA POWER 10-year daily weather…", "Reading NOAA/NWS forecast and Open-Meteo CMIP6 climate range…", "Running FAO-56 water balance per crop…"];
    let k = 0; status.textContent = msgs[0];
    const tick = setInterval(() => { k = (k + 1) % msgs.length; status.textContent = msgs[k]; }, 1500);
    const poly = state.vertices.length > 60 ? simplify(state.vertices, 60) : state.vertices;
    const cs = [...state.crops].sort((x, y) => CROP_ORDER[x] - CROP_ORDER[y]);
    const reuse = state.base && state.base.key === JSON.stringify(poly) && cs.join() === "Corn,Soy";
    const pQuick = reuse ? Promise.resolve(state.base.q)
      : api("/quick", { body: { polygon: poly, crops: state.crops } }).catch((e) => ({ __error: e.message, __needsLive: e.needsLive }));
    const fid = state.hitField?.field_id;
    const pDeep = fid ? Promise.all([
      api("/simulate", { body: { field_id: fid, n: 500, seed: 42 } }),
      api(`/field/${fid}/profile`),
      api(`/validation/backtest?field_id=${fid}&year=2012`).catch(() => null),
    ]).catch((e) => ({ __error: e.message })) : Promise.resolve(null);
    const [q, d] = await Promise.all([pQuick, pDeep]);
    clearInterval(tick);
    state.quick = q; state.active = 0;
    show("page-results");
    renderTier1(q, d);
    renderTier2(d, fid);
  }
  function simplify(pts, n) { const s = Math.ceil(pts.length / n); return pts.filter((_, i) => i % s === 0); }

  // ------------------------------------------------------------------ Tier 1 → mockup results dashboard
  const dist = (o, u = "") => (!o ? GAP : `<strong>${fmt(o.p50)}</strong>${u} ${rng(o.p10, o.p90)}`);
  const row = (k, v) => `<div class="flex justify-between gap-3 bg-[#214d3a] px-3.5 py-2 rounded-xl"><span class="text-emerald-100/80">${k}</span><span class="font-bold text-right">${v}</span></div>`;
  let charts = [];
  // ------------------------------------------------------------------ PORT: team mockup V8 results dashboard (verbatim) + engine binding
  let portedHtml = null;
  async function renderPorted(el, q, d) {
    if (portedHtml == null) portedHtml = await fetch("mockup_results.html").then((r) => r.text());
    el.innerHTML = portedHtml;
    const M = window.MockupV8, S = M.state;
    const ring = (q.input?.polygon || state.vertices).map(([lon, lat]) => [lat, lon]);
    M.setGeo(ring);
    S.selectedCrops = [...state.crops].sort((x, y) => CROP_ORDER[x] - CROP_ORDER[y]);
    const py = q.climate_history?.per_year || [];
    window.__AF_BIND = py.length ? { years: py.map((r) => r.year), temp: py.map((r) => r.t2m_mean_c), precip: py.map((r) => r.precip_mm), et0: py.map((r) => r.et0_pm_mm), rzw: py.every((r) => r.root_zone_wetness_mean != null) ? py.map((r) => r.root_zone_wetness_mean) : null } : null;
    await M.runFieldShiftLiveApiEngine();
    if (q.geometry?.area_ha) S.geo.area_m2 = q.geometry.area_ha * 10000;
    if (q.elevation?.value_m != null) { // engine has the centroid only: anchor the prototype relief grid to it
      const off = q.elevation.value_m - S.dem.medianElev_m;
      S.dem.medianElev_m = q.elevation.value_m;
      S.dem.minElev_m = +(S.dem.minElev_m + off).toFixed(2); S.dem.maxElev_m = +(S.dem.maxElev_m + off).toFixed(2);
      if (Array.isArray(S.dem.gridZ)) S.dem.gridZ = S.dem.gridZ.map((r) => (Array.isArray(r) ? r.map((z) => z + off) : r + off));
    }
    const cands = q.rotation_candidates || [];
    S.scenarios.forEach((sc) => {
      const seq = Array.isArray(sc.rotSeq) ? sc.rotSeq.join() : null;
      const c = cands.find((k) => k.sequence.join() === seq);
      if (c?.mean_season_etc_mm != null) sc.ETm_mm = c.mean_season_etc_mm;
    });
    M.renderResultsDashboard();
    const tag = '<span class="af-proto ml-1 px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 text-[10px] font-bold align-middle">prototype estimate (team V8)</span>';
    ["#scen-profit-ac", "#kpi-som-idx", "#kpi-stab-all", "#opt-alloc-solver"].forEach((sel) => { const n = $(sel); if (n) n.insertAdjacentHTML("afterend", tag); });
    const tb = $("#all-scenarios-tbody")?.closest("table");
    if (tb) tb.insertAdjacentHTML("afterend", tag);
    const sim = Array.isArray(d) ? d[0] : null;
    const w = sim?.strategies?.[0]?.metrics?.season_water_deficit_mm;
    if (tb && w && w.p10 != null) {
      tb.insertAdjacentHTML("afterend", `<p id="pilot-engine-line" class="text-xs text-slate-700 font-semibold mt-2">Pilot-field engine: deficit P10–P90 ${fmt(w.p10)}–${fmt(w.p90)} mm, CVaR10% ${fmt(w.cvar)} mm (n=${sim.n ?? sim.n_seasons ?? 500} seasons)</p>`);
    }
  }
  function renderTier1(q, d) {
    const el = $("#tier1");
    charts.forEach((c) => c.destroy()); charts = [];
    if (!q || q.__error) {
      el.innerHTML = q?.__needsLive
        ? `<div class="rounded-2xl bg-white border border-amber-400 p-4 text-sm">📦 <strong>Quick Screen for custom fields needs the live server.</strong> This static snapshot only contains the 4 pilot presets (Corn+Soy, Corn+Soy+Wheat). No fallback values are shown.${liveLink()}</div>`
        : errBox("Quick Screen unavailable", q?.__error);
      return;
    }
    if (window.MockupV8) { renderPorted(el, q, d); return; }
    const g = q.geometry || {}, ch = q.climate_history, fc = q.forecast_anomaly, pj = q.climate_projection;
    const cands = q.rotation_candidates || [];
    const cards = Object.fromEntries((q.crop_cards || []).map((c) => [c.crop, c]));
    const yrs = ch?.per_year || [];
    const wet = yrs.map((y) => y.root_zone_wetness_mean).filter((x) => x != null);
    const deficitShare = (q.crop_cards || []).map((c) => `${cname(c.crop)} ${c.history?.water_stress?.share_of_years_with_deficit != null ? fmt(c.history.water_stress.share_of_years_with_deficit * 100) + "%" : "gap"}`).join(" · ");
    const periods = Object.entries(pj?.periods || {});
    const fid = state.hitField?.field_id;
    const prof = d && !d.__error ? d[1] : null, v = prof?.vision || {};
    const cdl = (prof?.cdl_history || []).slice().sort((a, b) => b.year - a.year).slice(0, 6);
    el.innerHTML = `
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      <aside class="lg:col-span-4 space-y-5">
        <div class="bg-white rounded-2xl p-5 shadow-md border border-slate-200">
          <div class="flex items-center justify-between mb-3">
            <h2 class="text-sm font-extrabold text-[#173a2b] uppercase tracking-wider">Selected Crops</h2>
            <span class="px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-900 text-[11px] font-bold">2–3 crop rotation</span>
          </div>
          <div class="flex flex-wrap gap-2">${(q.input?.crops || state.crops).map((c) => `<span class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#2c4e38] text-white text-xs font-bold">${CROP_DB[c]?.icon || ""} ${cname(c)}</span>`).join("")}</div>
          <p class="text-xs text-slate-600 mt-3 leading-relaxed">Rotations with no crop repeated back-to-back, shown <strong class="text-[#173a2b]">unranked</strong> as [Result 1], [Result 2]…</p>
        </div>
        <div class="bg-[#173a2b] text-white rounded-2xl p-5 shadow-xl space-y-3.5">
          <div class="flex items-center justify-between">
            <div class="text-xs font-bold uppercase tracking-wider text-amber-300">🛰️ [Step 1–2] USGS 3DEP &amp; NASA POWER</div>
            <span class="text-[11px] text-emerald-300 font-mono">${fmt(g.centroid?.lat, 4)}, ${fmt(g.centroid?.lon, 4)}</span>
          </div>
          <p class="text-xs text-emerald-100/85 leading-relaxed">WGS84 ellipsoid area <strong>${fmt(g.area_ha, 2)} ha</strong> (${fmt(g.perimeter_km, 3)} km perimeter) · NASA POWER ${esc(ch?.period || "")} daily agro-weather at the centroid (~0.5° cell, not field-precise).</p>
          <div class="space-y-2 text-xs">
            ${row("USGS 3DEP elevation (centroid)", q.elevation ? fmt(q.elevation.value_m, 1) + " m" : GAP)}
            ${row("10-yr mean temp / precip", ch ? `${fmt(ch.mean?.t2m_c?.mean, 1)} °C / ${fmt(ch.mean?.precip_mm?.mean)} mm/yr` : GAP)}
            ${row("10-yr mean reference ET₀", ch ? `${fmt(ch.mean?.et0_mm?.mean)} mm/yr` : GAP)}
            ${row("Years with irrigation deficit", `<span class="text-amber-300">${deficitShare || "gap"}</span>`)}
            ${row("Root-zone wetness (POWER, 0–1)", wet.length ? fmt(wet.reduce((a, b) => a + b, 0) / wet.length, 3) : GAP)}
          </div>
        </div>
        <div class="bg-white rounded-2xl p-5 shadow-md border border-slate-200 space-y-3">
          <div class="text-xs font-extrabold uppercase tracking-wider text-[#173a2b]">🌦️ [Step 3] Possible range (scenario) · NOAA/NWS + CMIP6</div>
          <p class="text-[11px] text-slate-600 leading-relaxed">${esc(pj?.source || "Climate projection: information gap")}. ${esc(pj?.note || "")}</p>
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs border-collapse">
              <thead><tr class="border-b border-slate-200 text-slate-500"><th class="py-1.5 font-bold">Period</th><th class="py-1.5 font-bold text-right">Temp</th><th class="py-1.5 font-bold text-right">Precip (P10–P90)</th><th class="py-1.5 font-bold text-right">ET₀</th></tr></thead>
              <tbody class="divide-y divide-slate-100 font-semibold text-slate-800">
                ${ch ? `<tr><td class="py-1.5 text-slate-700">${esc(ch.period)} (POWER obs.)</td><td class="py-1.5 text-right">${fmt(ch.mean?.t2m_c?.mean, 2)} °C</td><td class="py-1.5 text-right">${fmt(ch.mean?.precip_mm?.p10)}–${fmt(ch.mean?.precip_mm?.p90)} mm</td><td class="py-1.5 text-right text-amber-800">${fmt(ch.mean?.et0_mm?.mean)} mm</td></tr>` : ""}
                ${periods.map(([k, p]) => `<tr><td class="py-1.5 text-slate-700">${esc(k)} (scenario)</td><td class="py-1.5 text-right">${fmt(p.t2m_mean_c, 2)} °C</td><td class="py-1.5 text-right">${fmt(p.precip_mm_per_year?.p10)}–${fmt(p.precip_mm_per_year?.p90)} mm</td><td class="py-1.5 text-right text-amber-800">${fmt(p.et0_mm_per_year?.p50 ?? p.et0_mm_per_year?.mean)} mm</td></tr>`).join("")}
              </tbody>
            </table>
          </div>
          <div class="text-[11px] text-emerald-800 bg-emerald-50 rounded-xl px-3 py-2 font-medium">NWS 7-day anomaly: ${fc && fc.anomaly_c != null ? `<strong>${fc.anomaly_c > 0 ? "+" : ""}${fmt(fc.anomaly_c, 1)} °C</strong> vs ${esc(fc.baseline)} — ${esc(fc.note)}` : "information gap"}</div>
        </div>
        <div class="bg-[#173a2b] text-white rounded-2xl p-5 shadow-xl space-y-3 border border-amber-400/30">
          <div class="flex items-center justify-between">
            <div class="text-xs font-extrabold uppercase tracking-wider text-amber-300">🧪 [Step 5] Deep Analysis · pilot field</div>
            <span class="px-2 py-0.5 rounded bg-amber-400/20 text-amber-200 text-[10px] font-bold">${fid ? "Monte Carlo · CVaR" : "4 pilot counties"}</span>
          </div>
          ${fid && prof ? `
          <div class="text-xs sm:text-sm font-extrabold text-white leading-relaxed bg-[#214d3a] p-3 rounded-xl border border-emerald-400/20">${esc(prof.region_label || COUNTY[prof.county_fips] || "")} · field ${esc(fid)} · ${fmt(prof.area_ha, 1)} ha · current rotation ${esc(prof.current_rotation || "—")}</div>
          <div class="space-y-1.5 text-xs pt-1">
            <div class="flex justify-between gap-2"><span class="text-emerald-100/80">Prithvi-EO crop map (vision):</span><span class="font-extrabold text-amber-300">${esc(v.crop_pred || "—")}</span></div>
            <div class="flex justify-between gap-2"><span class="text-emerald-100/80">Agreement with USDA CDL:</span><span class="font-bold">${v.agreement_with_cdl != null ? fmt(v.agreement_with_cdl * 100, 0) + "%" : "—"}</span></div>
            <div class="flex justify-between gap-2"><span class="text-emerald-100/80">Soil OM / AWC (gSSURGO):</span><span class="font-bold">${fmt(prof.soil?.om_pct, 1)}% / ${fmt(prof.soil?.awc_cm_cm, 2)} cm/cm</span></div>
            <div class="flex justify-between gap-2"><span class="text-emerald-100/80">NDVI peak (HLS):</span><span class="font-bold text-emerald-300">${fmt(prof.ndvi_peak, 2)}</span></div>
          </div>
          <div class="flex flex-wrap gap-1 text-[10px]">${cdl.map((c) => `<span class="px-1.5 py-0.5 rounded bg-white/15">${c.year}: ${esc(c.crop)}</span>`).join("")}</div>
          <a href="#tier2" data-jump="#tier2" class="block text-center w-full py-2.5 rounded-xl bg-[#66b888] hover:bg-[#57a879] text-[#0f291e] font-extrabold text-xs">Compare strategies A–D ↓</a>
          <div class="text-[10px] text-emerald-200/70 pt-1 border-t border-emerald-400/20">${esc(prof.disclaimer || "")}</div>`
          : fid ? `<div class="text-xs text-emerald-100/85">Deep analysis engine unavailable — information gap.</div>`
          : `<div class="text-xs sm:text-sm font-bold text-white leading-relaxed bg-[#214d3a] p-3 rounded-xl border border-emerald-400/20">Deep analysis (Monte Carlo water balance, CVaR, 2012 backtest, Prithvi/CDL) is available for the 20 demo fields in Story IA, McLean IL, Lancaster NE and Union OH. Use a preset on the map.</div>`}
        </div>
      </aside>
      <div class="lg:col-span-8 space-y-5">
        <div class="bg-white rounded-2xl p-4 shadow-md border border-slate-200">
          <div class="text-xs font-extrabold uppercase tracking-wider text-slate-500 mb-2.5">📋 [Step 4] Unranked rotation scenarios (2–3 crops · no crop back-to-back)</div>
          <div id="scenario-tabs" class="flex flex-wrap gap-2"></div>
        </div>
        <div id="scen-card" class="bg-white rounded-3xl p-6 shadow-xl border border-slate-200 space-y-6"></div>
      </div>
    </div>`;
    renderScenario(q, cards);
  }
  function renderScenario(q, cards) {
    const cands = q.rotation_candidates || [];
    const i = Math.min(state.active, cands.length - 1), sc = cands[i];
    $("#scenario-tabs").innerHTML = cands.map((c, k) => `<button type="button" data-scen="${k}" class="${k === i
      ? "px-4 py-2.5 rounded-xl bg-[#173a2b] text-white text-xs font-extrabold shadow-md transition"
      : "px-4 py-2.5 rounded-xl bg-slate-50 hover:bg-emerald-50 text-[#173a2b] border border-slate-200 text-xs font-bold transition"}">[Result ${c.candidate}] ${c.sequence.map(cname).join(" → ")}</button>`).join("");
    if (!sc) { $("#scen-card").innerHTML = GAP; return; }
    const crops = [...new Set(sc.sequence)];
    const cc = crops.map((c) => cards[c]).filter(Boolean);
    const ri = sc.relative_water_use_index;
    const projDef = cc.map((c) => `${cname(c.crop)} ${fmt(c.projection?.irrigation_deficit_mm?.p50)} mm`).join(" · ");
    const histDef = cc.map((c) => `${cname(c.crop)} ${fmt(c.history?.irrigation_deficit_mm?.p50)} mm`).join(" · ");
    const yrsDef = cc.map((c) => `${cname(c.crop)} ${c.history?.water_stress?.share_of_years_with_deficit != null ? fmt(c.history.water_stress.share_of_years_with_deficit * 100) + "%" : "gap"}`).join(" · ");
    $("#scen-card").innerHTML = `
      <div class="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 pb-4">
        <div>
          <div class="flex items-center gap-2 mb-2">
            <span class="inline-block px-3 py-1 rounded-full bg-amber-100 text-amber-900 text-xs font-extrabold">[Result ${sc.candidate}] (${cands.length} scenarios · unranked)</span>
            <span class="inline-block px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-900 text-[11px] font-bold">${esc(sc.label)}</span>
          </div>
          <h2 class="text-xl sm:text-2xl font-extrabold text-[#173a2b]">${sc.sequence.map(cname).join(" – ")} rotation</h2>
          <div class="text-sm font-extrabold text-emerald-700 mt-1">Sequence: ${sc.sequence.map(cname).join(" → ")}</div>
        </div>
        <div class="text-right bg-emerald-50/80 px-4 py-3 rounded-2xl border border-emerald-200">
          <div class="text-[11px] text-slate-600 font-bold">Water-use index (continuous corn = 100)</div>
          <div class="text-2xl font-extrabold text-[#173a2b] underline decoration-dotted cursor-help" title="${esc(ri?.tooltip || REL_TIP)}">${ri ? fmt(ri.value, 1) : "gap"}</div>
          <div class="text-xs text-emerald-800 font-bold">relative index, not a guarantee</div>
        </div>
      </div>
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div class="rounded-xl bg-slate-50 border border-slate-200 p-3.5"><div class="text-[11px] text-slate-500 font-semibold">Mean season crop water demand (ETc)</div><div class="text-base font-extrabold text-[#173a2b] mt-0.5">${fmt(sc.mean_season_etc_mm)} mm</div><div class="text-[11px] text-slate-500 mt-0.5">FAO-56 Kc × ET₀</div></div>
        <div class="rounded-xl bg-slate-50 border border-slate-200 p-3.5"><div class="text-[11px] text-slate-500 font-semibold">Mean irrigation deficit</div><div class="text-base font-extrabold text-emerald-700 mt-0.5">${fmt(sc.mean_season_irrigation_deficit_mm)} mm</div><div class="text-[11px] text-slate-500 mt-0.5">max(0, ETc − Peff)</div></div>
        <div class="rounded-xl bg-slate-50 border border-slate-200 p-3.5"><div class="text-[11px] text-slate-500 font-semibold">Years with deficit (10 yr)</div><div class="text-sm font-extrabold text-[#173a2b] mt-0.5">${yrsDef}</div></div>
        <div class="rounded-xl bg-slate-50 border border-slate-200 p-3.5"><div class="text-[11px] text-slate-500 font-semibold">Scenario-range deficit P50</div><div class="text-sm font-extrabold text-amber-700 mt-0.5">${projDef}</div><div class="text-[11px] text-slate-500 mt-0.5">possible range, not a forecast</div></div>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="rounded-2xl bg-emerald-50 border border-emerald-200 p-4"><div class="text-xs font-extrabold uppercase tracking-wider text-emerald-900 mb-1.5">✅ What the engine shows (FAO-56)</div>
          <p class="text-xs sm:text-sm text-slate-800 font-medium leading-relaxed">Past 10-yr irrigation deficit P50: ${histDef}. Water-use index ${ri ? fmt(ri.value, 1) : "gap"} vs continuous corn (=100) at this location.</p></div>
        <div class="rounded-2xl bg-amber-50 border border-amber-200 p-4"><div class="text-xs font-extrabold uppercase tracking-wider text-amber-900 mb-1.5">⚠️ Trade-offs / limits (scenario range)</div>
          <p class="text-xs sm:text-sm text-slate-800 font-medium leading-relaxed">Scenario-range deficit P50: ${projDef}. Sequences with the same crops in a different order share the same seasonal averages here — order effects such as N credit are not modelled.</p></div>
      </div>
      <div class="rounded-2xl bg-slate-100 border border-slate-200 px-4 py-3.5 text-xs sm:text-sm text-slate-800 font-medium">
        <strong class="text-[#173a2b]">🚜 Check locally (information gaps):</strong> ${(q.info_gaps || []).map(esc).join(" · ") || "—"}
      </div>
      <div class="pt-2">
        <div class="text-xs font-extrabold text-[#173a2b] mb-2">📊 All candidate rotations (unranked · click to switch)</div>
        <div class="overflow-x-auto rounded-2xl border border-slate-200">
          <table class="w-full text-left text-xs border-collapse">
            <thead class="bg-slate-100 text-slate-700"><tr><th class="py-2.5 px-3 font-extrabold">No.</th><th class="py-2.5 px-3 font-extrabold">Rotation sequence</th><th class="py-2.5 px-3 font-extrabold text-right">Mean ETc</th><th class="py-2.5 px-3 font-extrabold text-right">Irrigation deficit</th><th class="py-2.5 px-3 font-extrabold text-right">Water-use index</th></tr></thead>
            <tbody class="divide-y divide-slate-200 bg-white">${cands.map((c, k) => `<tr data-scen="${k}" class="${k === i ? "bg-emerald-50/90 font-bold" : "hover:bg-slate-50"} cursor-pointer transition">
              <td class="py-2.5 px-3 text-[#173a2b] font-extrabold">[Result ${c.candidate}]</td>
              <td class="py-2.5 px-3"><div class="font-extrabold text-[#173a2b]">${c.sequence.map(cname).join(" → ")}</div></td>
              <td class="py-2.5 px-3 text-right">${fmt(c.mean_season_etc_mm)} mm</td>
              <td class="py-2.5 px-3 text-right text-emerald-800">${fmt(c.mean_season_irrigation_deficit_mm)} mm</td>
              <td class="py-2.5 px-3 text-right font-mono">${c.relative_water_use_index ? fmt(c.relative_water_use_index.value, 1) : "gap"}</td></tr>`).join("")}</tbody>
          </table>
        </div>
      </div>
      <div class="pt-2">
        <div class="flex flex-wrap items-center justify-between gap-2 mb-2.5">
          <span class="text-xs font-extrabold text-[#173a2b]">📸 Field visual comparison: monoculture (before) vs rotation (after) — illustrative</span>
          <span class="text-[11px] text-slate-500">AI-generated images; illustrative, not your field</span>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="relative aspect-[4/3] rounded-2xl overflow-hidden border border-slate-200 shadow-md bg-slate-100">
            <img src="${CROP_DB.Corn.img}" alt="Illustrative continuous corn field" class="w-full h-full object-cover block" />
            <div class="absolute top-3 left-3 px-2.5 py-1 rounded-md bg-black/70 text-white text-[11px] font-bold">Before · continuous monoculture</div>
          </div>
          <div class="relative aspect-[4/3] rounded-2xl overflow-hidden border border-emerald-200 shadow-md bg-emerald-950/10">
            <div class="absolute inset-0 flex">${crops.map((c) => `<img src="${CROP_DB[c]?.img}" alt="Illustrative ${cname(c)} field" class="h-full object-cover" style="width:${100 / crops.length}%" />`).join("")}</div>
            <div class="absolute top-3 left-3 px-2.5 py-1 rounded-md bg-emerald-900/85 text-white text-[11px] font-bold">After · [Result ${sc.candidate}] ${sc.sequence.map(cname).join(" → ")}</div>
            <div class="absolute bottom-2.5 left-2 right-2 flex items-center justify-around gap-1.5 pointer-events-none">${crops.map((c) => `<span class="px-2 py-1 rounded-md bg-black/65 text-white text-[11px] font-bold">${CROP_DB[c]?.icon || ""} ${cname(c)}</span>`).join("")}</div>
          </div>
        </div>
      </div>
      <div class="pt-3 border-t border-slate-200">
        <div class="mb-4"><div class="text-xs font-extrabold uppercase tracking-wider text-emerald-800">📊 FAO-56 engine — 4-panel analysis</div>
          <p class="text-xs text-slate-600">Field outline (WGS84) · NASA POWER yearly water · unranked scenario comparison · possible range (scenario) for precipitation</p></div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="rounded-2xl bg-[#f8faf5] border border-slate-200 p-4 shadow-sm"><div class="text-xs font-extrabold text-[#173a2b] mb-2">① Measured field boundary (WGS84) · 3DEP centroid ${q.elevation ? fmt(q.elevation.value_m, 1) + " m" : "gap"}</div>
            <div class="relative h-56 flex items-center justify-center"><canvas id="field-canvas" width="460" height="240" class="w-full h-full rounded-xl border border-slate-200 bg-white"></canvas></div></div>
          <div class="rounded-2xl bg-[#f8faf5] border border-slate-200 p-4 shadow-sm"><div class="text-xs font-extrabold text-[#173a2b] mb-2">② NASA POWER ${esc(q.climate_history?.period || "")} yearly precip &amp; ET₀ (observed)</div>
            <div class="relative h-56"><canvas id="hydrology-chart"></canvas></div></div>
          <div class="rounded-2xl bg-[#f8faf5] border border-slate-200 p-4 shadow-sm"><div class="text-xs font-extrabold text-[#173a2b] mb-2">③ Scenario comparison (unranked): ETc · irrigation deficit</div>
            <div class="relative h-56"><canvas id="scenario-bar-chart"></canvas></div></div>
          <div class="rounded-2xl bg-[#f8faf5] border border-slate-200 p-4 shadow-sm"><div class="text-xs font-extrabold text-[#173a2b] mb-2">④ Possible range (scenario): annual precip P10–P90</div>
            <div class="relative h-56"><canvas id="stability-chart"></canvas></div></div>
        </div>
      </div>
      <div class="pt-2">
        <details class="group rounded-2xl bg-[#102419] text-emerald-100 border border-emerald-500/30 overflow-hidden">
          <summary class="cursor-pointer px-4 py-3 text-xs font-extrabold text-amber-300 flex items-center justify-between select-none"><span>🖥️ ${esc(q.engine)} — assumptions &amp; sources report</span><span class="text-emerald-300 group-open:rotate-180 transition-transform">▼</span></summary>
          <pre class="p-4 text-[11px] font-mono leading-relaxed text-emerald-100/95 overflow-x-auto bg-[#0b1911] border-t border-emerald-500/20 whitespace-pre-wrap">${esc([
            `engine: ${q.engine} · label: ${q.label} · generated ${q.generated_utc || ""}`,
            `geometry: ${q.geometry?.method || ""}`,
            `elevation: ${q.elevation?.source || "information gap"}`,
            `climate history: ${q.climate_history?.source || "information gap"} · ET0 ${q.climate_history?.et0_method || ""}`,
            `forecast: ${q.forecast_anomaly?.source || "information gap"}`,
            `projection: ${q.climate_projection?.source || "information gap"}`,
            ...(q.assumptions || []).map((a) => `assumption ${a.name}: ${typeof a.value === "object" ? JSON.stringify(a.value) : a.value} ${a.source ? "— " + a.source : ""}`),
            ...(q.economic_assumptions || []).map((a) => `economic assumption ${a.name || a.item || ""}: ${a.value} ${a.unit || ""} — ${a.source || ""} ${a.year || ""}`),
            ...(q.sources || []).map((s) => `source: ${s}`),
            `disclaimer: ${q.disclaimer || ""}`,
          ].join("\n"))}</pre>
        </details>
      </div>`;
    drawTier1Charts(q, cands, i);
  }
  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-scen]");
    if (b && state.quick && !state.quick.__error) {
      state.active = +b.dataset.scen;
      renderScenario(state.quick, Object.fromEntries((state.quick.crop_cards || []).map((c) => [c.crop, c])));
    }
    const j = e.target.closest("[data-jump]");
    if (j) { e.preventDefault(); $(j.dataset.jump)?.scrollIntoView({ behavior: "smooth", block: "start" }); }
  });
  function drawTier1Charts(q, cands, i) {
    charts.forEach((c) => c.destroy()); charts = [];
    // ① field outline from the polygon actually sent to the engine
    const cv = $("#field-canvas"), ring = q.input?.polygon || state.vertices;
    if (cv && ring?.length >= 3) {
      const ctx = cv.getContext("2d"), W = cv.width, H = cv.height;
      ctx.clearRect(0, 0, W, H);
      const lat0 = ring.reduce((a, p) => a + p[1], 0) / ring.length, kx = Math.cos((lat0 * Math.PI) / 180);
      const xs = ring.map((p) => p[0] * kx), ys = ring.map((p) => p[1]);
      const minx = Math.min(...xs), maxx = Math.max(...xs), miny = Math.min(...ys), maxy = Math.max(...ys);
      const s = Math.min((W - 40) / (maxx - minx || 1), (H - 40) / (maxy - miny || 1));
      const ox = (W - (maxx - minx) * s) / 2, oy = (H - (maxy - miny) * s) / 2;
      ctx.beginPath();
      ring.forEach((p, k) => { const x = ox + (p[0] * kx - minx) * s, y = H - (oy + (p[1] - miny) * s); k ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
      ctx.closePath(); ctx.fillStyle = "rgba(130,195,65,.35)"; ctx.fill(); ctx.strokeStyle = "#173a2b"; ctx.lineWidth = 2.5; ctx.stroke();
      ctx.fillStyle = "#173a2b"; ctx.font = "bold 12px Inter, sans-serif";
      ctx.fillText(`${fmt(q.geometry?.area_ha, 2)} ha · ${fmt(q.geometry?.perimeter_km, 3)} km`, 10, 18);
    }
    const yrs = q.climate_history?.per_year || [];
    if ($("#hydrology-chart") && yrs.length) charts.push(new Chart($("#hydrology-chart"), {
      type: "bar",
      data: { labels: yrs.map((y) => y.year), datasets: [
        { label: "Precip (mm)", data: yrs.map((y) => y.precip_mm), backgroundColor: "rgba(37,99,235,.55)" },
        { type: "line", label: "ET₀ (mm)", data: yrs.map((y) => y.et0_pm_mm), borderColor: "#d97706", backgroundColor: "#d97706", tension: 0.3 },
      ] },
      options: { maintainAspectRatio: false, plugins: { legend: { position: "bottom", labels: { font: { size: 11 } } } } },
    }));
    if ($("#scenario-bar-chart") && cands.length) charts.push(new Chart($("#scenario-bar-chart"), {
      type: "bar",
      data: { labels: cands.map((c) => `[${c.candidate}] ${c.sequence.map((x) => cname(x)[0]).join("→")}`), datasets: [
        { label: "Mean ETc (mm)", data: cands.map((c) => c.mean_season_etc_mm), backgroundColor: cands.map((_, k) => (k === i ? "#173a2b" : "rgba(36,84,62,.45)")) },
        { label: "Irrigation deficit (mm)", data: cands.map((c) => c.mean_season_irrigation_deficit_mm), backgroundColor: cands.map((_, k) => (k === i ? "#d97706" : "rgba(217,119,6,.4)")) },
      ] },
      options: { maintainAspectRatio: false, plugins: { legend: { position: "bottom", labels: { font: { size: 11 } } } } },
    }));
    const ch = q.climate_history, pp = Object.entries(q.climate_projection?.periods || {});
    const ranges = [...(ch ? [[`${ch.period} obs.`, ch.mean?.precip_mm]] : []), ...pp.map(([k, p]) => [`${k} scen.`, p.precip_mm_per_year])].filter(([, o]) => o);
    if ($("#stability-chart") && ranges.length) charts.push(new Chart($("#stability-chart"), {
      data: { labels: ranges.map(([k]) => k), datasets: [
        { type: "bar", label: "P10–P90 (mm/yr)", data: ranges.map(([, o]) => [o.p10, o.p90]), backgroundColor: "rgba(130,195,65,.5)", borderColor: "#24543e", borderWidth: 1, borderSkipped: false, barPercentage: 0.5 },
        { type: "line", showLine: false, label: "P50", data: ranges.map(([, o]) => o.p50 ?? null), pointStyle: "line", pointRadius: 16, borderWidth: 3, borderColor: "#173a2b" },
      ] },
      options: { maintainAspectRatio: false, scales: { y: { beginAtZero: false, title: { display: true, text: "mm/yr" } } }, plugins: { legend: { position: "bottom", labels: { font: { size: 11 } } } } },
    }));
  }

  // ------------------------------------------------------------------ Tier 2 (engine) → strategy comparison in mockup card style
  const PCT = (o, code) => (code === "A" ? `<strong>baseline</strong> <span class="text-[11px] text-slate-500">(A = reference for %)</span>`
    : !o || o.p50 === null || o.p50 === undefined ? GAP
    : `<span title="${REL_TIP}" class="underline decoration-dotted cursor-help font-bold">${o.p50 > 0 ? "+" : ""}${fmt(o.p50, 0)}%</span><br>${rng(o.p10, o.p90)}`);
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
    if (!fid) { el.innerHTML = ""; return; }
    if (!d || d.__error) { el.innerHTML = errBox("Deep analysis engine unavailable", d?.__error); return; }
    const [sim, prof, bt] = d;
    state.sim = sim;
    const strat = [...sim.strategies].sort((a, b) => a.strategy_code.localeCompare(b.strategy_code));
    const btBy = Object.fromEntries((bt?.results || []).map((r) => [r.strategy_code, r]));
    const cards = strat.map((s) => {
      const hl = matches(s.strategy_code), ref = s.strategy_code === "D";
      const m = s.metrics || {}, wd = m.season_water_deficit_mm || {}, b12 = btBy[s.strategy_code]?.metrics;
      return `<article class="bg-white rounded-3xl p-5 shadow-xl border-2 ${hl ? "border-[#66b888]" : "border-slate-200"} flex flex-col space-y-3">
        <div class="flex items-start justify-between gap-2">
          <div><span class="inline-block whitespace-nowrap px-3 py-1 rounded-full bg-amber-100 text-amber-900 text-xs font-extrabold mb-1.5">Strategy ${esc(s.strategy_code)} · ${esc(s.sequence)}</span>
          <h3 class="text-lg font-extrabold text-[#173a2b] leading-tight">${esc(s.label)}</h3>
          <div class="text-xs text-emerald-700 font-bold">${esc(s.goal_label || "")}</div></div>
          ${hl ? '<span class="shrink-0 px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-900 text-[11px] font-bold">matches your crops</span>' : ""}
          ${ref ? '<span class="shrink-0 px-2.5 py-1 rounded-full bg-slate-100 text-slate-600 text-[11px] font-bold">reference</span>' : ""}
        </div>
        <p class="text-xs text-slate-700"><strong class="text-[#173a2b]">Why:</strong> ${esc(s.why)}</p>
        <div class="grid grid-cols-2 gap-2 text-xs">
          <div class="rounded-xl bg-slate-50 border border-slate-200 p-2.5"><div class="text-[11px] text-slate-500 font-semibold">Season water deficit P50</div><strong class="text-[#173a2b]">${fmt(wd.p50)} mm/yr</strong><div>${rng(wd.p10, wd.p90)}</div><div class="text-[11px] text-amber-800 font-bold">CVaR 10%: ${fmt(wd.cvar)} mm</div></div>
          <div class="rounded-xl bg-slate-50 border border-slate-200 p-2.5"><div class="text-[11px] text-slate-500 font-semibold">2012 drought backtest</div><strong class="text-[#173a2b]">${b12 ? fmt(b12.season_water_deficit_mm) + " mm deficit" : GAP}</strong><div class="text-[11px] text-slate-500">${b12 ? fmt(b12.stress_days) + " stress days" : ""}</div></div>
          <div class="rounded-xl bg-slate-50 border border-slate-200 p-2.5"><div class="text-[11px] text-slate-500 font-semibold">Winter bare days P50</div><strong class="text-[#173a2b]">${m.winter_bare_days?.p50 != null ? fmt(m.winter_bare_days.p50) + " days" : GAP}</strong></div>
          <div class="rounded-xl bg-slate-50 border border-slate-200 p-2.5"><div class="text-[11px] text-slate-500 font-semibold">Water use vs A</div>${PCT(s.display?.water_use_pct, s.strategy_code)}</div>
        </div>
        <div class="rounded-2xl bg-emerald-50 border border-emerald-200 p-3 text-xs"><div class="font-extrabold uppercase tracking-wider text-emerald-900 mb-1">✅ Benefits</div><ul class="list-disc ml-4 text-slate-800">${(s.benefits || []).map((x) => `<li>${esc(x)}</li>`).join("") || `<li>${GAP}</li>`}</ul></div>
        <div class="rounded-2xl bg-amber-50 border border-amber-200 p-3 text-xs"><div class="font-extrabold uppercase tracking-wider text-amber-900 mb-1">⚠️ Trade-offs</div><ul class="list-disc ml-4 text-slate-800">${(s.cons || []).map((x) => `<li>${esc(x)}</li>`).join("") || "<li>none listed</li>"}</ul></div>
        <details class="ev text-xs rounded-xl bg-slate-100 border border-slate-200 px-3 py-2"><summary class="font-bold text-[#173a2b] cursor-pointer">Evidence (${(s.evidence || []).length} sources)</summary><ul class="ml-1 text-slate-600">${(s.evidence || []).map((x) => `<li>• ${x.url ? `<a class="underline" target="_blank" rel="noopener" href="${esc(x.url)}">${esc(x.quote || x.url)}</a>` : esc(x.quote || "")}${x.doi ? ` (doi:${esc(x.doi)})` : ""}</li>`).join("")}</ul></details>
        <div class="text-xs"><div class="font-bold text-slate-700">Information gaps</div><ul class="list-disc ml-4 text-slate-600">${(s.info_gaps || []).map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>
        <div class="text-xs"><div class="font-bold text-red-800">Check locally</div><ul class="list-disc ml-4 text-slate-700">${(s.local_review_risks || []).map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>
        <div class="mt-auto"><button data-explain="${esc(s.strategy_code)}" class="w-full px-3 py-2.5 rounded-xl bg-[#173a2b] text-white text-xs font-bold hover:bg-[#24543e]">Explain this strategy (AI, numbers from engine only)</button>
        <div class="explain-out mt-2 text-xs text-slate-700 whitespace-pre-wrap"></div></div>
      </article>`;
    }).join("");
    const risks = [...new Set(strat.flatMap((s) => s.local_review_risks || []))];
    el.innerHTML = `
      <div class="space-y-5 mt-2">
        <div class="bg-[#173a2b] text-white rounded-2xl px-5 py-3.5 shadow-lg border border-emerald-400/30 flex flex-wrap items-center justify-between gap-3">
          <div class="text-xs sm:text-sm font-bold leading-snug"><span class="text-amber-300 font-extrabold">[Strategy comparison · Deep Analysis]</span> pilot field ${esc(fid)} · ${esc(prof.region_label || COUNTY[prof.county_fips] || "")} · Monte Carlo water balance n=${esc(sim.n)}, seed=${esc(sim.seed)}, run ${esc(sim.run_id)}</div>
          <span class="px-3 py-1 rounded-full bg-emerald-500/20 border border-emerald-300/30 text-emerald-200 text-[11px] font-bold">not ranked · D = reference</span>
        </div>
        <div class="bg-white rounded-3xl p-6 shadow-xl border border-slate-200">
          <div class="flex flex-wrap justify-between items-baseline gap-2 mb-2"><div class="text-xs font-extrabold uppercase tracking-wider text-emerald-800">📊 Season water deficit — possible range (P10–P90) and CVaR<sub>10%</sub></div>
          <span class="text-[11px] text-slate-500">mm/yr · bar = P10–P90, line = P50, ◆ = CVaR (mean of worst 10%), ● = 2012 backtest · green = matches your crops · ${esc(sim.cvar_definition)}</span></div>
          <div class="h-72"><canvas id="dist-chart" role="img" aria-label="Season water deficit per strategy: P10–P90 range, P50, CVaR and 2012 backtest; the same values are written on each strategy card below"></canvas></div>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">${cards}</div>
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div class="bg-white rounded-2xl p-5 shadow-md border border-slate-200"><div class="text-xs font-extrabold uppercase tracking-wider text-[#173a2b] mb-2">Information gaps</div>
            <ul class="list-disc ml-5 text-xs text-slate-600">${[...(prof.info_gaps || []), ...(sim.info_gaps || [])].map((x) => `<li>${esc(typeof x === "string" ? x : x.message || x.item || JSON.stringify(x))}</li>`).join("")}</ul></div>
          <div id="s7" class="s7 scroll-mt-16 rounded-2xl bg-amber-50 border border-amber-300 shadow-md p-5"><div class="text-xs font-extrabold uppercase tracking-wider text-[#173a2b] mb-1">S7 · Human judgement checklist</div>
            <p class="text-xs text-slate-600 mb-2">ART FARM does not replace your judgement. Before acting, check these with your agronomist or extension office:</p>
            <ul class="text-xs space-y-1">${risks.map((r) => `<li><label class="flex gap-2"><input type="checkbox" class="mt-0.5"> <span>${esc(r)}</span></label></li>`).join("")}
            <li><label class="flex gap-2"><input type="checkbox" class="mt-0.5"> <span>In-field soil test (not provided by this tool)</span></label></li></ul>
            <p class="text-xs text-slate-600 mt-2">${esc(sim.disclaimer || "")}</p></div>
        </div>
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
          { type: "bar", label: "P10–P90", pointStyle: "rect", data: wd.map((w) => [w.p10, w.p90]), backgroundColor: strat.map((s) => (matches(s.strategy_code) ? "rgba(130,195,65,.55)" : "rgba(36,84,62,.25)")), borderColor: "#24543e", borderWidth: 1, borderSkipped: false, barPercentage: 0.5 },
          { type: "line", showLine: false, label: "P50", data: wd.map((w) => w.p50 ?? null), pointStyle: "line", pointRadius: 18, borderWidth: 3, borderColor: "#173a2b" },
          { type: "line", showLine: false, label: "CVaR 10%", data: wd.map((w) => w.cvar ?? null), pointStyle: "rectRot", pointRadius: 6, backgroundColor: "#d97706" },
          { type: "line", showLine: false, label: "2012 backtest", data: strat.map((s) => btBy[s.strategy_code]?.metrics?.season_water_deficit_mm ?? null), pointRadius: 6, backgroundColor: "#b91c1c" },
        ],
      },
      options: { maintainAspectRatio: false, scales: { y: { title: { display: true, text: "mm/yr" }, beginAtZero: true } }, plugins: { legend: { position: "bottom", labels: { usePointStyle: true, font: { size: 12 } } } } },
    });
  }
  async function explain(btn, fid) {
    const out = btn.nextElementSibling, code = btn.dataset.explain;
    btn.disabled = true; out.textContent = "Asking the explainer (numbers come only from engine tool calls)…";
    try {
      const r = await api("/explain", { body: { field_id: fid, strategy_code: code, lang: "en", question: `Why might strategy ${code} fit or not fit this field, and what should I check locally?` } });
      out.textContent = (r.answer || "").replace(/\*\*/g, "") + (r.insufficient_evidence ? "\n[insufficient evidence in the library]" : "") + "\n— AI-generated explanation (SI); verify locally.";
    } catch (e) { if (e.needsLive) { out.innerHTML = "AI explanation is available on the live server." + liveLink(); btn.disabled = false; return; } out.textContent = "Explanation unavailable — " + friendly(e.message) + " (detail: " + e.message + ")"; }
    btn.disabled = false;
  }

  // deep link
  const h = location.hash.replace("#", "");
  if (h && $("#page-" + h) && h !== "loading" && h !== "results") show("page-" + h);
})();
