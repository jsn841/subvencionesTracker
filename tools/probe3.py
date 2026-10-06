import json, re, sys, urllib.request, collections, subprocess, os, ssl
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) subvencionesTracker"}
def get(url, ctx=None, timeout=300):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.read()
def p(*a): print(*a, flush=True)
part = sys.argv[1]
B = "https://www.infosubvenciones.es/bdnstrans/api"
if part == "bdns":
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "bdns-fetch"], check=False)
    try:
        import importlib.util
        spec = importlib.util.find_spec("bdns")
        root = os.path.dirname(spec.origin) if spec else None
        p("BDNSFETCH", root)
        if root:
            out = subprocess.run(["grep", "-rhoE", r"concesiones[^\"']*|\"[a-zA-Z]+\"\s*:\s*[a-zA-Z_]+", root, "--include=*.py"], capture_output=True, text=True).stdout
            p("\n".join(sorted(set(out.splitlines()))[:300]))
    except Exception as e: p("ERR", e)
    def tot(q):
        try:
            j = json.loads(get(B + "/concesiones/busqueda?page=0&pageSize=2&" + q))
            return j["totalElements"], [(c["fechaConcesion"], c["beneficiario"], c["importe"], c["nivel2"], c["convocatoria"][:90]) for c in j["content"]]
        except Exception as e: return "ERR " + str(e)[:200]
    for q in ["regiones=520", "regiones=521", "regiones=227", "finalidad=20", "finalidad=20&tipoAdministracion=C",
              "regiones=520&tipoAdministracion=C", "organos=56", "organos=12", "beneficiario=REPUBLICA", "nifCif=N",
              "fechaDesde=01/01/2008&fechaHasta=31/12/2008", "fechaDesde=01/01/2016&fechaHasta=31/01/2016", "fechaDesde=01/01/2014&fechaHasta=31/12/2015&tipoAdministracion=C",
              "pageSize=10000", "regiones=520&finalidad=20", "descripcion=cooperaci%C3%B3n%20internacional"]:
        p("Q", q, tot(q))
    j = json.loads(get(B + "/concesiones/busqueda?page=0&pageSize=1000&regiones=520"))
    p("PAGESIZE1000 got", len(j["content"]))
    cnt = collections.Counter((c["nivel1"], c["nivel2"]) for c in j["content"]); p("ORG", cnt.most_common(30))
    p("BEN", collections.Counter(c["beneficiario"][:60] for c in j["content"]).most_common(40))
    p("YRS", collections.Counter(c["fechaConcesion"][:4] for c in j["content"]).most_common())
    for path in ["/convocatorias/busqueda?page=0&pageSize=3&regiones=520", "/concesiones/busqueda?page=0&pageSize=1&regiones=520&order=fechaConcesion&direccion=asc"]:
        p("RAW", path, get(B + path)[:2500].decode())
elif part == "crs":
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "oda_reader", "pyarrow", "pandas"], check=True)
    url = "https://webfs-dcd.oecd.org/files/dotStat/DSD_CRS/CRS.parquet"
    r = subprocess.run(["curl", "-sSL", "-A", UA["User-Agent"], "-D", "/tmp/h.txt", "-o", "/tmp/crs.parquet", url]); p(open("/tmp/h.txt").read()[:1500])
    p("SIZE", os.path.getsize("/tmp/crs.parquet")); p("HEAD", open("/tmp/crs.parquet","rb").read(300))
    import pyarrow.parquet as pq, pandas as pd
    try:
        f = pq.ParquetFile("/tmp/crs.parquet")
    except Exception as e:
        p("PQERR", e)
        import oda_reader
        df = oda_reader.bulk_download_crs(); p("ODAREADER", df.shape)
        df.to_parquet("/tmp/crs.parquet"); f = pq.ParquetFile("/tmp/crs.parquet")
    p("ROWS", f.metadata.num_rows); p("SCHEMA", [(x.name, str(x.type)) for x in f.schema_arrow])
    cols = [x.name for x in f.schema_arrow]
    dcol = next(c for c in cols if c.lower() in ("donor_code", "donorcode"))
    tbl = pq.read_table("/tmp/crs.parquet")
    import pyarrow.compute as pc
    col = tbl[dcol]
    mask = pc.equal(pc.cast(col, "string"), "50")
    df = tbl.filter(mask).to_pandas(); del tbl
    p("SPAIN ROWS", len(df))
    ycol = next(c for c in cols if c.lower() == "year")
    p("YEARS", df.groupby(ycol).size().to_dict())
    for c in df.columns:
        if df[c].dtype == object and df[c].nunique() < 300:
            p("CAT", c, df[c].nunique(), json.dumps(df[c].value_counts().head(40).to_dict(), ensure_ascii=False, default=str))
        elif df[c].dtype == object:
            p("TXT", c, df[c].nunique(), df[c].isna().mean())
    p("SAMPLE", df.tail(3).to_json(orient="records", force_ascii=False))
    p("SAMPLE_OLD", df[df[ycol] < 1995].head(2).to_json(orient="records", force_ascii=False))
    num = [c for c in df.columns if str(df[c].dtype).startswith(("float", "int"))]
    p("NUMSUMS\n" + df.groupby(ycol)[num].sum().to_string())
    df.to_parquet("crs_spain.parquet")
elif part == "infoaod":
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "certifi"], check=True)
    out = subprocess.run("echo | openssl s_client -connect infoaod.maec.es:443 -servername infoaod.maec.es -showcerts 2>&1 | head -60", shell=True, capture_output=True, text=True).stdout
    p(out)
    out = subprocess.run("echo | openssl s_client -connect infoaod.maec.es:443 -servername infoaod.maec.es 2>/dev/null | openssl x509 -noout -text | grep -A2 -iE 'Authority Information|CA Issuers|Issuer:'", shell=True, capture_output=True, text=True).stdout
    p("AIA", out)
    m = re.search(r"CA Issuers - URI:(\S+)", out)
    if m:
        import certifi
        der = get(m.group(1)); open("/tmp/inter.der", "wb").write(der)
        subprocess.run("openssl x509 -inform der -in /tmp/inter.der -out /tmp/inter.pem || cp /tmp/inter.der /tmp/inter.pem", shell=True)
        subprocess.run(f"cat {certifi.where()} /tmp/inter.pem > /tmp/bundle.pem", shell=True)
        ctx = ssl.create_default_context(cafile="/tmp/bundle.pem")
        for u in ["https://infoaod.maec.es/", "https://infoaod.maec.es/descargas/DescargasAyuda.aspx"]:
            try:
                s = get(u, ctx).decode("utf-8", "replace")
                p("PAGE", u, len(s), re.sub(r"\s+", " ", re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", s, flags=re.S))[:4000])
                for l in sorted(set(re.findall(r'href="([^"]+)"', s))): p("  LINK", l)
            except Exception as e: p("ERR", u, e)
    s = get("https://www.exteriores.gob.es/es/ServiciosAlCiudadano/Paginas/Cooperacion/Seguimiento-y-Transparencia.aspx").decode("utf-8","replace")
    for l in sorted(set(re.findall(r'href="([^"]+)"', s))):
        if re.search(r"volcado|xls|zip|csv|seguimiento|infoaod", l, re.I): p("  EXT", l)
elif part == "iati":
    x = get("https://www.aecid.es/documents/d/guest/aecid-activity")
    import xml.etree.ElementTree as ET
    root = ET.fromstring(x); acts = root.findall("iati-activity"); p("ACTS", len(acts), "BYTES", len(x))
    yrs = collections.Counter(); types = collections.Counter(); tags = collections.Counter(); ctry = collections.Counter()
    for a in acts:
        for ch in a: tags[ch.tag] += 1
        for rc in a.findall("recipient-country"): ctry[rc.get("code")] += 1
        for t in a.findall("transaction"):
            d = t.find("transaction-date"); tt = t.find("transaction-type")
            if d is not None: yrs[d.get("iso-date","")[:4]] += 1
            if tt is not None: types[tt.get("code")] += 1
    p("TXYEARS", sorted(yrs.items())); p("TXTYPES", types); p("TAGS", tags.most_common()); p("CTRY", ctry.most_common(20))
    s = ET.tostring(acts[len(acts)//2], encoding="unicode"); s = re.sub(r"<budget.*?</budget>\s*", "", s, flags=re.S); p("ONE", s[:6000])
