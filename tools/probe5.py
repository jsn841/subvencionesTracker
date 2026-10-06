import json, re, sys, urllib.request, urllib.parse, collections, csv, io, time
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) subvencionesTracker"}
def get(url, timeout=900, headers=None):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()
def p(*a): print(*a, flush=True)
part = sys.argv[1]
if part == "crs3":
    base = "https://sdmx.oecd.org/dcd-public/rest"
    for key in ["ESP..........", "ESP............"]:
        try:
            d = get(f"{base}/availableconstraint/OECD.DCD.FSD,DSD_CRS@DF_CRS,/{key}/all/TIME_PERIOD", headers={"Accept": "application/vnd.sdmx.structure+json;version=1.0"})
            p("AVAIL", key, d[:1500].decode("utf-8", "replace"))
        except Exception as e: p("AVAILERR", key, e)
    for yr in (2022, 2015, 2005):
        for key in ["ESP..........", "ESP............"]:
            u = f"{base}/data/OECD.DCD.FSD,DSD_CRS@DF_CRS,/{key}?startPeriod={yr}&endPeriod={yr}&format=csvfilewithlabels"
            try:
                t0 = time.time(); d = get(u); p("GOT", yr, key, len(d), round(time.time()-t0))
                break
            except Exception as e: p("ERR", yr, key, str(e)[:100]); d = None
        if not d: continue
        rows = list(csv.DictReader(io.StringIO(d.decode("utf-8-sig"))))
        p("COLS", list(rows[0].keys()))
        p("N", len(rows))
        combo = collections.Counter((r["MEASURE"], r["FLOW_TYPE"], r["PRICE_BASE"], r["UNIT_MEASURE"], r["MD_DIM"]) for r in rows)
        p("COMBOS", combo.most_common(40))
        for k in ["Measure", "Flow type", "Price base", "Unit of measure", "DONOR_AGENCY", "Donor agency", "MODALITY", "Modality", "CATEGORY_NAME", "FINANCETYPE_NAME", "BIMULTI_CODE", "REGION", "Region", "CHANNEL", "Channel", "Recipient"]:
            if k in rows[0]: p("V", k, collections.Counter(r[k] for r in rows).most_common(45))
        dd = [r for r in rows if r["MD_DIM"] == "DD"]
        ids = collections.Counter(r["MD_ID"] for r in dd); p("MDID uniq", len(ids), ids.most_common(3))
        one = ids.most_common(1)[0][0]
        for r in dd:
            if r["MD_ID"] == one: p("ONE", json.dumps({k: v for k, v in r.items() if v and k not in ("LONG_DESCRIPTION",)}, ensure_ascii=False)[:1800])
        tot = collections.defaultdict(float)
        for r in dd:
            try: tot[(r["MEASURE"], r["FLOW_TYPE"], r["PRICE_BASE"], r["UNIT_MEASURE"], r["UNIT_MULT"])] += float(r["OBS_VALUE"] or 0)
            except: pass
        p("TOTALS", sorted(tot.items(), key=lambda x: -abs(x[1]))[:20])
        time.sleep(5)
elif part == "bdns2":
    B = "https://www.infosubvenciones.es/bdnstrans/api/concesiones/busqueda?"
    def q(params):
        u = B + urllib.parse.urlencode(params, doseq=True)
        try:
            j = json.loads(get(u))
            if "content" not in j: return ("NOCONTENT", str(j)[:300])
            return j["totalElements"], len(j["content"]), [(c["fechaConcesion"], c["beneficiario"][:40], c["importe"], c["nivel2"][:40]) for c in j["content"][:2]]
        except Exception as e: return "ERR " + str(e)[:200]
    tests = [
        {"page": 0, "pageSize": 1000, "regiones": 520},
        {"page": 0, "pageSize": 1000, "regiones": 520, "vpd": "GE"},
        {"page": 0, "pageSize": 10000, "regiones": 521, "vpd": "GE"},
        {"page": 0, "pageSize": 5, "fechaDesde": "01/01/2016", "fechaHasta": "31/12/2016"},
        {"page": 0, "pageSize": 5, "fechaDesde": "01/01/2016", "fechaHasta": "31/12/2016", "vpd": "GE"},
        {"page": 0, "pageSize": 5, "fechaDesde": "01/01/2014", "fechaHasta": "31/12/2014", "tipoAdministracion": "C", "vpd": "GE"},
        {"page": 0, "pageSize": 3, "regiones": 520, "order": "fechaConcesion", "direccion": "asc", "vpd": "GE"},
        {"page": 0, "pageSize": 3, "regiones": 521, "order": "fechaConcesion", "direccion": "asc", "vpd": "GE"},
        {"page": 0, "pageSize": 3, "finalidad": 20, "order": "fechaConcesion", "direccion": "asc", "vpd": "GE"},
        {"page": 0, "pageSize": 3, "order": "fechaConcesion", "direccion": "asc", "vpd": "GE"},
        {"page": 0, "pageSize": 3, "regiones": [520, 521], "vpd": "GE"},
        {"page": 0, "pageSize": 3, "fechaRegInicio": "01/10/2026", "fechaRegFin": "06/10/2026", "vpd": "GE"},
        {"page": 0, "pageSize": 3, "fechaDesde": "01/09/2026", "fechaHasta": "06/10/2026", "regiones": 520, "vpd": "GE"},
    ]
    for t in tests: p("Q", t, q(t))
    # how many regions top-level non-ES
    reg = json.loads(get("https://www.infosubvenciones.es/bdnstrans/api/regiones"))
    top = [(c["id"], c["descripcion"]) for c in reg]; p("TOP", top)
    for rid, name in top:
        if not name.startswith("ES "): p("REGCOUNT", rid, name, q({"page": 0, "pageSize": 1, "regiones": rid, "vpd": "GE"})[0])
    # tipos de beneficiario in concesion? check one full record of foreign entity
    p("RAW", get(B + "page=0&pageSize=2&regiones=521&vpd=GE")[:1800].decode())
    # convocatoria regiones to check
    p("CONV", get("https://www.infosubvenciones.es/bdnstrans/api/convocatorias?vpd=GE&numConv=" + str(json.loads(get(B + "page=0&pageSize=1&regiones=520&vpd=GE"))["content"][0]["numeroConvocatoria"]))[:2500].decode())
