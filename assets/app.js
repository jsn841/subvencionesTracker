/* Ayudas de España al exterior — lógica de la web (sin dependencias salvo ECharts y SheetJS). */
(() => {
  "use strict";

  // ---------- Textos por capa ----------
  const LAYERS = {
    aod: {
      tab: "Ayuda al desarrollo (OCDE)",
      nota: "Ayuda Oficial al Desarrollo que España comunica a la OCDE (Creditor Reporting System), proyecto a proyecto, de todas las administraciones: Estado, comunidades autónomas, entidades locales y universidades. Importes publicados en dólares y convertidos a euros con el tipo de cambio medio anual del BCE.",
      medidas: { imp: "Desembolsado", imp2: "Comprometido" },
      benef: "Canal o entidad receptora",
      org: "Organismo español que informa",
    },
    bdns: {
      tab: "Concesiones registradas (BDNS)",
      nota: "Concesiones de subvenciones y ayudas inscritas en la Base de Datos Nacional de Subvenciones cuya convocatoria tiene como destino un país extranjero o la cooperación internacional. La consulta pública de la BDNS solo muestra los últimos cuatro años; esta web conserva lo descargado desde el inicio.",
      medidas: { imp: "Importe concedido", imp2: "Ayuda equivalente" },
      benef: "Beneficiario",
      org: "Ministerio u organismo",
    },
    iati: {
      tab: "Actividades de AECID (IATI)",
      nota: "Actividades que la Agencia Española de Cooperación Internacional para el Desarrollo (AECID) publica en el estándar internacional IATI. Son años recientes y la mayor parte también figura en los datos de la OCDE cuando estos se publican.",
      medidas: { imp: "Desembolsado", imp2: "Comprometido" },
      benef: "Organización receptora",
      org: "Ministerio",
    },
  };
  const NO_SUMA = "Cada fuente se muestra por separado y sus cifras no se suman entre sí, porque una misma ayuda puede aparecer en más de una.";
  const DICT_COLS = ["b", "bt", "p", "pn", "r", "adm", "org", "org2", "ins", "mod", "cat", "sec", "crit"];
  const MS_FIELDS = ["pn", "r", "adm", "org", "ins", "mod", "sec"];
  const FIELD_LABEL = { pn: "País o destino", r: "Región", adm: "Administración", org: "Ministerio u organismo", ins: "Instrumento", mod: "Tipo de ayuda", sec: "Sector o finalidad" };
  const PAGE_SIZE = 50;

  // ---------- Formatos ----------
  const grouping = (() => { try { new Intl.NumberFormat("es-ES", { useGrouping: "always" }).format(1000); return "always"; } catch { return true; } })();
  const fmtEUR = new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR", maximumFractionDigits: 0, useGrouping: grouping });
  const fmtEUR2 = new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR", minimumFractionDigits: 2, maximumFractionDigits: 2, useGrouping: grouping });
  const fmtUSD = new Intl.NumberFormat("es-ES", { style: "currency", currency: "USD", maximumFractionDigits: 0, useGrouping: grouping });
  const fmtInt = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 0, useGrouping: grouping });
  const fmt1 = new Intl.NumberFormat("es-ES", { minimumFractionDigits: 1, maximumFractionDigits: 1, useGrouping: grouping });
  const eur = (v) => (v == null || Number.isNaN(v) ? "—" : fmtEUR.format(v));
  function enPalabras(v) {
    const a = Math.abs(v);
    if (a >= 1e9) return `${fmt1.format(v / 1e9)} mil millones de euros`;
    if (a >= 1e6) return `${fmt1.format(v / 1e6)} millones de euros`;
    if (a >= 1e3) return `${fmt1.format(v / 1e3)} mil euros`;
    return `${fmtInt.format(v)} euros`;
  }
  function compacto(v) {
    const a = Math.abs(v);
    if (a >= 1e9) return `${fmt1.format(v / 1e9)} mil M€`;
    if (a >= 1e6) return `${fmt1.format(v / 1e6)} M€`;
    if (a >= 1e3) return `${fmtInt.format(v / 1e3)} mil €`;
    return `${fmtInt.format(v)} €`;
  }
  const norm = (s) => (s || "").toString().normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const esc = (s) => (s == null ? "" : String(s)).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const cut = (s, n) => (s && s.length > n ? s.slice(0, n - 1) + "…" : s || "");
  const $ = (id) => document.getElementById(id);

  // ---------- Estado ----------
  const state = {
    layer: "aod", measure: "imp", sel: {}, texto: "", benef: "", y0: null, y1: null, min: null, max: null,
    sort: { key: "imp", dir: -1 }, page: 0,
  };
  let manifest = null;
  const stores = {};
  let store = null;          // datos de la capa activa
  let filtered = new Uint32Array(0);
  let sortedCache = null;
  const charts = {};
  let countryNames = {};     // ISO3 -> nombre en español
  let mapReady = null;

  // ---------- Carga de datos ----------
  async function fetchJSON(url) {
    const r = await fetch(url, { cache: "no-cache" });
    if (!r.ok) throw new Error(`${url}: ${r.status}`);
    return r.json();
  }

  async function loadLayer(layer) {
    if (stores[layer]) return stores[layer];
    const info = manifest.capas[layer];
    const files = info.anios.filter((a) => a.registros > 0);
    const total = files.reduce((s, a) => s + a.registros, 0);
    const S = {
      layer, n: 0, years: info.anios.map((a) => a.anio).sort((a, b) => a - b),
      dict: {}, dictIndex: {}, cols: {}, search: null,
    };
    for (const c of DICT_COLS) { S.dict[c] = []; S.dictIndex[c] = new Map(); S.cols[c] = new Int32Array(total); }
    for (const c of ["id", "ref", "f", "t", "url", "nota"]) S.cols[c] = new Array(total);
    S.cols.a = new Int16Array(total);
    for (const c of ["imp", "imp2", "usd", "usd2"]) S.cols[c] = new Float64Array(total);
    const hasNum = { imp: false, imp2: false, usd: false, usd2: false };

    const prog = $("progress");
    prog.hidden = false;
    let done = 0;
    const update = () => {
      $("progress-bar").style.width = `${(100 * done) / Math.max(files.length, 1)}%`;
      $("progress-text").textContent = `Descargando datos: ${done} de ${files.length} años`;
    };
    update();
    const results = new Array(files.length);
    let next = 0;
    async function worker() {
      while (next < files.length) {
        const i = next++;
        results[i] = await fetchJSON(files[i].archivo);
        done++; update();
      }
    }
    await Promise.all(Array.from({ length: Math.min(6, files.length) }, worker));
    const regionPorPais = manifest.region_por_pais || {};
    for (const d of results) {
      const ci = Object.fromEntries(d.cols.map((c, i) => [c, i]));
      const remap = {};
      for (const c of DICT_COLS) {
        const local = d.dict[c] || [];
        remap[c] = local.map((v) => {
          if (c === "r" && !v) return null; // se rellena después según el país
          let g = S.dictIndex[c].get(v);
          if (g === undefined) { g = S.dict[c].length; S.dict[c].push(v); S.dictIndex[c].set(v, g); }
          return g;
        });
      }
      for (const row of d.rows) {
        const k = S.n++;
        for (const c of DICT_COLS) {
          let g = remap[c][row[ci[c]]];
          if (c === "r" && g === null) {
            const pais = d.dict.p[row[ci.p]];
            const v = regionPorPais[pais] || "Sin especificar";
            g = S.dictIndex.r.get(v);
            if (g === undefined) { g = S.dict.r.length; S.dict.r.push(v); S.dictIndex.r.set(v, g); }
          }
          S.cols[c][k] = g;
        }
        for (const c of ["id", "ref", "f", "t", "url", "nota"]) S.cols[c][k] = row[ci[c]] === "" ? null : row[ci[c]];
        S.cols.a[k] = row[ci.a] || 0;
        for (const c of ["imp", "imp2", "usd", "usd2"]) {
          const v = row[ci[c]];
          if (v === "" || v == null) S.cols[c][k] = NaN; else { S.cols[c][k] = +v; hasNum[c] = true; }
        }
      }
    }
    S.hasNum = hasNum;
    prog.hidden = true;
    stores[layer] = S;
    return S;
  }

  function buildSearch(S) {
    if (S.search) return S.search;
    const C = S.cols, D = S.dict;
    S.search = new Array(S.n);
    for (let i = 0; i < S.n; i++) {
      S.search[i] = norm(`${C.t[i] || ""} ${D.b[C.b[i]]} ${D.pn[C.pn[i]]} ${D.org[C.org[i]]} ${D.org2[C.org2[i]]} ${C.ref[i] || ""} ${D.sec[C.sec[i]]} ${D.mod[C.mod[i]]}`);
    }
    return S.search;
  }

  // ---------- Filtros ----------
  function applyFilters() {
    const S = store, C = S.cols, m = C[state.measure];
    const masks = {};
    for (const f of MS_FIELDS) {
      const sel = state.sel[f];
      if (sel && sel.size) {
        const mk = new Uint8Array(S.dict[f].length);
        for (const v of sel) { const g = S.dictIndex[f].get(v); if (g !== undefined) mk[g] = 1; }
        masks[f] = mk;
      }
    }
    const words = norm(state.texto).split(/\s+/).filter(Boolean);
    const search = words.length ? buildSearch(S) : null;
    const benef = norm(state.benef);
    let bmask = null;
    if (benef) {
      bmask = new Uint8Array(S.dict.b.length);
      S.dict.b.forEach((v, i) => { if (norm(v).includes(benef)) bmask[i] = 1; });
    }
    const y0 = state.y0 ?? -Infinity, y1 = state.y1 ?? Infinity;
    const mn = state.min ?? -Infinity, mx = state.max ?? Infinity;
    const out = new Uint32Array(S.n);
    let k = 0;
    const mf = Object.keys(masks);
    outer: for (let i = 0; i < S.n; i++) {
      const y = C.a[i];
      if (y < y0 || y > y1) continue;
      for (const f of mf) if (!masks[f][C[f][i]]) continue outer;
      if (bmask && !bmask[C.b[i]]) continue;
      if (state.min != null || state.max != null) {
        const v = m[i];
        if (Number.isNaN(v) || v < mn || v > mx) continue;
      }
      if (search) { const s = search[i]; for (const w of words) if (!s.includes(w)) continue outer; }
      out[k++] = i;
    }
    filtered = out.subarray(0, k);
    sortedCache = null;
    state.page = 0;
  }

  // ---------- Selectores múltiples ----------
  const msWidgets = {};
  function buildMultiSelects() {
    document.querySelectorAll("[data-ms]").forEach((field) => {
      const key = field.dataset.ms;
      field.querySelector(".ms-btn")?.remove();
      field.querySelector(".ms-pop")?.remove();
      const btn = document.createElement("button");
      btn.type = "button"; btn.className = "ms-btn"; btn.setAttribute("aria-haspopup", "listbox"); btn.setAttribute("aria-expanded", "false");
      field.appendChild(btn);
      msWidgets[key] = { btn, field };
      btn.addEventListener("click", () => togglePop(key));
      refreshMsButton(key);
    });
  }
  function refreshMsButton(key) {
    const w = msWidgets[key]; if (!w) return;
    const sel = state.sel[key];
    const n = sel ? sel.size : 0;
    w.btn.textContent = n === 0 ? "Todos" : n === 1 ? [...sel][0] : `${n} seleccionados`;
    w.btn.classList.toggle("active", n > 0);
    w.btn.title = n ? [...sel].join(" · ") : "Todos";
  }
  function optionTotals(key) {
    // importe de cada opción dentro de los datos de la capa (sin filtros), para ordenar
    const S = store, col = S.cols[key], m = S.cols[state.measure];
    const tot = new Float64Array(S.dict[key].length), cnt = new Uint32Array(S.dict[key].length);
    for (let i = 0; i < S.n; i++) { const g = col[i]; cnt[g]++; const v = m[i]; if (!Number.isNaN(v)) tot[g] += v; }
    return S.dict[key].map((v, g) => ({ v, tot: tot[g], cnt: cnt[g] })).filter((o) => o.v !== "" && o.cnt > 0).sort((a, b) => b.tot - a.tot);
  }
  let openPop = null;
  function closePop() {
    if (!openPop) return;
    openPop.pop.remove(); openPop.btn.setAttribute("aria-expanded", "false"); openPop = null;
  }
  function togglePop(key) {
    if (openPop && openPop.key === key) return closePop();
    closePop();
    const w = msWidgets[key];
    const pop = document.createElement("div");
    pop.className = "ms-pop";
    pop.innerHTML = `<input type="search" placeholder="Buscar…" aria-label="Buscar opción"><div class="ms-list" role="listbox" aria-multiselectable="true"></div>
      <div class="ms-actions"><button type="button" class="btn-link" data-a="clear">Quitar selección</button><button type="button" class="btn" data-a="close">Aplicar</button></div>`;
    w.field.appendChild(pop);
    w.btn.setAttribute("aria-expanded", "true");
    openPop = { key, pop, btn: w.btn };
    const opts = optionTotals(key);
    const list = pop.querySelector(".ms-list");
    const sel = state.sel[key] || (state.sel[key] = new Set());
    const draw = (q) => {
      const nq = norm(q);
      const shown = opts.filter((o) => !nq || norm(o.v).includes(nq)).slice(0, 400);
      list.innerHTML = shown.map((o, i) => `<label class="ms-opt"><input type="checkbox" data-i="${i}" ${sel.has(o.v) ? "checked" : ""}><span>${esc(o.v)}</span><small>${compacto(o.tot)}</small></label>`).join("")
        || `<div class="empty">Sin coincidencias</div>`;
      list.querySelectorAll("input").forEach((cb) => cb.addEventListener("change", () => {
        const v = shown[+cb.dataset.i].v;
        cb.checked ? sel.add(v) : sel.delete(v);
        refreshMsButton(key); scheduleUpdate();
      }));
    };
    draw("");
    const search = pop.querySelector("input[type=search]");
    search.addEventListener("input", () => draw(search.value));
    pop.querySelector('[data-a="clear"]').addEventListener("click", () => { sel.clear(); refreshMsButton(key); draw(search.value); scheduleUpdate(); });
    pop.querySelector('[data-a="close"]').addEventListener("click", closePop);
    search.focus();
  }
  document.addEventListener("click", (e) => { if (openPop && !openPop.pop.contains(e.target) && e.target !== openPop.btn) closePop(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && openPop) { const b = openPop.btn; closePop(); b.focus(); } });

  function renderActiveFilters() {
    const box = $("active-filters");
    const chips = [];
    for (const f of MS_FIELDS) for (const v of state.sel[f] || []) chips.push({ label: `${FIELD_LABEL[f]}: ${v}`, clear: () => { state.sel[f].delete(v); refreshMsButton(f); } });
    if (state.texto) chips.push({ label: `Texto: “${state.texto}”`, clear: () => { state.texto = ""; $("f-texto").value = ""; } });
    if (state.benef) chips.push({ label: `Beneficiario: “${state.benef}”`, clear: () => { state.benef = ""; $("f-benef").value = ""; } });
    const ys = store.years;
    if (state.y0 != null && state.y0 !== ys[0]) chips.push({ label: `Desde ${state.y0}`, clear: () => { state.y0 = null; $("f-anio-desde").value = ys[0]; } });
    if (state.y1 != null && state.y1 !== ys[ys.length - 1]) chips.push({ label: `Hasta ${state.y1}`, clear: () => { state.y1 = null; $("f-anio-hasta").value = ys[ys.length - 1]; } });
    if (state.min != null) chips.push({ label: `Importe ≥ ${eur(state.min)}`, clear: () => { state.min = null; $("f-min").value = ""; } });
    if (state.max != null) chips.push({ label: `Importe ≤ ${eur(state.max)}`, clear: () => { state.max = null; $("f-max").value = ""; } });
    box.innerHTML = "";
    chips.forEach((c) => {
      const el = document.createElement("span");
      el.className = "chip";
      el.innerHTML = `<span>${esc(c.label)}</span><button type="button" aria-label="Quitar filtro ${esc(c.label)}">×</button>`;
      el.querySelector("button").addEventListener("click", () => { c.clear(); scheduleUpdate(); });
      box.appendChild(el);
    });
  }

  // ---------- Totales ----------
  function renderTotals() {
    const S = store, C = S.cols, m = C[state.measure];
    let tot = 0, conImporte = 0, sinImporte = 0;
    const paises = new Set();
    let ymin = Infinity, ymax = -Infinity;
    for (const i of filtered) {
      const v = m[i];
      if (Number.isNaN(v)) sinImporte++; else { tot += v; conImporte++; }
      paises.add(C.pn[i]);
      if (C.a[i] < ymin) ymin = C.a[i];
      if (C.a[i] > ymax) ymax = C.a[i];
    }
    const L = LAYERS[state.layer];
    $("hero-label").textContent = `Total ${L.medidas[state.measure].toLowerCase()} · ${manifest.capas[state.layer].corto}`;
    $("hero-value").textContent = eur(tot);
    $("hero-words").textContent = filtered.length ? enPalabras(tot) : "Ningún registro cumple los filtros";
    const foot = [];
    if (state.layer === "aod") {
      let usd = 0; const mu = state.measure === "imp" ? C.usd : C.usd2;
      for (const i of filtered) { const v = mu[i]; if (!Number.isNaN(v)) usd += v; }
      foot.push(`Euros corrientes de cada año, convertidos desde ${fmtUSD.format(usd)} publicados por la OCDE.`);
    } else {
      foot.push("Euros corrientes, tal como los publica la fuente.");
    }
    if (sinImporte) foot.push(`${fmtInt.format(sinImporte)} registros sin importe en euros no se suman.`);
    foot.push(NO_SUMA);
    $("hero-foot").textContent = foot.join(" ");
    $("s-n").textContent = fmtInt.format(filtered.length);
    $("s-paises").textContent = fmtInt.format(paises.size);
    $("s-periodo").textContent = filtered.length ? (ymin === ymax ? `${ymin}` : `${ymin}–${ymax}`) : "—";
    $("s-media").textContent = conImporte ? eur(tot / conImporte) : "—";
  }

  // ---------- Gráficas ----------
  function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
  function baseTextStyle() { return { color: css("--text-2"), fontFamily: getComputedStyle(document.body).fontFamily }; }
  function chart(id) {
    if (!charts[id]) charts[id] = echarts.init($(id), null, { renderer: "canvas" });
    return charts[id];
  }
  function tooltipBase() {
    return { backgroundColor: css("--surface"), borderColor: css("--border"), textStyle: { color: css("--text") }, confine: true };
  }
  function groupBy(col, limit) {
    const S = store, C = S.cols, m = C[state.measure];
    const tot = new Float64Array(S.dict[col].length), cnt = new Uint32Array(S.dict[col].length);
    for (const i of filtered) { const g = C[col][i]; const v = m[i]; cnt[g]++; if (!Number.isNaN(v)) tot[g] += v; }
    const arr = [];
    for (let g = 0; g < tot.length; g++) if (cnt[g]) arr.push({ g, name: S.dict[col][g], value: tot[g], n: cnt[g] });
    arr.sort((a, b) => b.value - a.value);
    return limit ? arr.slice(0, limit) : arr;
  }
  function barRanking(id, items, extraTooltip) {
    const ch = chart(id);
    const data = items.slice().reverse();
    ch.setOption({
      animation: false,
      textStyle: baseTextStyle(),
      grid: { left: 18, right: 76, top: 6, bottom: 6, containLabel: true },
      tooltip: { ...tooltipBase(), trigger: "item", formatter: (p) => `<strong>${esc(p.data.full)}</strong><br>${eur(p.value)}<br>${fmtInt.format(p.data.n)} registros${extraTooltip ? extraTooltip(p.data) : ""}` },
      xAxis: { type: "value", axisLabel: { show: false }, splitLine: { show: false } },
      yAxis: { type: "category", data: data.map((d) => cut(d.name, $(id).clientWidth < 480 ? 22 : 38)), axisTick: { show: false }, axisLine: { lineStyle: { color: css("--border") } }, axisLabel: { color: css("--text-2") } },
      series: [{
        type: "bar", barMaxWidth: 22, itemStyle: { color: css("--series-1"), borderRadius: [0, 4, 4, 0] },
        label: { show: true, position: "right", formatter: (p) => compacto(p.value), color: css("--text-2") },
        data: data.map((d) => ({ value: d.value, full: d.name, n: d.n })),
      }],
    }, true);
  }
  function renderAnnual() {
    const S = store, C = S.cols, m = C[state.measure];
    const ys = S.years;
    if (!ys.length) return;
    const y0 = Math.max(ys[0], state.y0 ?? ys[0]), y1 = Math.min(ys[ys.length - 1], state.y1 ?? ys[ys.length - 1]);
    const tot = new Map();
    for (const i of filtered) { const v = m[i]; if (!Number.isNaN(v)) tot.set(C.a[i], (tot.get(C.a[i]) || 0) + v); }
    const conArchivo = new Set(manifest.capas[state.layer].anios.filter((a) => a.registros > 0).map((a) => a.anio));
    const years = [], vals = [], sinDatos = [];
    for (let y = y0; y <= y1; y++) {
      years.push(String(y));
      if (!conArchivo.has(y)) { vals.push(null); sinDatos.push(y); } else vals.push(tot.get(y) || 0);
    }
    $("c-anual-sub").textContent = `${LAYERS[state.layer].medidas[state.measure]}, euros corrientes.` + (sinDatos.length ? ` Sin datos publicados por la fuente: ${sinDatos.join(", ")}.` : "");
    chart("c-anual").setOption({
      animation: false,
      textStyle: baseTextStyle(),
      grid: { left: 8, right: 16, top: 24, bottom: 8, containLabel: true },
      tooltip: { ...tooltipBase(), trigger: "axis", axisPointer: { type: "shadow" }, formatter: (ps) => { const p = ps[0]; return `<strong>${p.name}</strong><br>${p.value == null ? "Sin datos en la fuente" : eur(p.value)}`; } },
      xAxis: { type: "category", data: years, axisTick: { show: false }, axisLine: { lineStyle: { color: css("--border") } }, axisLabel: { color: css("--text-3") } },
      yAxis: { type: "value", axisLabel: { formatter: compacto, color: css("--text-3") }, splitLine: { lineStyle: { color: css("--grid") } } },
      series: [{ type: "bar", barMaxWidth: 24, itemStyle: { color: css("--series-1"), borderRadius: [4, 4, 0, 0] }, data: vals }],
    }, true);
  }
  async function ensureMap() {
    if (mapReady) return mapReady;
    mapReady = (async () => {
      const [topo, countries] = await Promise.all([fetchJSON("assets/geo/world-50m.topo.json"), fetchJSON("assets/geo/countries.json")]);
      const numToIso = {};
      for (const [a3, v] of Object.entries(countries)) { numToIso[v.n] = a3; countryNames[a3] = v.es; }
      const geo = topojson.feature(topo, topo.objects.countries);
      geo.features = geo.features.filter((f) => f.properties.name !== "Antarctica");
      for (const f of geo.features) {
        let iso = f.id ? numToIso[f.id] : null;
        if (!iso && f.properties.name === "Kosovo") iso = "XKX";
        f.properties = { iso: iso || `X-${f.properties.name}`, nombre: (iso && countryNames[iso]) || f.properties.name };
      }
      echarts.registerMap("mundo", geo);
    })();
    return mapReady;
  }
  async function renderMap() {
    await ensureMap();
    const items = groupBy("p");
    const S = store;
    const pnByP = new Map();
    for (const i of filtered) { const g = S.cols.p[i]; if (!pnByP.has(g)) pnByP.set(g, S.dict.pn[S.cols.pn[i]]); }
    let fuera = 0;
    const data = [];
    for (const it of items) {
      const code = it.name;
      if (/^[A-Z]{3}$/.test(code) && !["XNE", "XWW", "XUN"].includes(code)) data.push({ name: code, value: it.value, nombre: pnByP.get(it.g), n: it.n });
      else fuera += it.value;
    }
    const vals = data.map((d) => d.value).filter((v) => v > 0).sort((a, b) => a - b);
    const q = (p) => vals.length ? vals[Math.min(vals.length - 1, Math.floor(p * vals.length))] : 0;
    const cuts = [q(0.5), q(0.75), q(0.9), q(0.97)].filter((v, i, a) => v > 0 && a.indexOf(v) === i);
    const colors = [css("--seq-0"), css("--seq-1"), css("--seq-2"), css("--seq-3"), css("--seq-4")];
    const pieces = [];
    let prev = 0;
    cuts.forEach((c, i) => { pieces.push({ gt: prev, lte: c, label: `${compacto(prev)} – ${compacto(c)}`, color: colors[i] }); prev = c; });
    pieces.push({ gt: prev, label: `Más de ${compacto(prev)}`, color: colors[Math.min(cuts.length, 4)] });
    $("c-mapa-sub").textContent = data.length
      ? `Importe recibido por país. ${fuera > 0 ? `Además, ${eur(fuera)} van a varios países, a regiones o a destinos no especificados y no aparecen en el mapa.` : ""}`
      : "Ningún registro filtrado está asignado a un país concreto.";
    chart("c-mapa").setOption({
      animation: false,
      textStyle: baseTextStyle(),
      tooltip: { ...tooltipBase(), trigger: "item", formatter: (p) => p.data ? `<strong>${esc(p.data.nombre || countryNames[p.name] || p.name)}</strong><br>${eur(p.data.value)}<br>${fmtInt.format(p.data.n)} registros` : `${esc(countryNames[p.name] || p.name)}<br>Sin registros con los filtros actuales` },
      visualMap: { type: "piecewise", pieces, left: 8, bottom: 8, orient: "vertical", itemWidth: 14, itemHeight: 10, textStyle: { color: css("--text-2"), fontSize: 11 }, backgroundColor: "transparent" },
      series: [{
        type: "map", map: "mundo", nameProperty: "iso", roam: true, scaleLimit: { min: 1, max: 12 },
        itemStyle: { areaColor: css("--map-empty"), borderColor: css("--surface"), borderWidth: 0.5 },
        emphasis: { label: { show: false }, itemStyle: { areaColor: css("--accent-soft") } },
        select: { disabled: true },
        data,
      }],
    }, true);
  }
  function renderCharts() {
    renderAnnual();
    barRanking("c-paises", groupBy("pn", 15));
    const org = groupBy("org");
    const top = org.slice(0, 12);
    if (org.length > 12) {
      const rest = org.slice(12);
      top.push({ name: `Resto (${rest.length} organismos)`, value: rest.reduce((s, d) => s + d.value, 0), n: rest.reduce((s, d) => s + d.n, 0) });
    }
    barRanking("c-org", top);
    $("c-benef-sub").textContent = `Los 15 primeros · ${LAYERS[state.layer].benef}` + (state.layer === "bdns" ? ". Las personas físicas aparecen agrupadas y sin nombre." : "");
    barRanking("c-benef", groupBy("b", 15));
    renderMap().catch((e) => { $("c-mapa-sub").textContent = "No se pudo cargar el mapa."; console.error(e); });
  }

  // ---------- Tabla ----------
  function sortedIdx() {
    if (sortedCache) return sortedCache;
    const S = store, C = S.cols, { key, dir } = state.sort;
    const arr = Array.from(filtered);
    if (key === "imp") { const m = C[state.measure]; arr.sort((a, b) => dir * (((Number.isNaN(m[a]) ? -Infinity : m[a]) - (Number.isNaN(m[b]) ? -Infinity : m[b]))) || C.a[b] - C.a[a]); }
    else if (key === "a") arr.sort((a, b) => dir * (C.a[a] - C.a[b] || String(C.f[a] || "").localeCompare(String(C.f[b] || ""))));
    else if (DICT_COLS.includes(key)) { const d = S.dict[key], col = C[key]; arr.sort((a, b) => dir * d[col[a]].localeCompare(d[col[b]], "es")); }
    else { const col = C[key]; arr.sort((a, b) => dir * String(col[a] || "").localeCompare(String(col[b] || ""), "es")); }
    sortedCache = arr;
    return arr;
  }
  function renderTable() {
    const S = store, C = S.cols, D = S.dict, m = C[state.measure];
    const idx = sortedIdx();
    const pages = Math.max(1, Math.ceil(idx.length / PAGE_SIZE));
    state.page = Math.min(state.page, pages - 1);
    const slice = idx.slice(state.page * PAGE_SIZE, (state.page + 1) * PAGE_SIZE);
    const tb = $("tabla").querySelector("tbody");
    tb.innerHTML = slice.length ? slice.map((i) => `<tr data-i="${i}" tabindex="0">
        <td>${C.f[i] ? esc(C.f[i]) : C.a[i]}</td>
        <td class="title">${esc(cut(C.t[i], 140))}</td>
        <td>${esc(cut(D.b[C.b[i]], 70))}</td>
        <td>${esc(D.pn[C.pn[i]])}</td>
        <td>${esc(cut(D.org[C.org[i]], 60))}</td>
        <td class="num">${Number.isNaN(m[i]) ? '<span class="muted">sin dato</span>' : eur(m[i])}</td></tr>`).join("")
      : `<tr><td colspan="6" class="empty">Ningún registro cumple los filtros.</td></tr>`;
    $("page-info").textContent = idx.length ? `Página ${state.page + 1} de ${fmtInt.format(pages)} · ${fmtInt.format(idx.length)} registros` : "";
    $("prev").disabled = state.page === 0;
    $("next").disabled = state.page >= pages - 1;
    $("tabla").querySelector("th[data-sort=b]").textContent = LAYERS[state.layer].benef;
    $("tabla").querySelector("th[data-sort=org]").textContent = LAYERS[state.layer].org;
    $("tabla").querySelector("th[data-sort=imp]").textContent = LAYERS[state.layer].medidas[state.measure];
    document.querySelectorAll("#tabla th[data-sort]").forEach((th) => th.setAttribute("aria-sort", th.dataset.sort === state.sort.key ? (state.sort.dir > 0 ? "ascending" : "descending") : "none"));
  }

  // ---------- Ficha ----------
  function enlaceOriginal(i) {
    const S = store, C = S.cols;
    const url = C.url[i];
    if (state.layer === "aod" && url) {
      const ids = url;
      const api = `https://sdmx.oecd.org/dcd-public/rest/data/OECD.DCD.FSD,DSD_CRS@DF_CRS,/ESP.........${ids}.?startPeriod=${C.a[i]}&endPeriod=${C.a[i]}&format=csvfilewithlabels`;
      return [{ href: api, text: "Registro en la API oficial de la OCDE (descarga CSV)" },
        { href: "https://data-explorer.oecd.org/vis?df[ds]=dsDisseminateFinalDMZ&df[id]=DSD_CRS%40DF_CRS&df[ag]=OECD.DCD.FSD", text: "Conjunto de datos CRS en el OCDE Data Explorer" }];
    }
    if (state.layer === "bdns" && url) return [{ href: url, text: "Convocatoria en infosubvenciones.es (incluye sus concesiones)" }];
    if (state.layer === "iati" && url) return [{ href: url, text: "Actividad en d-portal.org (visor oficial de datos IATI)" }];
    return [];
  }
  function openFicha(i) {
    const S = store, C = S.cols, D = S.dict, L = LAYERS[state.layer];
    const info = manifest.capas[state.layer];
    const v = (c) => (DICT_COLS.includes(c) ? D[c][C[c][i]] : C[c][i]);
    const rows = [
      ["Fecha", C.f[i] || `Año ${C.a[i]} (la fuente no da fecha exacta)`],
      [L.benef, v("b")],
      ["Tipo de beneficiario o canal", v("bt")],
      ["País o destino", v("pn") + (v("p") && /^[A-Z]{3}$/.test(v("p")) ? ` (${v("p")})` : "")],
      ["Región", v("r")],
      ["Administración", v("adm")],
      [L.org, v("org")],
      ["Órgano", v("org2")],
      ["Instrumento", v("ins")],
      ["Tipo de ayuda", v("mod")],
      ["Categoría", v("cat")],
      ["Sector o finalidad", v("sec")],
      [L.medidas.imp, Number.isNaN(C.imp[i]) ? null : fmtEUR2.format(C.imp[i])],
      [L.medidas.imp2, Number.isNaN(C.imp2[i]) ? null : fmtEUR2.format(C.imp2[i])],
      ["Desembolsado (USD, publicado)", Number.isNaN(C.usd[i]) ? null : fmtUSD.format(C.usd[i])],
      ["Comprometido (USD, publicado)", Number.isNaN(C.usd2[i]) ? null : fmtUSD.format(C.usd2[i])],
      ["Identificador oficial", C.ref[i]],
      ["Motivo de inclusión", v("crit")],
      ["Observaciones", C.nota[i]],
    ].filter(([, val]) => val != null && val !== "");
    const m = C[state.measure][i];
    const links = enlaceOriginal(i);
    $("ficha-body").innerHTML = `
      <h2 id="ficha-titulo">${esc(C.t[i])}</h2>
      <div class="ficha-amount">${Number.isNaN(m) ? "Sin importe" : fmtEUR2.format(m)}</div>
      <div class="muted">${esc(L.medidas[state.measure])}${state.layer === "aod" ? " · convertido desde dólares con el tipo de cambio medio anual del BCE" : ""}</div>
      <dl>${rows.map(([k, val]) => `<dt>${esc(k)}</dt><dd>${esc(val)}</dd>`).join("")}</dl>
      <div class="src"><strong>Fuente:</strong> ${esc(info.fuente)}.<br>${links.map((l) => `<a href="${esc(l.href)}" target="_blank" rel="noopener">${esc(l.text)}</a>`).join("<br>") || "Esta fuente no ofrece un enlace a cada registro."}</div>`;
    const dlg = $("ficha");
    if (typeof dlg.showModal === "function") dlg.showModal(); else dlg.setAttribute("open", "");
  }

  // ---------- Descargas ----------
  function exportRows() {
    const S = store, C = S.cols, D = S.dict, L = LAYERS[state.layer];
    return sortedIdx().map((i) => {
      const o = {
        "Fuente": manifest.capas[state.layer].corto,
        "Año": C.a[i],
        "Fecha": C.f[i] || "",
        "Título oficial": C.t[i] || "",
        [L.benef]: D.b[C.b[i]],
        "Tipo de beneficiario o canal": D.bt[C.bt[i]],
        "Código país o destino": D.p[C.p[i]],
        "País o destino": D.pn[C.pn[i]],
        "Región": D.r[C.r[i]],
        "Administración": D.adm[C.adm[i]],
        [L.org]: D.org[C.org[i]],
        "Órgano": D.org2[C.org2[i]],
        "Instrumento": D.ins[C.ins[i]],
        "Tipo de ayuda": D.mod[C.mod[i]],
        "Categoría": D.cat[C.cat[i]],
        "Sector o finalidad": D.sec[C.sec[i]],
        [`${L.medidas.imp} (EUR)`]: Number.isNaN(C.imp[i]) ? null : C.imp[i],
        [`${L.medidas.imp2} (EUR)`]: Number.isNaN(C.imp2[i]) ? null : C.imp2[i],
      };
      if (state.layer === "aod") { o["Desembolsado (USD)"] = Number.isNaN(C.usd[i]) ? null : C.usd[i]; o["Comprometido (USD)"] = Number.isNaN(C.usd2[i]) ? null : C.usd2[i]; }
      o["Identificador oficial"] = C.ref[i] || "";
      o["Motivo de inclusión"] = D.crit[C.crit[i]];
      o["Observaciones"] = C.nota[i] || "";
      const l = enlaceOriginal(i)[0];
      o["Enlace"] = l ? l.href : "";
      return o;
    });
  }
  function fileBase() { return `ayudas-exterior_${state.layer}_${new Date().toISOString().slice(0, 10)}`; }
  function download(blob, name) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  }
  function downloadCSV() {
    const rows = exportRows();
    if (!rows.length) return;
    const heads = Object.keys(rows[0]);
    const cell = (v) => {
      if (v == null) return "";
      if (typeof v === "number") return String(v).replace(".", ",");
      const s = String(v);
      return /[;"\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    };
    const csv = "﻿" + [heads.join(";"), ...rows.map((r) => heads.map((h) => cell(r[h])).join(";"))].join("\r\n");
    download(new Blob([csv], { type: "text/csv;charset=utf-8" }), `${fileBase()}.csv`);
  }
  let xlsxLoading = null;
  async function downloadXLSX() {
    const btn = $("dl-xlsx");
    btn.disabled = true; const old = btn.textContent; btn.textContent = "Preparando Excel…";
    try {
      if (!window.XLSX) {
        xlsxLoading = xlsxLoading || new Promise((res, rej) => { const s = document.createElement("script"); s.src = "assets/vendor/xlsx.full.min.js"; s.onload = res; s.onerror = rej; document.head.appendChild(s); });
        await xlsxLoading;
      }
      const rows = exportRows();
      const ws = XLSX.utils.json_to_sheet(rows);
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, "Registros");
      const info = [["Fuente", manifest.capas[state.layer].fuente], ["Descargado", new Date().toISOString()], ["Filtros", ($("active-filters").innerText || "Ninguno").replace(/×/g, "").replace(/\s*\n\s*/g, " · ")], ["Nota", NO_SUMA], ["Metodología", location.href.replace(/index\.html.*|#.*$/, "") + "metodologia.html"]];
      XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(info), "Información");
      XLSX.writeFile(wb, `${fileBase()}.xlsx`, { compression: true });
    } catch (e) {
      alert("No se pudo generar el Excel. Prueba con la descarga CSV.");
      console.error(e);
    } finally { btn.disabled = false; btn.textContent = old; }
  }

  // ---------- URL (para compartir una vista filtrada) ----------
  function writeHash() {
    const p = new URLSearchParams();
    p.set("fuente", state.layer);
    if (state.measure !== "imp") p.set("importe", "2");
    for (const f of MS_FIELDS) if (state.sel[f]?.size) p.set(f, [...state.sel[f]].join("|"));
    if (state.texto) p.set("texto", state.texto);
    if (state.benef) p.set("benef", state.benef);
    if (state.y0 != null) p.set("desde", state.y0);
    if (state.y1 != null) p.set("hasta", state.y1);
    if (state.min != null) p.set("min", state.min);
    if (state.max != null) p.set("max", state.max);
    history.replaceState(null, "", "#" + p.toString());
  }
  function readHash() {
    const p = new URLSearchParams(location.hash.slice(1));
    if (p.get("fuente") && LAYERS[p.get("fuente")]) state.layer = p.get("fuente");
    state.measure = p.get("importe") === "2" ? "imp2" : "imp";
    for (const f of MS_FIELDS) state.sel[f] = new Set(p.get(f) ? p.get(f).split("|") : []);
    state.texto = p.get("texto") || "";
    state.benef = p.get("benef") || "";
    state.y0 = p.get("desde") ? +p.get("desde") : null;
    state.y1 = p.get("hasta") ? +p.get("hasta") : null;
    state.min = p.get("min") ? +p.get("min") : null;
    state.max = p.get("max") ? +p.get("max") : null;
  }

  // ---------- Orquestación ----------
  let pending = null;
  function scheduleUpdate() {
    clearTimeout(pending);
    pending = setTimeout(update, 120);
  }
  function update() {
    if (!store) return;
    applyFilters();
    renderActiveFilters();
    renderTotals();
    renderCharts();
    renderTable();
    writeHash();
  }

  function renderLayerTabs() {
    const box = $("layer-tabs");
    box.innerHTML = "";
    for (const [k, L] of Object.entries(LAYERS)) {
      const info = manifest.capas[k];
      const ys = info.anios.filter((a) => a.registros > 0).map((a) => a.anio);
      const n = info.anios.reduce((s, a) => s + a.registros, 0);
      const b = document.createElement("button");
      b.type = "button"; b.className = "layer-tab"; b.setAttribute("role", "tab");
      b.setAttribute("aria-selected", String(k === state.layer));
      b.disabled = n === 0;
      b.innerHTML = `<strong>${esc(L.tab)}</strong><span>${ys.length ? `${Math.min(...ys)}–${Math.max(...ys)} · ${fmtInt.format(n)} registros` : "Sin datos todavía"}</span>`;
      b.addEventListener("click", () => switchLayer(k, true));
      box.appendChild(b);
    }
    $("layer-note").textContent = `${LAYERS[state.layer].nota} ${NO_SUMA}`;
  }
  function renderMeasureToggle() {
    const box = $("measure-toggle");
    box.innerHTML = "";
    for (const [k, label] of Object.entries(LAYERS[state.layer].medidas)) {
      const b = document.createElement("button");
      b.type = "button"; b.setAttribute("role", "radio"); b.setAttribute("aria-checked", String(state.measure === k));
      b.textContent = label;
      b.addEventListener("click", () => { state.measure = k; sortedCache = null; renderMeasureToggle(); update(); });
      box.appendChild(b);
    }
  }
  function fillYearSelects() {
    const ys = store.years;
    const opts = ys.map((y) => `<option value="${y}">${y}</option>`).join("");
    $("f-anio-desde").innerHTML = opts; $("f-anio-hasta").innerHTML = opts;
    if (state.y0 != null && !ys.includes(state.y0)) state.y0 = null;
    if (state.y1 != null && !ys.includes(state.y1)) state.y1 = null;
    $("f-anio-desde").value = state.y0 ?? ys[0];
    $("f-anio-hasta").value = state.y1 ?? ys[ys.length - 1];
  }
  async function switchLayer(layer, resetFilters) {
    closePop();
    state.layer = layer;
    if (resetFilters) {
      state.measure = "imp";
      for (const f of MS_FIELDS) state.sel[f] = new Set();
      state.y0 = state.y1 = null;
    }
    renderLayerTabs();
    renderMeasureToggle();
    $("hero-label").textContent = "Cargando datos…";
    try {
      store = await loadLayer(layer);
    } catch (e) {
      $("hero-label").textContent = "No se pudieron cargar los datos. Recarga la página.";
      console.error(e);
      return;
    }
    if (state.layer !== layer) return;
    fillYearSelects();
    buildMultiSelects();
    update();
  }

  function bindControls() {
    $("f-texto").value = state.texto;
    $("f-benef").value = state.benef;
    $("f-min").value = state.min ?? "";
    $("f-max").value = state.max ?? "";
    $("f-texto").addEventListener("input", (e) => { state.texto = e.target.value.trim(); scheduleUpdate(); });
    $("f-benef").addEventListener("input", (e) => { state.benef = e.target.value.trim(); scheduleUpdate(); });
    const num = (v) => (v === "" ? null : Math.max(0, +v));
    $("f-min").addEventListener("input", (e) => { state.min = num(e.target.value); scheduleUpdate(); });
    $("f-max").addEventListener("input", (e) => { state.max = num(e.target.value); scheduleUpdate(); });
    $("f-anio-desde").addEventListener("change", (e) => {
      state.y0 = +e.target.value; if (state.y1 != null && state.y0 > state.y1) { state.y1 = state.y0; $("f-anio-hasta").value = state.y0; }
      scheduleUpdate();
    });
    $("f-anio-hasta").addEventListener("change", (e) => {
      state.y1 = +e.target.value; if (state.y0 != null && state.y1 < state.y0) { state.y0 = state.y1; $("f-anio-desde").value = state.y1; }
      scheduleUpdate();
    });
    $("reset").addEventListener("click", () => {
      for (const f of MS_FIELDS) { state.sel[f] = new Set(); refreshMsButton(f); }
      state.texto = state.benef = ""; state.y0 = state.y1 = state.min = state.max = null;
      ["f-texto", "f-benef", "f-min", "f-max"].forEach((id) => { $(id).value = ""; });
      fillYearSelects();
      update();
    });
    document.querySelectorAll("#tabla th[data-sort]").forEach((th) => th.addEventListener("click", () => {
      const k = th.dataset.sort;
      state.sort = { key: k, dir: state.sort.key === k ? -state.sort.dir : (k === "imp" || k === "a" ? -1 : 1) };
      sortedCache = null; state.page = 0; renderTable();
    }));
    const tbody = $("tabla").querySelector("tbody");
    tbody.addEventListener("click", (e) => { const tr = e.target.closest("tr[data-i]"); if (tr) openFicha(+tr.dataset.i); });
    tbody.addEventListener("keydown", (e) => { if (e.key === "Enter") { const tr = e.target.closest("tr[data-i]"); if (tr) openFicha(+tr.dataset.i); } });
    $("prev").addEventListener("click", () => { state.page--; renderTable(); $("tabla").scrollIntoView({ block: "nearest" }); });
    $("next").addEventListener("click", () => { state.page++; renderTable(); $("tabla").scrollIntoView({ block: "nearest" }); });
    $("dl-csv").addEventListener("click", downloadCSV);
    $("dl-xlsx").addEventListener("click", downloadXLSX);
    $("ficha").addEventListener("click", (e) => { if (e.target === $("ficha")) $("ficha").close(); });
    let rs = null;
    window.addEventListener("resize", () => { clearTimeout(rs); rs = setTimeout(() => Object.values(charts).forEach((c) => c.resize()), 150); });
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { if (store) renderCharts(); });
  }

  async function init() {
    readHash();
    bindControls();
    try {
      manifest = await fetchJSON("data/manifest.json");
    } catch (e) {
      $("hero-label").textContent = "Todavía no hay datos cargados. Vuelve a intentarlo más tarde.";
      return;
    }
    const fecha = (s) => (s ? new Date(s).toLocaleString("es-ES", { dateStyle: "long", timeStyle: "short" }) : "—");
    const est = (k) => manifest.capas[k]?.estado?.ultima_comprobacion;
    $("footer-update").textContent = `Última comprobación de las fuentes — OCDE: ${fecha(est("aod"))} · BDNS: ${fecha(est("bdns"))} · IATI: ${fecha(est("iati"))}.`;
    if (!manifest.capas[state.layer]?.anios.some((a) => a.registros > 0)) {
      state.layer = Object.keys(LAYERS).find((k) => manifest.capas[k]?.anios.some((a) => a.registros > 0)) || "aod";
    }
    await switchLayer(state.layer, false);
  }
  document.addEventListener("DOMContentLoaded", init);
})();
