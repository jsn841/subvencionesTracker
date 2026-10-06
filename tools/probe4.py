import json, re, sys, urllib.request, subprocess, os, ssl, time
import urllib.parse
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) subvencionesTracker"}
def get(url, ctx=None, timeout=600, headers=None):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.read()
def p(*a): print(*a, flush=True)
part = sys.argv[1]
if part == "crs2":
    # Structure: dimensions and codelists
    st = json.loads(get("https://sdmx.oecd.org/dcd-public/rest/dataflow/OECD.DCD.FSD/DSD_CRS@DF_CRS/latest?references=all",
                        headers={"Accept": "application/vnd.sdmx.structure+json;version=1.0"}))
    data = st.get("data", st)
    for ds in data.get("dataStructures", []):
        comps = ds["dataStructureComponents"]
        p("DIMS", [(d["id"], d.get("localRepresentation", {}).get("enumeration")) for d in comps["dimensionList"]["dimensions"]])
        p("ATTRS", [a["id"] for a in comps.get("attributeList", {}).get("attributes", [])])
        p("MEAS", [m["id"] for m in comps.get("measureList", {}).get("measures", [])] if "measureList" in comps else comps.get("measureList"))
    for cl in data.get("codelists", []):
        codes = cl.get("codes", [])
        p("CL", cl["id"], len(codes), [(c["id"], c.get("name")) for c in codes[:12]])
        if cl["id"] in ("CL_DAC_DONOR_AGENCY", "CL_CRS_MEASURE", "CL_DAC_FLOW_TYPE", "CL_MODALITY", "CL_PRICE_BASE", "CL_UNIT_MEASURE", "CL_DAC_FLOW", "CL_MD_DIM") or "AGENC" in cl["id"] or "MEASURE" in cl["id"] or "MD" in cl["id"]:
            p("CLFULL", cl["id"], [(c["id"], c.get("name")) for c in codes if c["id"].startswith(("ESP", "50")) or len(codes) < 120])
    # Data sample: Spain 2022, CSV with labels
    for q in ["ESP.......", "ESP........", "ESP.........", "ESP..........", "ESP..........."]:
        u = f"https://sdmx.oecd.org/dcd-public/rest/data/OECD.DCD.FSD,DSD_CRS@DF_CRS,/{q}?startPeriod=2022&endPeriod=2022&format=csvfilewithlabels"
        try:
            t0 = time.time(); d = get(u); p("DATAOK", q, len(d), round(time.time()-t0, 1)); open("/tmp/crs2022.csv", "wb").write(d); break
        except Exception as e: p("DATAERR", q, str(e)[:200])
    if os.path.exists("/tmp/crs2022.csv"):
        import csv, collections
        rows = list(csv.DictReader(open("/tmp/crs2022.csv", encoding="utf-8")))
        p("NROWS", len(rows)); p("COLS", list(rows[0].keys()))
        for r in rows[:4]: p("ROW", json.dumps(r, ensure_ascii=False))
        for k in rows[0].keys():
            c = collections.Counter(r[k] for r in rows)
            if len(c) < 60: p("VALS", k, len(c), c.most_common(40))
            else: p("NVALS", k, len(c))
    # also try the older years
    for yr in (1973, 1990, 2005):
        u = f"https://sdmx.oecd.org/dcd-public/rest/data/OECD.DCD.FSD,DSD_CRS@DF_CRS,/ESP............?startPeriod={yr}&endPeriod={yr}&format=csvfile"
        try: d = get(u); p("YEAR", yr, len(d), d[:300])
        except Exception as e: p("YEARERR", yr, str(e)[:200])
elif part == "infoaod2":
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "certifi"], check=True)
    import certifi
    der = get("http://www.cert.fnmt.es/certs/ACCOMP.crt"); open("/tmp/inter.der", "wb").write(der)
    subprocess.run("openssl x509 -inform der -in /tmp/inter.der -out /tmp/inter.pem", shell=True)
    subprocess.run(f"cat {certifi.where()} /tmp/inter.pem > /tmp/bundle.pem", shell=True)
    ctx = ssl.create_default_context(cafile="/tmp/bundle.pem")
    for u in ["https://infoaod.maec.es/Analisis", "https://infoaod.maec.es/Metodologia", "https://infoaod.maec.es/Escaneo"]:
        try:
            s = get(u, ctx).decode("utf-8", "replace")
            p("PAGE", u, len(s), re.sub(r"\s+", " ", re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", s, flags=re.S))[:2500])
            for l in sorted(set(re.findall(r'(?:href|src)="([^"]+)"', s))): p("  LINK", l)
        except Exception as e: p("ERR", u, e)
    base = "https://www.exteriores.gob.es/es/ServiciosAlCiudadano/Documents/Cooperacion/Seguimiento-y-transparencia/Seguimiento/"
    names = []
    for y in range(2003, 2025):
        for n in [f"Volcado-AOD-{y}.xlsx", f"Volcado-AOD-{y}.xls", f"Volcado-PACI-{y}.xls", f"Volcado-PACI-{y}.xlsx", f"Volcado-Seguimiento-AOD-{y}.xlsx", f"Volcado-AOD-{y}.zip", f"Volcado AOD {y}.xlsx", f"Seguimiento-AOD-{y}.xlsx", f"Volcado-{y}.xlsx"]:
            names.append(n)
    for n in names:
        u = base + urllib.parse.quote(n) if False else base + n.replace(" ", "%20")
        try:
            req = urllib.request.Request(u, method="HEAD", headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r: p("FOUND", u, r.headers.get("content-length"), r.headers.get("content-type"))
        except Exception as e:
            pass
    # Sharepoint search API for files in that library
    for u in ["https://www.exteriores.gob.es/es/ServiciosAlCiudadano/_api/web/GetFolderByServerRelativeUrl('/es/ServiciosAlCiudadano/Documents/Cooperacion/Seguimiento-y-transparencia/Seguimiento')/Files?$select=Name,Length",
              "https://www.exteriores.gob.es/es/ServiciosAlCiudadano/Paginas/Cooperacion/Seguimiento-y-Transparencia.aspx"]:
        try:
            s = get(u, headers={"Accept": "application/json;odata=nometadata"}).decode("utf-8", "replace")
            p("SP", u[:80], len(s), s[:300])
            for m in sorted(set(re.findall(r"(?:Volcado|volcado)[^\"'<>]{0,120}", s))): p("  VOL", m)
            for m in sorted(set(re.findall(r"[^\"'<> ]+\.(?:xlsx?|zip|csv)", s, re.I))): p("  FILE", m)
        except Exception as e: p("SPERR", u[:80], e)
