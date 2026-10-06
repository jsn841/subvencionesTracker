import json, re, sys, urllib.request, collections, io
UA = {"User-Agent": "Mozilla/5.0 (subvencionesTracker probe)"}
def get(url, headers=None, timeout=300):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()
def p(*a): print(*a, flush=True)
part = sys.argv[1]
if part == "bdns":
    h = get("https://www.infosubvenciones.es/bdnstrans/doc/swagger").decode("utf-8","replace")
    p("SWAGGERHTML", re.sub(r"\s+", " ", h)[:1500])
    for js in re.findall(r'src="([^"]+\.js)"', h):
        u = js if js.startswith("http") else "https://www.infosubvenciones.es/bdnstrans/doc/" + js.lstrip("./")
        try:
            t = get(u).decode("utf-8","replace")
            for m in set(re.findall(r'["\'](/[^"\']*api-docs[^"\']*|[^"\']*\.json)["\']', t)): p("JSREF", u, m)
        except Exception as e: p("JSERR", u, e)
    for u in ["https://www.infosubvenciones.es/bdnstrans/api/v3/api-docs", "https://www.infosubvenciones.es/bdnstrans/doc/v3/api-docs",
              "https://www.infosubvenciones.es/bdnstrans/doc/api-docs", "https://www.infosubvenciones.es/bdnstrans/api/api-docs",
              "https://www.infosubvenciones.es/bdnstrans/doc/swagger/v3/api-docs", "https://www.infosubvenciones.es/bdnstrans/api/openapi.json"]:
        try:
            d = get(u)
            if d[:1] == b"{":
                spec = json.loads(d); p("SPEC OK", u)
                for path, ops in spec.get("paths", {}).items():
                    for m, op in ops.items():
                        p("OP", m.upper(), path, [(x.get("name"), (x.get("schema") or {}).get("type")) for x in op.get("parameters", [])])
                comps = spec.get("components", {}).get("schemas", {})
                for k, v in comps.items(): p("SCHEMA", k, list((v.get("properties") or {}).keys()))
                break
            else: p("NOTJSON", u, d[:80])
        except Exception as e: p("ERR", u, e)
    reg = json.loads(get("https://www.infosubvenciones.es/bdnstrans/api/regiones"))
    def walk(n, depth=0):
        for c in n:
            if depth < 2: p("REG", depth, c["id"], c["descripcion"])
            walk(c.get("children", []), depth+1)
    walk(reg)
    for u in ["finalidades?vpd=GE", "beneficiarios?vpd=GE", "organos?vpd=GE&idAdmon=C", "organos/agrupacion?vpd=GE&idAdmon=C", "actividades?vpd=GE", "objetivos?vpd=GE", "reglamentos?vpd=GE"]:
        try: p("LIST", u, get("https://www.infosubvenciones.es/bdnstrans/api/" + u)[:1500].decode("utf-8","replace"))
        except Exception as e: p("LISTERR", u, e)
elif part == "crs":
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "oda_reader", "pyarrow", "pandas"], check=True)
    from oda_reader.crs import get_full_crs_parquet_url
    url = get_full_crs_parquet_url(); p("CRSURL", url)
    subprocess.run(["curl", "-sSL", "-o", "/tmp/crs.parquet", url], check=True)
    import pyarrow.parquet as pq, pyarrow.compute as pc
    f = pq.ParquetFile("/tmp/crs.parquet")
    p("ROWS", f.metadata.num_rows); p("SCHEMA", [(x.name, str(x.type)) for x in f.schema_arrow])
    cols = [x.name for x in f.schema_arrow]
    dcol = [c for c in cols if c.lower() in ("donor_code", "donorcode")][0]
    t = pq.read_table("/tmp/crs.parquet", filters=[(dcol, "in", [50, "50"])]) if True else None
    df = t.to_pandas(); p("SPAIN ROWS", len(df))
    ycol = [c for c in cols if c.lower() == "year"][0]
    p("YEARS", df.groupby(ycol).size().to_dict())
    for c in df.columns:
        if df[c].dtype == object and df[c].nunique() < 400:
            p("CAT", c, df[c].nunique(), df[c].value_counts().head(25).to_dict())
    p("SAMPLE", df.tail(3).to_json(orient="records", force_ascii=False)[:5000])
    p("SAMPLE_OLD", df[df[ycol] < 1990].head(2).to_json(orient="records", force_ascii=False)[:3000])
    num = [c for c in df.columns if re.search(r"usd|national|commit|disburs", c, re.I)]
    p("NUMSUMS", df.groupby(ycol)[num].sum(numeric_only=True).tail(6).to_string())
    for c in df.columns:
        if re.search(r"crs_?id|project", c, re.I): p("IDCOL", c, df[c].isna().mean(), df[c].nunique())
elif part == "infoaod":
    for u in ["https://infoaod.maec.es/", "https://infoaod.maec.es/descargas/DescargasAyuda.aspx", "https://infoaod.maec.es/descargas"]:
        try:
            s = get(u).decode("utf-8","replace")
            p("PAGE", u, len(s), re.sub(r"\s+", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", s, flags=re.S))[:2500])
            for l in sorted(set(re.findall(r'href="([^"]+)"', s))): p("  LINK", l)
        except Exception as e: p("ERR", u, e)
    s = get("https://www.exteriores.gob.es/es/ServiciosAlCiudadano/Paginas/Cooperacion/Seguimiento-y-Transparencia.aspx").decode("utf-8","replace")
    for l in sorted(set(re.findall(r'href="([^"]+)"', s))):
        if re.search(r"volcado|xls|zip|csv|seguimiento", l, re.I): p("  EXT", l)
elif part == "iati":
    x = get("https://www.aecid.es/documents/d/guest/aecid-activity")
    p("BYTES", len(x)); s = x.decode("utf-8","replace"); p(s[:3000])
    import xml.etree.ElementTree as ET
    root = ET.fromstring(x); acts = root.findall("iati-activity"); p("ACTS", len(acts))
    yrs = collections.Counter(); types = collections.Counter(); tags = collections.Counter()
    for a in acts:
        for ch in a: tags[ch.tag] += 1
        for t in a.findall("transaction"):
            d = t.find("transaction-date"); tt = t.find("transaction-type")
            if d is not None: yrs[d.get("iso-date","")[:4]] += 1
            if tt is not None: types[tt.get("code")] += 1
    p("TXYEARS", sorted(yrs.items())); p("TXTYPES", types); p("TAGS", tags.most_common())
    p("ONE", ET.tostring(acts[len(acts)//2], encoding="unicode")[:5000])
